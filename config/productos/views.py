from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from mensajeria.models import Message
from usuarios.decoradores import admin_required
from .models import Producto, Pedido, PedidoItem
from .forms import ProductoForm
from .carrito import Carrito
from .pdf_factura import generar_pdf_factura
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors
from django.conf import settings
from .descuentos import calcular_total_empresa, descuento_por_cantidad_empresa
from .models import Factura, FacturaItem

# ---------------------------------------------------------
# ZONA ADMIN
# ---------------------------------------------------------

@admin_required
def listar_productos(request):
    productos = Producto.objects.all().order_by('-creado')
    return render(request, "productos/listar.html", {"productos": productos})

@admin_required
def crear_producto(request):
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("listar_productos")
    else:
        form = ProductoForm()

    return render(request, "productos/crear.html", {"form": form})

@admin_required
def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect("listar_productos")
    else:
        form = ProductoForm(instance=producto)

    return render(request, "productos/editar.html", {"form": form, "producto": producto})

@admin_required
def eliminar_producto(request, id):
    try:
        producto = get_object_or_404(Producto, id=id)
        if producto.stock > 0:
            messages.error(request, "No se puede eliminar un producto con stock disponible.")
            return redirect("listar_productos")
        else:
            producto.delete()
            return redirect("listar_productos")
    except Exception as e:
        messages.error(request, f"Error al eliminar el producto: {e}")
        return redirect("listar_productos")

# ---------------------------------------------------------
# ZONA CLIENTES
# ---------------------------------------------------------

def catalogo(request):
    productos_list = Producto.objects.filter(activo=True, stock__gt=0).order_by('-creado')
    # Filtrado por categoría
    categoria_slug = request.GET.get('categoria')
    if categoria_slug:
        productos_list = productos_list.filter(categoria=categoria_slug)
    # Búsqueda por nombre o descripción
    query = request.GET.get('buscar')
    if query:
        productos_list = productos_list.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query) |
            Q(categoria__icontains=query)
        )
    
    paginator = Paginator(productos_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'categoria_seleccionada': categoria_slug,
        'lista_categorias': Producto.CATEGORIAS
    }
    
    return render(request, "productos/catalogo.html", context)
# ---------------------------------------------------------
# ZONA CARRITO Y COMPRA
# ---------------------------------------------------------
@login_required
def restar_del_carrito(request, id):
    producto = get_object_or_404(Producto, id=id)
    carrito = Carrito(request)
    carrito.restar(producto)
    return redirect("ver_carrito")

@login_required
def agregar_al_carrito(request, id):
    producto = get_object_or_404(Producto, id=id, activo=True)
    carrito = Carrito(request)
    
    try:
        cantidad = int(request.POST.get("cantidad", 1))
    except ValueError:
        cantidad = 1

    carrito.add(producto, cantidad)
    return redirect("ver_carrito")

@login_required
def ver_carrito(request):
    carrito = Carrito(request)
    return render(request, "productos/carrito.html", {"carrito": carrito})

@login_required
def eliminar_del_carrito(request, id):
    producto = get_object_or_404(Producto, id=id)
    carrito = Carrito(request)
    carrito.remove(producto)
    return redirect("ver_carrito")

@login_required
def vaciar_carrito(request):
    carrito = Carrito(request)
    carrito.clear()
    return redirect("ver_carrito")

@login_required
def finalizar_compra(request):
    carrito = Carrito(request)

    if not carrito.cart:
        return redirect("catalogo_productos")

    es_empresa = hasattr(request.user, "es_empresa") and request.user.es_empresa()

    pedido = Pedido.objects.create(
        usuario=request.user,
        total=0,
        estado="pagado"
    )

    total_bruto = 0
    total_descuento = 0
    total_final = 0

    for item in carrito:
        producto = item["producto"]
        cantidad = item["cantidad"]
        precio = int(item["precio"])

        # Validación de stock
        if cantidad > producto.stock:
            cantidad = producto.stock
        
        if cantidad <= 0:
            continue

        subtotal_bruto = precio * cantidad
        
        monto_descuento_item = 0
        if es_empresa:
            # Asumiendo que descuento_por_cantidad_empresa devuelve un decimal
            pct_descuento = descuento_por_cantidad_empresa(cantidad) 
            monto_descuento_item = int(subtotal_bruto * pct_descuento) # Convertimos a int
        
        subtotal_final = subtotal_bruto - monto_descuento_item

        # Actualizar Stock y Base de Datos
        producto.stock -= cantidad
        producto.save()

        PedidoItem.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio,
        )

        # Acumuladores
        total_bruto += subtotal_bruto
        total_descuento += monto_descuento_item
        total_final += subtotal_final

    pedido.total = total_final
    pedido.save()

    carrito.clear()

    contexto = {
        "pedido": pedido,
        "total_bruto": total_bruto,
        "total_descuento": total_descuento,
        "total_final": total_final,
        "es_empresa": es_empresa,
    }

    return render(request, "productos/compra_exitosa.html", contexto)

