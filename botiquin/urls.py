"""URLs de la app botiquin."""
from django.urls import path

from . import views

app_name = "botiquin"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nuevo/", views.crear, name="crear"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/eliminar/", views.eliminar, name="eliminar"),
    path("alertas/", views.alertas, name="alertas"),
    path("alertas/<int:pk>/leida/", views.marcar_alerta_leida, name="alerta_leida"),
    path("alertas/leer-todas/", views.marcar_todas_leidas, name="alertas_leer_todas"),
    path("pautas/", views.pautas_lista, name="pautas_lista"),
    path("pautas/nueva/", views.pauta_crear, name="pauta_crear"),
    path("pautas/<int:pk>/editar/", views.pauta_editar, name="pauta_editar"),
    path("pautas/<int:pk>/eliminar/", views.pauta_eliminar, name="pauta_eliminar"),
]
