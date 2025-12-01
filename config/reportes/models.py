from django.db import models
from django.conf import settings


class Reporte(models.Model):
    TIPO_EVENTO = [
        ('DESCUENTO', 'Descuento aplicado'),
        ('STOCK', 'Cambio de stock'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_EVENTO)
    producto = models.ForeignKey('productos.Producto', on_delete=models.CASCADE)
    descripcion = models.TextField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo} - {self.producto.nombre} - {self.fecha.strftime('%Y-%m-%d %H:%M')}"
