from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator

from usuarios.decoradores import admin_required
from .models import Producto, Pedido, PedidoItem
from .forms import ProductoForm
from .carrito import Carrito
from .descuentos import descuento_por_cantidad_empresa

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
    producto = get_object_or_404(Producto, id=id)
    producto.delete()
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