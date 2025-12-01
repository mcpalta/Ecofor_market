from django.db.models.signals import pre_save
from django.dispatch import receiver
from productos.models import Producto
from .models import Reporte

@receiver(pre_save, sender=Producto)
def registrar_cambios_producto(sender, instance, **kwargs):
    try:
        producto_original = Producto.objects.get(pk=instance.pk)
    except Producto.DoesNotExist:
        return  # Es un producto nuevo, no registrar

    # Detectar cambio en STOCK
    if producto_original.stock != instance.stock:
        diferencia = instance.stock - producto_original.stock
        tipo_mov = "Aumento" if diferencia > 0 else "Disminución"

        Reporte.objects.create(
            tipo="STOCK",
            producto=instance,
            descripcion=f"Stock modificado: {tipo_mov} ({diferencia}). Valor previo: {producto_original.stock}, nuevo valor: {instance.stock}."
        )

    # Detectar cambio en DESCUENTO
    if producto_original.descuento != instance.descuento:
        Reporte.objects.create(
            tipo="DESCUENTO",
            producto=instance,
            descripcion=f"Descuento cambiado de {producto_original.descuento}% a {instance.descuento}%."
        )
