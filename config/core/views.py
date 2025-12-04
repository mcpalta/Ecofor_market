from django.shortcuts import render
from productos.models import Producto

def home(request):
    productos = Producto.objects.filter(activo=True).order_by('-creado')[:6]
    context = {
            'productos': productos
        }
    return render(request, 'core/home.html', context)