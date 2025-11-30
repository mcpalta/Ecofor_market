from django.db import models
from django.conf import settings


class Producto(models.Model):
    CATEGORIAS = [
        ("Papelería y Dispensadores", (
            ("higienicos", "Higiénicos"),
            ("toallas_papel", "Toallas de papel"),
            ("servilletas", "Servilletas"),
            ("panuelos", "Pañuelos"),
            ("panos", "Paños"),
            ("sabanillas", "Sabanillas"),
            ("dispensadores", "Dispensadores"),
        )),
        ("Artículos de Aseo", (
            ("contenedores", "Contenedores"),
            ("basureros", "Basureros"),
            ("articulos_limpieza", "Artículos de limpieza"),
            ("aseo", "Aseo"),
        )),
        ("Productos Químicos", (
            ("pisos", "Pisos"),
            ("limpiadores", "Limpiadores"),
            ("desodorante", "Desodorante Ambiental"),
            ("automotriz", "Automotriz"),
            ("lavanderia", "Lavandería"),
        )),
        ("Seguridad y Horeca", (
            ("epp", "Elementos de Protección Personal (EPP)"),
            ("horeca", "HORECA (Hoteles, Restaurantes, Cafeterías)"),
        )),
    ]

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    precio = models.PositiveIntegerField(verbose_name="Precio")
    stock = models.PositiveIntegerField(default=0)
    categoria = models.CharField(max_length=50, choices=CATEGORIAS, default="limpiadores")
    activo = models.BooleanField(default=True)

    imagen = models.ImageField(
        upload_to="productos/",
        blank=True,
        null=True,
        verbose_name="Imagen del producto"
    )

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.nombre} ({self.get_categoria_display()}) - Stock: {self.stock}"


class Pedido(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente (sin pago real)"),
        ("pagado", "Pagado (simulado)"),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    total = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-creado"]

    def __str__(self):
        return f"Pedido #{self.id} de {self.usuario.username}"


class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, related_name="items", on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.PositiveIntegerField()

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"