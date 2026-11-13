"""Context processors de las páginas públicas.

El contenido educativo de cuidado del botiquín vive en `publico.contenido` y
se comparte entre el portal público, las vistas de apoyo de la app privada y
el correo de alertas. Este processor lo pone a disposición de todas las
plantillas para no repetirlo en cada vista.
"""
from django.urls import reverse

from .contenido import PILARES_CUIDADO


def consejos_cuidado(request):
    """Pilares educativos de cuidado del botiquín y enlace a Puntos Azules."""
    return {
        "pilares_cuidado": PILARES_CUIDADO,
        "url_puntos_azules": f"{reverse('publico:puntos_azules')}#directorio",
    }
