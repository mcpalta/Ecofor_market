from django.contrib import admin
from .models import Reporte

@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'producto', 'fecha')
    list_filter = ('tipo', 'fecha')
    search_fields = ('producto__nombre', 'descripcion')
