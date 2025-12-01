from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from django.http import HttpResponse
from datetime import datetime

def generar_pdf_factura(usuario, items, total_bruto, total_descuento, total_final):
    # preparar respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="factura_{datetime.now().strftime("%Y%m%d%H%M%S")}.pdf"'
    )

    p = canvas.Canvas(response, pagesize=letter)

    # márgenes
    margin_left = 40
    margin_right = 550
    y = 750

    # Encabezado
    p.setFont("Helvetica-Bold", 18)
    p.drawString(margin_left, y, "FACTURA ELECTRÓNICA")
    y -= 30

    p.setFont("Helvetica", 12)
    p.drawString(margin_left, y, "Ecofor Market")
    y -= 18
    p.drawString(margin_left, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    y -= 35

    # Datos del cliente
    p.setFont("Helvetica-Bold", 13)
    p.drawString(margin_left, y, "Datos del Cliente")
    y -= 22

    p.setFont("Helvetica", 11)
    p.drawString(margin_left, y, f"Razón Social: {usuario.username}")
    y -= 17
    p.drawString(margin_left, y, f"Email: {usuario.email}")
    y -= 17
    p.drawString(margin_left, y, f"RUT Empresa: {usuario.rut}")
    y -= 30

    # Encabezado tabla
    p.setFont("Helvetica-Bold", 11)

    col_producto = margin_left
    col_cantidad = margin_left + 280  # Aumentado de 230
    col_precio = margin_left + 350    # Aumentado de 300
    col_desc = margin_left + 420      # Aumentado de 380
    col_total = margin_left + 480     # Aumentado de 460

    # Encabezados
    p.drawString(col_producto, y, "Producto")
    p.drawString(col_cantidad, y, "Cant.")
    p.drawString(col_precio, y, "Precio")
    p.drawString(col_desc, y, "Desc.")
    p.drawString(col_total, y, "Total")

    y -= 12
    p.line(margin_left, y, margin_right, y)
    y -= 22

    p.setFont("Helvetica", 10)

    # Items
    for item in items:

        # Ajuste automático de salto de página
        if y < 80:
            p.showPage()
            y = 750
            p.setFont("Helvetica", 10)

        # Imprimir fila
        p.drawString(col_producto, y, item["nombre"][:40])  # corta nombres largos
        p.drawString(col_cantidad, y, str(item["cantidad"]))
        p.drawString(col_precio, y, f"${item['precio']:,}")
        p.drawString(col_desc, y, f"-${item['descuento']:,}")
        p.drawString(col_total, y, f"${item['subtotal_final']:,}")
        y -= 20

    # totales
    y -= 15
    p.line(margin_left, y, margin_right, y)
    y -= 30

    p.setFont("Helvetica-Bold", 12)
    p.drawString(col_precio, y, f"Total Bruto: ${total_bruto:,}")
    y -= 22
    p.drawString(col_precio, y, f"Descuentos: -${total_descuento:,}")
    y -= 22
    p.drawString(col_precio, y, f"Total Final (Exento IVA): ${total_final:,}")

    # cerrar PDF
    p.showPage()
    p.save()
    return response
