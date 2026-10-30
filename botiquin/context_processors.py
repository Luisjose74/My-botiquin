"""Datos globales para la barra de navegación de la app."""
from .models import Alerta


def alertas_pendientes(request):
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    return {
        "alertas_pendientes": Alerta.objects.filter(
            usuario=usuario, leida=False
        ).count()
    }
