from decimal import Decimal, ROUND_DOWN

def descuento_por_cantidad_empresa(cantidad):
    """
    Devuelve porcentaje de descuento según cantidad.
    """
    if cantidad >= 500:
        return Decimal("0.12")
    elif cantidad >= 100:
        return Decimal("0.07")
    return Decimal("0.00")

def calcular_total_empresa(precio_unitario, cantidad):
    """
    Calcula total de un ítem para empresas:
    - Quita IVA (19%)
    - Aplica descuento por cantidad
    """
    iva = Decimal("1.19")
    precio_unitario = Decimal(precio_unitario)
    cantidad = Decimal(cantidad)

    # Precio sin IVA
    precio_sin_iva = (precio_unitario / iva).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    # Porcentaje de descuento
    descuento_pct = descuento_por_cantidad_empresa(cantidad)

    # Precio con descuento
    precio_con_descuento = (precio_sin_iva * (Decimal("1.0") - descuento_pct)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    # Total del ítem
    total = (precio_con_descuento * cantidad).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    return total
