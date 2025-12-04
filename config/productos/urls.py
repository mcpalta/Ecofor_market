from django.urls import path
from . import views

urlpatterns = [
    # CRUD admin
    path("admin-lista/", views.listar_productos, name="listar_productos"),
    path("admin-crear/", views.crear_producto, name="crear_producto"),
    path("admin-editar/<int:id>/", views.editar_producto, name="editar_producto"),
    path("admin-eliminar/<int:id>/", views.eliminar_producto, name="eliminar_producto"),

    # Catálogo
    path("catalogo/", views.catalogo, name="catalogo_productos"),

    # Carrito
    path("carrito/generar_factura/", views.generar_factura, name="generar_factura"),
    path("carrito/", views.ver_carrito, name="ver_carrito"),
    path("carrito/agregar/<int:id>/", views.agregar_al_carrito, name="agregar_al_carrito"),
    path("restar/<int:id>/", views.restar_del_carrito, name="restar_del_carrito"),
    path("carrito/eliminar/<int:id>/", views.eliminar_del_carrito, name="eliminar_del_carrito"),
    path("carrito/vaciar/", views.vaciar_carrito, name="vaciar_carrito"),
    path("carrito/finalizar/", views.finalizar_compra, name="finalizar_compra"),
    path("factura/pdf/", views.generar_factura_pdf, name="generar_factura_pdf"),
    path("solicitar-cotizacion/<int:pedido>/", views.solicitar_cotizacion, name="solicitar_cotizacion"),
    path("carrito/crear-pedido-cotizacion/", views.crear_pedido_cotizacion, name="crear_pedido_cotizacion"),
    path("carrito/<int:pedido_id>/", views.ver_carrito, name="ver_carrito_con_pedido"),
    path("cotizaciones/buscar/", views.buscar_cotizacion, name="buscar_cotizacion"),
    path("cotizaciones/<int:pedido_id>/", views.ver_cotizacion, name="ver_cotizacion"),
    path("cotizaciones/pdf/<int:pedido_id>/", views.generar_cotizacion_pdf, name="generar_cotizacion_pdf"),
    path("pago-ingresar/", views.ingresar_id_pago, name="ingresar_id_pago"),
    path("pago/<int:pedido_id>/", views.ver_pago, name="ver_pago"),
    path("pago/<int:pedido_id>/confirmar/", views.confirmar_pago, name="confirmar_pago"),


]