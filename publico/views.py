"""Vistas de las páginas públicas e institucionales de Mi Botiquín Digital.

Las páginas de contenido (portada, educación, institucional y legales) no
requieren inicio de sesión y solo aceptan el método GET. El formulario de
contacto sí acepta POST. El contenido se toma de `publico.contenido`, de
modo que la información institucional y educativa se actualiza desde un solo
lugar.
"""
import smtplib
import time

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .contenido import (
    AVISO_PROFESIONAL,
    DATOS_RECOLECTADOS,
    FAQ,
    FECHA_ACTUALIZACION,
    FUNCIONES,
    HITOS_VENCIMIENTO,
    INSTRUCCIONES_ENTREGA,
    INSTITUCION,
    NO_ENTREGAR,
    PASOS,
    PERFILES,
    PUNTOS_AZULES,
    PUNTOS_AZULES_INTRO,
    PUNTOS_AZULES_NOTA,
    SECCIONES_EDUCACION,
    SITIO,
    VERSION_LEGAL,
)
from .forms import ETIQUETAS_ASUNTO, ContactoForm


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


def _destinatario_contacto():
    """Casilla que recibe los mensajes del formulario de contacto."""
    correo = (INSTITUCION.get("correo") or "").strip()
    if correo:
        return correo
    from email.utils import parseaddr

    return parseaddr(getattr(settings, "DEFAULT_FROM_EMAIL", ""))[1]


def _enviar_mensaje_contacto(form):
    """Envía el mensaje del formulario por correo.

    Devuelve True si el correo salió, False si falló el envío.
    """
    destinatario = _destinatario_contacto()
    if not destinatario:
        return False

    motivo = ETIQUETAS_ASUNTO.get(form.cleaned_data["asunto"], "Consulta")
    # El asunto se limpia de saltos de línea para no romper la cabecera.
    asunto = f"[Contacto · {motivo}] {form.cleaned_data['nombre']}".replace(
        "\n", " "
    ).replace("\r", " ")

    cuerpo = (
        f"Mensaje recibido desde el formulario de contacto de {SITIO['nombre']}.\n\n"
        f"Nombre: {form.cleaned_data['nombre']}\n"
        f"Correo: {form.cleaned_data['correo']}\n"
        f"Motivo: {motivo}\n\n"
        f"{form.cleaned_data['mensaje']}\n"
    )

    mensaje = EmailMultiAlternatives(
        subject=asunto[:120],
        body=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario],
        reply_to=[form.cleaned_data["correo"]],
    )
    try:
        mensaje.send()
    except (smtplib.SMTPException, OSError):
        return False
    return True


@require_http_methods(["GET", "POST"])
def contacto(request):
    """Formulario público de contacto con el equipo del proyecto."""
    if request.method == "POST":
        # Campo trampa: si viene relleno se confirma el envío sin procesar.
        if (request.POST.get("sitio_web") or "").strip():
            messages.success(
                request,
                "¡Gracias por escribirnos! Te responderemos a la brevedad.",
            )
            return redirect("publico:contacto")

        form = ContactoForm(request.POST)
        if form.is_valid():
            if form.envio_simulado:
                # Envío automatizado: se acepta sin mandar el correo.
                messages.success(
                    request,
                    "¡Gracias por escribirnos! Te responderemos a la brevedad.",
                )
                return redirect("publico:contacto")

            if _enviar_mensaje_contacto(form):
                messages.success(
                    request,
                    "¡Gracias por escribirnos! Recibimos tu mensaje y te "
                    "responderemos a la brevedad.",
                )
                return redirect("publico:contacto")

            messages.error(
                request,
                "No pudimos enviar el mensaje en este momento. Escríbenos "
                "directamente a "
                f"{_destinatario_contacto()} o inténtalo de nuevo más tarde.",
            )
        else:
            messages.error(
                request,
                "Revisa los campos marcados: falta información para enviar el "
                "mensaje.",
            )
    else:
        form = ContactoForm(initial={"inicio": str(int(time.time()))})

    contexto = _contexto(
        request,
        titulo="Contacto",
        descripcion=(
            "Escríbenos para resolver dudas, reportar un error o enviar "
            "sugerencias sobre Mi Botiquín Digital."
        ),
        form=form,
        marca_tiempo=int(time.time()),
        destinatario=_destinatario_contacto(),
        seccion_activa="contacto",
    )
    return render(request, "publico/contacto.html", contexto)


@require_GET
def robots_txt(request):
    """Archivo robots.txt del sitio (indica el sitemap a los buscadores)."""
    base = getattr(settings, "SITE_URL", "").strip().rstrip("/")
    sitemap = (
        f"{base}/sitemap.xml"
        if base
        else request.build_absolute_uri("/sitemap.xml")
    )
    return render(
        request,
        "publico/robots.txt",
        {"sitemap": sitemap},
        content_type="text/plain; charset=utf-8",
    )


@require_GET
def puntos_azules(request):
    """Directorio de Puntos Azules y guía de entrega segura."""
    contexto = _contexto(
        request,
        titulo="Puntos Azules",
        descripcion=(
            "Directorio de los puntos de recolección de medicamentos de "
            "Sogamoso (Boyacá) y guía para entregar de forma segura los "
            "medicamentos vencidos o deteriorados."
        ),
        intro=PUNTOS_AZULES_INTRO,
        puntos=PUNTOS_AZULES,
        nota_directorio=PUNTOS_AZULES_NOTA,
        instrucciones=INSTRUCCIONES_ENTREGA,
        no_entregar=NO_ENTREGAR,
        seccion_activa="puntos_azules",
    )
    return render(request, "publico/puntos_azules.html", contexto)


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
