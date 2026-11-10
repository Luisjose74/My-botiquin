"""Vistas de las páginas públicas e institucionales de Mi Botiquín Digital.

Todas las páginas de esta app son públicas: no requieren inicio de sesión y
solo aceptan el método GET. El contenido se toma de `publico.contenido`, de
modo que la información institucional y educativa se actualiza desde un solo
lugar.
"""
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .contenido import (
    AVISO_PROFESIONAL,
    DATOS_RECOLECTADOS,
    FAQ,
    FECHA_ACTUALIZACION,
    FUNCIONES,
    HITOS_VENCIMIENTO,
    INSTITUCION,
    PASOS,
    PERFILES,
    SECCIONES_EDUCACION,
    SITIO,
    VERSION_LEGAL,
)


def _url_canonica(request):
    """URL absoluta de la página actual (para SEO y redes sociales)."""
    base = getattr(settings, "SITE_URL", "").strip().rstrip("/")
    if base:
        return f"{base}{request.path}"
    return request.build_absolute_uri(request.path)


def _contexto(request, titulo, descripcion, **extra):
    """Contexto común de todas las páginas públicas."""
    contexto = {
        "sitio": SITIO,
        "institucion": INSTITUCION,
        "titulo_pagina": titulo,
        "descripcion_pagina": descripcion,
        "url_canonica": _url_canonica(request),
        "aviso_profesional": AVISO_PROFESIONAL,
    }
    contexto.update(extra)
    return contexto


@require_GET
def portada(request):
    """Página principal pública: qué es el proyecto y cómo aporta valor."""
    contexto = _contexto(
        request,
        titulo="Inicio",
        descripcion=SITIO["descripcion"],
        funciones=FUNCIONES,
        pasos=PASOS,
        perfiles=PERFILES,
        hitos=HITOS_VENCIMIENTO,
        faq=FAQ,
        seccion_activa="portada",
    )
    return render(request, "publico/portada.html", contexto)


@require_GET
def acerca_de(request):
    """Página institucional: origen, propósito, metodología y créditos."""
    contexto = _contexto(
        request,
        titulo="Acerca del proyecto",
        descripcion=(
            "Conoce el origen, el propósito y la metodología de Mi Botiquín "
            "Digital, un proyecto de Regencia de Farmacia desarrollado en la "
            "Universidad Pedagógica y Tecnológica de Colombia."
        ),
        funciones=FUNCIONES,
        seccion_activa="acerca_de",
    )
    return render(request, "publico/acerca_de.html", contexto)


@require_GET
def educacion(request):
    """Guía de educación sanitaria preventiva (Regencia de Farmacia)."""
    contexto = _contexto(
        request,
        titulo="Educación sanitaria",
        descripcion=(
            "Recomendaciones de Regencia de Farmacia: almacenamiento correcto, "
            "desecho seguro de medicamentos vencidos, señales de alarma y "
            "cuándo consultar a un profesional de salud."
        ),
        secciones=SECCIONES_EDUCACION,
        seccion_activa="educacion",
    )
    return render(request, "publico/educacion.html", contexto)


@require_GET
def privacidad(request):
    """Política de tratamiento de datos personales (Ley 1581 de 2012)."""
    contexto = _contexto(
        request,
        titulo="Política de privacidad",
        descripcion=(
            "Cómo tratamos los datos personales en Mi Botiquín Digital: qué "
            "recogemos, para qué los usamos, cómo los protegemos y cómo "
            "puedes ejercer tus derechos, conforme a la Ley 1581 de 2012."
        ),
        datos=DATOS_RECOLECTADOS,
        version=VERSION_LEGAL,
        fecha=FECHA_ACTUALIZACION,
        seccion_activa="privacidad",
    )
    return render(request, "publico/privacidad.html", contexto)


@require_GET
def terminos(request):
    """Condiciones de uso del servicio."""
    contexto = _contexto(
        request,
        titulo="Términos y condiciones",
        descripcion=(
            "Condiciones de uso de Mi Botiquín Digital: alcance del servicio, "
            "uso de la cuenta, límites del alcance clínico y legislación "
            "aplicable."
        ),
        version=VERSION_LEGAL,
        fecha=FECHA_ACTUALIZACION,
        seccion_activa="terminos",
    )
    return render(request, "publico/terminos.html", contexto)
