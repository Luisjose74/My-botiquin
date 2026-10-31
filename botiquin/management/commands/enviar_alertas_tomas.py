"""Envía las alertas matutinas de tomas del día según las pautas activas.

Uso: python manage.py enviar_alertas_tomas

Identifica, para la fecha actual, qué pautas de toma corresponden y envía
un correo (Gmail) a cada integrante con sus tomas del día. Si el usuario tiene
configurado el canal WhatsApp y existe un endpoint configurado
(WHATSAPP_API_URL / WHATSAPP_API_TOKEN), también se intenta enviar por WhatsApp.

Pensado para ejecutarse a primera hora del día mediante tarea programada.
"""
import logging
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from botiquin.models import PautaToma
from cuentas.models import Usuario

logger = logging.getLogger(__name__)


def pautas_del_dia(hoy):
    return [
        p
        for p in PautaToma.objects.filter(activa=True).select_related(
            "medicamento", "miembro", "miembro__usuario"
        )
        if p._corresponde(hoy)
    ]


def agrupar_por_usuario(pautas):
    grupos = {}
    for pauta in pautas:
        usuario = getattr(pauta.miembro, "usuario", None)
        if usuario is None:
            continue
        grupos.setdefault(usuario, []).append(pauta)
    return grupos


def enviar_correo(usuario, pautas, hoy):
    if not usuario.email:
        logger.warning("Usuario %s sin correo: no se envía alerta de tomas.", usuario.pk)
        return False
    contexto = {
        "usuario": usuario,
        "pautas": pautas,
        "fecha": hoy,
        "site_url": getattr(settings, "SITE_URL", ""),
    }
    texto = render_to_string("botiquin/email_tomas_dia.txt", contexto)
    html = render_to_string("botiquin/email_tomas_dia.html", contexto)
    mensaje = EmailMultiAlternatives(
        subject=f"Tomas del día — {hoy.strftime('%d/%m/%Y')}",
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[usuario.email],
    )
    mensaje.attach_alternative(html, "text/html")
    try:
        mensaje.send()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error enviando correo de tomas a %s: %s", usuario.pk, exc)
        return False


def enviar_whatsapp(usuario, pautas, hoy):
    url = os.environ.get("WHATSAPP_API_URL", "").strip()
    token = os.environ.get("WHATSAPP_API_TOKEN", "").strip()
    if not url or not token:
        return False
    telefono = getattr(usuario, "telefono", "") or ""
    if not telefono:
        return False
    try:
        import requests

        texto = "Tomas del día ({}):\n".format(hoy.strftime("%d/%m/%Y"))
        for p in pautas:
            hora = p.hora.strftime("%H:%M") if p.hora else ""
            texto += f"- {p.medicamento.nombre} ({p.miembro.nombre}) dosis {p.dosis} {hora}\n"
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


class Command(BaseCommand):
    help = "Envía las alertas matutinas de tomas del día según las pautas activas."

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        pautas = pautas_del_dia(hoy)
        grupos = agrupar_por_usuario(pautas)

        correos = 0
        whatsapps = 0
        for usuario, lista in grupos.items():
            if usuario.canal_alertas == "correo" or usuario.canal_alertas == "notificacion":
                if enviar_correo(usuario, lista, hoy):
                    correos += 1
            if usuario.canal_alertas == "whatsapp":
                if enviar_whatsapp(usuario, lista, hoy):
                    whatsapps += 1
                else:
                    # Fallback a correo si WhatsApp no está configurado.
                    if enviar_correo(usuario, lista, hoy):
                        correos += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Tomas del día: {len(pautas)}. Usuarios notificados: {len(grupos)}. "
                f"Correos: {correos}. WhatsApp: {whatsapps}."
            )
        )