@login_required
def generar_factura(request):
    carrito = Carrito(request)

    if not carrito.cart:
        return redirect("catalogo_productos")

    # Solo empresas pueden generar factura
    es_empresa = hasattr(request.user, "es_empresa") and request.user.es_empresa()
    if not es_empresa:
        messages.error(request, "Solo las cuentas de empresa pueden generar facturas.")
        return redirect("ver_carrito")

    total_bruto = 0
    total_descuento = 0
    total_final = 0

    items_factura = []  

    for item in carrito:
        producto = item["producto"]
        cantidad = item["cantidad"]
        precio = int(item["precio"])

        # Subtotal antes de descuento
        subtotal_bruto = precio * cantidad

        # Descuento según cantidad
        pct_descuento = descuento_por_cantidad_empresa(cantidad)
        monto_descuento_item = int(subtotal_bruto * pct_descuento)

        # Total final del item
        subtotal_final = subtotal_bruto - monto_descuento_item

        # Acumular totales generales
        total_bruto += subtotal_bruto
        total_descuento += monto_descuento_item
        total_final += subtotal_final

        # Guardar datos del item para el template
        items_factura.append({
            "producto": producto,         
            "cantidad": cantidad,
            "precio": precio,
            "subtotal_bruto": subtotal_bruto,
            "descuento": monto_descuento_item,
            "total_final": subtotal_final,
        })

    contexto = {
        "usuario": request.user,
        "items": items_factura,   
        "total_bruto": total_bruto,
        "total_descuento": total_descuento,
        "total_final": total_final,
    }

    return render(request, "productos/factura.html", contexto)

@login_required
def generar_factura_pdf(request):
    carrito = Carrito(request)

    if not carrito.cart:
        return redirect("ver_carrito")

    user = request.user

    total_bruto = 0
    total_descuento = 0
    total_sin_iva = 0
    total_final = 0

    items_data = []

    for item in carrito:
        producto = item["producto"]
        cantidad = item["cantidad"]
        precio_unitario = float(item["precio"])

        # Validación de stock
        if cantidad > producto.stock:
            cantidad = producto.stock
        
        if cantidad <= 0:
            continue

        subtotal_bruto = precio_unitario * cantidad
        total_bruto += subtotal_bruto

        # Descuentos por cantidad
        pct_desc = descuento_por_cantidad_empresa(cantidad)
        monto_desc = subtotal_bruto * pct_desc
        total_descuento += monto_desc

        # Precio final sin IVA y con descuento
        total_item_final = calcular_total_empresa(precio_unitario, cantidad)

        total_sin_iva += (precio_unitario / 1.19) * cantidad
        total_final += total_item_final

        items_data.append({
            "nombre": producto.nombre,
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "descuento": monto_desc,
            "subtotal": total_item_final,
        })

        # Actualizar stock y guardar
        producto.stock -= cantidad
        producto.save()

    # Crear la factura en BD
    factura = Factura.objects.create(
        empresa=user,
        total_bruto=total_bruto,
        total_descuento=total_descuento,
        total_sin_iva=total_sin_iva,
        total_final=total_final,
    )

    for item in items_data:
        FacturaItem.objects.create(
            factura=factura,
            nombre=item["nombre"],
            cantidad=item["cantidad"],
            precio_unitario=item["precio_unitario"],
            descuento_aplicado=item["descuento"],
            subtotal=item["subtotal"]
        )

    # Vaciar carrito después de procesar
    carrito.clear()

    # Crear el PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"inline; filename=factura_{factura.id}.pdf"

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>FACTURA ELECTRÓNICA</b>", styles["Title"]))
    elements.append(Spacer(1, 0.5*cm))

    elements.append(Paragraph(f"Empresa: {user.username}", styles["Normal"]))
    elements.append(Paragraph(f"Factura Nº: {factura.id}", styles["Normal"]))
    elements.append(Paragraph(f"Fecha: {factura.fecha.strftime('%d-%m-%Y')}", styles["Normal"]))
    elements.append(Spacer(1, 0.5*cm))

    # Tabla de items
    table_data = [
        ["Producto", "Cant", "Precio Unit.", "Desc", "Subtotal Final"]
    ]

    for i in items_data:
        table_data.append([
            i["nombre"],
            i["cantidad"],
            f"${i['precio_unitario']:.0f}",
            f"${i['descuento']:.0f}",
            f"${i['subtotal']:.0f}"
        ])

    table = Table(table_data, colWidths=[6*cm, 2*cm, 3*cm, 3*cm, 3*cm])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.7*cm))

    # Totales
    elements.append(Paragraph(f"Total bruto: ${total_bruto:.0f}", styles["Normal"]))
    elements.append(Paragraph(f"Descuentos aplicados: ${total_descuento:.0f}", styles["Normal"]))
    elements.append(Paragraph(f"Total sin IVA: ${total_sin_iva:.0f}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Total final (empresa, sin IVA): ${total_final:.0f}</b>", styles["Heading3"]))

    doc.build(elements)
    return response
