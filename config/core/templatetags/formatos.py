from django import template

register = template.Library()

@register.filter
def clp(value):
    """
    Convierte un número entero en formato clp.
    """
    if value is None:
        return "$0"
    
    try:
        value = int(value)
        # Formatea con separador de miles (,) y luego reemplazamos por punto
        return "${:,.0f}".format(value).replace(",", ".")
    except (ValueError, TypeError):
        return "$0"