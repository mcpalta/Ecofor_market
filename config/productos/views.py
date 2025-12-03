from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from mensajeria.models import Message
from usuarios.decoradores import admin_required
from usuarios.models import Usuario
from .models import PagoSimulado, Producto, Pedido, PedidoItem
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


#def ver_carrito(request):
    #carrito = Carrito(request)
    #return render(request, "productos/carrito.html", {"carrito": carrito})
@login_required
def ver_carrito(request, pedido_id=None):
    carrito = Carrito(request)
    pedido = None

    if pedido_id:
        pedido = Pedido.objects.get(id=pedido_id)

    return render(request, "productos/carrito.html", {
        "carrito": carrito,
        "pedido": pedido
    })


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
    nuevo_num = pedido.id  # Usar ID del pedido como número de pedido
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

@login_required
def solicitar_cotizacion(request, pedido):
    pedido = get_object_or_404(Pedido, id=pedido, usuario=request.user)
    # Buscar un usuario del tipo "atencion" de forma aleatoria
    soporte = Usuario.objects.filter(tipo_cliente="atencion_cliente").order_by('?').first()

    if not soporte:
        messages.error(request, "No existe ningún usuario de atención al cliente.")
        return redirect("mis_pedidos")

    contenido = (
        "📌 **Solicitud de cotización**\n\n"
        f"Usuario: {request.user.username}\n"
        f"Pedido ID: {pedido.id}\n"
        f"Total estimado: ${pedido.total}\n\n"
        "Solicitud enviada automáticamente al equipo de atención al cliente."
    )

    Message.objects.create(
        sender=request.user,
        receiver=soporte,
        content=contenido
    )

    messages.success(request, "Tu solicitud de cotizacion fue enviada al equipo de atención al cliente.")
    return redirect("mensajeria:chat", user_id=soporte.id)

@login_required
def crear_pedido_cotizacion(request):
    carrito = Carrito(request)

    if not carrito.cart:
        return redirect("ver_carrito")

    pedido = Pedido.objects.create(
        usuario=request.user,
        total=0,
        estado="cotizacion"
    )

    total_final = 0

    for item in carrito:
        producto = item["producto"]
        cantidad = item["cantidad"]
        precio = int(item["precio"])

        if cantidad > producto.stock:
            cantidad = producto.stock

        if cantidad <= 0:
            continue

        # Crear item del pedido
        PedidoItem.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio
        )

        # SUMAR SUBTOTAL DEL ITEM
        total_final += precio * cantidad

    # ACTUALIZAR TOTAL DEL PEDIDO
    pedido.total = total_final
    pedido.save()

    return redirect("ver_carrito_con_pedido", pedido_id=pedido.id)


@login_required
def buscar_cotizacion(request):
    if not request.user.tipo_cliente == "atencion_cliente":
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect("home")

    pedido = None
    try:
        if request.method == "GET" and "id" in request.GET:
            pedido_id = request.GET.get("id")
            pedido = Pedido.objects.filter(id=pedido_id).first()

        if not pedido:
            messages.error(request, "No existe ninguna cotización con ese ID.")

    except:
        messages.error(request, f"Error al buscar la cotización: {e}")

    return render(request, "productos/buscar_cotizacion.html", {"pedido": pedido})

@login_required
def ver_cotizacion(request, pedido_id):
    if not request.user.tipo_cliente == "atencion_cliente":
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect("home")

    pedido = get_object_or_404(Pedido, id=pedido_id)
    items = PedidoItem.objects.filter(pedido=pedido)

    return render(request, "productos/ver_cotizacion.html", {
        "pedido": pedido,
        "items": items
    })

@login_required
def generar_cotizacion_pdf(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    items = PedidoItem.objects.filter(pedido=pedido)

    # Calcular totales
    total_bruto = 0
    for item in items:
        total_bruto += item.precio_unitario * item.cantidad

    # Crear PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"inline; filename=cotizacion_{pedido.id}.pdf"

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>COTIZACIÓN</b>", styles["Title"]))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"Cliente: {pedido.usuario.username}", styles["Normal"]))
    elements.append(Paragraph(f"Cotización Nº: {pedido.id}", styles["Normal"]))
    elements.append(Spacer(1, 0.5*cm))

    # Tabla de items
    table_data = [["Producto", "Cantidad", "Precio Unit.", "Subtotal"]]
    for item in items:
        subtotal = item.precio_unitario * item.cantidad
        table_data.append([
            item.producto.nombre,
            item.cantidad,
            f"${item.precio_unitario:.0f}",
            f"${subtotal:.0f}"
        ])

    table = Table(table_data, colWidths=[6*cm, 2*cm, 3*cm, 3*cm])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.7*cm))
    elements.append(Paragraph(f"<b>Total: ${total_bruto:.0f}</b>", styles["Heading3"]))

    doc.build(elements)
    return response

@login_required
def ingresar_id_pago(request):
    try:
        if request.method == "POST":
            pedido_id = request.POST.get("pedido_id")
            return redirect("ver_pago", pedido_id=pedido_id)

        return render(request, "productos/ingresar_id_pago.html")
    except Exception as e:
        messages.error(request, f"Error al procesar la solicitud: {e}")
        return redirect("catalogo_productos")

@login_required
def ver_pago(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

    return render(request, "productos/ver_pago.html", {"pedido": pedido})

@login_required
def confirmar_pago(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

    # Evitar pagos repetidos
    if pedido.estado == "pagado":
        messages.warning(request, "Este pedido ya fue pagado.")
        return redirect("ver_pago", pedido_id=pedido.id)

    # Descontar stock según los pedidos de la empresa
    items = pedido.items.all()

    for item in items:
        prod = item.producto
        prod.stock -= item.cantidad
        if prod.stock < 0:
            prod.stock = 0
        prod.save()

    pedido.estado = "pagado"
    pedido.save()

    return render(request, "productos/pago_exitoso.html", {"pedido": pedido})
