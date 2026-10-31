"""Notificaciones por correo/WhatsApp para asignaciones y recordatorios."""

import logging
import os

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def _enviar_correo(usuario, asunto, plantilla_txt, plantilla_html, contexto):
    if not usuario or not getattr(usuario, "email", None):
        logger.warning("Usuario sin correo: no se envía notificación.")
        return False
    texto = render_to_string(plantilla_txt, contexto)
    html = render_to_string(plantilla_html, contexto)
    mensaje = EmailMultiAlternatives(
        subject=asunto,
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[usuario.email],
    )
    mensaje.attach_alternative(html, "text/html")
    try:
        mensaje.send()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error enviando correo a %s: %s", usuario.pk, exc)
        return False


def _enviar_whatsapp(usuario, texto):
    url = os.environ.get("WHATSAPP_API_URL", "").strip()
    token = os.environ.get("WHATSAPP_API_TOKEN", "").strip()
    if not url or not token:
        return False
    telefono = getattr(usuario, "telefono", "") or ""
    if not telefono:
        return False
    try:
        import requests

        requests.post(
            url,
            json={"telefono": telefono, "mensaje": texto},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error enviando WhatsApp a %s: %s", usuario.pk, exc)
        return False


def notificar_medicamento_asignado(medicamento, miembro):
    """Notifica a un integrante que se le asignó un medicamento del inventario."""
    usuario = getattr(miembro, "usuario", None)
    if usuario is None or usuario == getattr(medicamento, "usuario", None):
        return False

    contexto = {
        "usuario": usuario,
        "medicamento": medicamento,
        "miembro": miembro,
        "site_url": getattr(settings, "SITE_URL", ""),
    }
    enviado = _enviar_correo(
        usuario,
        f"Nuevo medicamento asignado: {medicamento.nombre}",
        "botiquin/email_asignacion_medicamento.txt",
        "botiquin/email_asignacion_medicamento.html",
        contexto,
    )

    if getattr(usuario, "canal_alertas", "") == "whatsapp":
        texto = f"Se te asignó el medicamento {medicamento.nombre} en tu botiquín."
        _enviar_whatsapp(usuario, texto)

    return enviado


def notificar_asignacion(pauta):
    """Notifica al integrante que se le asignó un medicamento/pauta."""
    miembro = pauta.miembro
    usuario = getattr(miembro, "usuario", None)
    if usuario is None:
        return False

    contexto = {
        "usuario": usuario,
        "pauta": pauta,
        "medicamento": pauta.medicamento,
        "miembro": miembro,
        "site_url": getattr(settings, "SITE_URL", ""),
    }
    enviado = _enviar_correo(
        usuario,
        f"Nuevo medicamento asignado: {pauta.medicamento.nombre}",
        "botiquin/email_asignacion.txt",
        "botiquin/email_asignacion.html",
        contexto,
    )

    if getattr(usuario, "canal_alertas", "") == "whatsapp":
        texto = (
            f"Se te asignó {pauta.medicamento.nombre} "
            f"({pauta.get_frecuencia_display()}, dosis {pauta.dosis})."
        )
        _enviar_whatsapp(usuario, texto)

    return enviado


def enviar_recordatorio_hora(pautas, ahora):
    """Envía recordatorios para pautas cuya hora coincide con la hora actual."""
    from collections import defaultdict

    grupos = defaultdict(list)
    for pauta in pautas:
        usuario = getattr(pauta.miembro, "usuario", None)
        if usuario is None:
            continue
        grupos[usuario].append(pauta)

    correos = 0
    whatsapps = 0
    for usuario, lista in grupos.items():
        contexto = {
            "usuario": usuario,
            "pautas": lista,
            "hora": ahora,
            "site_url": getattr(settings, "SITE_URL", ""),
        }
        if getattr(usuario, "canal_alertas", "") in ("correo", "notificacion"):
            if _enviar_correo(
                usuario,
                f"Recordatorio de toma — {ahora.strftime('%H:%M')}",
                "botiquin/email_recordatorio_hora.txt",
                "botiquin/email_recordatorio_hora.html",
                contexto,
            ):
                correos += 1
        if getattr(usuario, "canal_alertas", "") == "whatsapp":
            texto = "Recordatorio de toma ({}):\n".format(ahora.strftime("%H:%M"))
            for p in lista:
                texto += f"- {p.medicamento.nombre} ({p.miembro.nombre}) dosis {p.dosis}\n"
            if _enviar_whatsapp(usuario, texto):
                whatsapps += 1
            else:
                if _enviar_correo(
                    usuario,
                    f"Recordatorio de toma — {ahora.strftime('%H:%M')}",
                    "botiquin/email_recordatorio_hora.txt",
                    "botiquin/email_recordatorio_hora.html",
                    contexto,
                ):
                    correos += 1
    return correos, whatsapps
