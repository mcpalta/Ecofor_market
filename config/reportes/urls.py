from django.urls import path
from . import views

urlpatterns = [
    path('ver/', views.ver_reportes, name='ver_reportes'),
]