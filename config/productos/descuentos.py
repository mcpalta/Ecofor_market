from decimal import Decimal

def descuento_por_cantidad_empresa(cantidad):
    """
    Retorna el porcentaje de descuento para clientes empresa
    según la cantidad total de un producto.
    """
    if cantidad >= 500:
        return 0.12  # 12 %
    elif cantidad >= 100:
        return 0.07  # 7 %
    return 0.00      # sin descuento


def calcular_total_empresa(precio_unitario, cantidad):
    """
    Calcula el total para empresas:
    - Remueve el IVA (19%)
    - Aplica descuento por cantidad
    """
    # Remover IVA (precio venía con IVA incluido)
    precio_sin_iva = precio_unitario / 1.19

    # Obtener porcentaje de descuento
    descuento_pct = descuento_por_cantidad_empresa(cantidad)

    # Aplicar descuento sobre el valor sin IVA
    precio_con_descuento = precio_sin_iva * (1 - descuento_pct)

    # Calcular el total final
    total = precio_con_descuento * cantidad

    return round(total, 2)