from django.shortcuts import render

from .models import Reporte

def ver_reportes(request):
    reportes = Reporte.objects.select_related('producto').order_by('-fecha')
    return render(request, 'reportes/ver_reportes.html', {'reportes': reportes})
