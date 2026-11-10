"""URLs de las páginas públicas e institucionales."""
from django.urls import path

from . import views

app_name = "publico"

urlpatterns = [
    path("", views.portada, name="portada"),
    path("acerca-de/", views.acerca_de, name="acerca_de"),
    path("educacion/", views.educacion, name="educacion"),
    path("privacidad/", views.privacidad, name="privacidad"),
    path("terminos/", views.terminos, name="terminos"),
]
