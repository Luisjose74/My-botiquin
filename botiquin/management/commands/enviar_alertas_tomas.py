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
    """Pares (pauta, horario) que corresponden al día indicado."""
    pares = []
    pautas = PautaToma.objects.filter(activa=True).select_related(
        "medicamento", "miembro", "miembro__usuario"
    ).prefetch_related("horarios")
    for pauta in pautas:
        if not pauta._corresponde(hoy):
            continue
        for horario in pauta.horarios.all():
            pares.append((pauta, horario))
    return pares


def agrupar_por_usuario(pares, hoy):
    """Agrupa las tomas del día por usuario, con su enlace de confirmación."""
    from django.urls import reverse
    from botiquin.notificaciones import generar_token_confirmacion, url_base_sitio

    base = url_base_sitio()
    grupos = {}
    for pauta, horario in pares:
        usuario = getattr(pauta.miembro, "usuario", None)
        if usuario is None:
            continue
        token = generar_token_confirmacion(pauta.pk, horario.pk, hoy)
        confirm_url = f"{base}{reverse('botiquin:confirmar_toma', args=[token])}"
        grupos.setdefault(usuario, []).append(
            {"pauta": pauta, "horario": horario, "confirm_url": confirm_url}
        )
    return grupos


def enviar_correo(usuario, items, hoy):
    if not usuario.email:
        logger.warning("Usuario %s sin correo: no se envía alerta de tomas.", usuario.pk)
        return False
    from botiquin.notificaciones import url_base_sitio

    contexto = {
        "usuario": usuario,
        "items": items,
        "pautas": [it["pauta"] for it in items],
        "fecha": hoy,
        "site_url": url_base_sitio(),
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


def enviar_whatsapp_texto(usuario, texto):
    import os

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


def enviar_whatsapp(usuario, pares, hoy):
    url = os.environ.get("WHATSAPP_API_URL", "").strip()
    token = os.environ.get("WHATSAPP_API_TOKEN", "").strip()
    if not url or not token:
        return False
    telefono = getattr(usuario, "telefono", "") or ""
    if not telefono:
        return False
    try:
        import requests

        texto = "Tomas del d\u00eda ({}):\n".format(hoy.strftime("%d/%m/%Y"))
        for pauta, horario in pares:
            hora = horario.hora.strftime("%H:%M") if horario.hora else ""
            texto += (
                f"- {pauta.medicamento.nombre} ({pauta.miembro.nombre}) "
                f"dosis {pauta.dosis} {hora}\n"
            )
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
    help = "Env\u00eda las alertas matutinas de tomas del d\u00eda seg\u00fan las pautas activas."

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        pares = pautas_del_dia(hoy)
        grupos = agrupar_por_usuario(pares, hoy)

        correos = 0
        whatsapps = 0
        for usuario, items in grupos.items():
            if usuario.canal_alertas == "correo" or usuario.canal_alertas == "notificacion":
                if enviar_correo(usuario, items, hoy):
                    correos += 1
            if usuario.canal_alertas == "whatsapp":
                # WhatsApp con formato enriquecido
                texto = "Tomas del d\u00eda ({}):\n".format(hoy.strftime("%d/%m/%Y"))
                for it in items:
                    p = it["pauta"]
                    hora = it["horario"].hora
                    texto += (
                        f"\U0001f48a *{p.medicamento.nombre}* ({p.miembro.nombre})"
                        f" \u2014 dosis {p.dosis}"
                        f" {hora.strftime('%H:%M') if hora else ''}\n"
                    )
                    texto += f"\u2705 Confirmar: {it['confirm_url']}\n"
                if enviar_whatsapp_texto(usuario, texto):
                    whatsapps += 1
                else:
                    if enviar_correo(usuario, items, hoy):
                        correos += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Tomas del d\u00eda: {len(pares)}. Usuarios notificados: {len(grupos)}. "
                f"Correos: {correos}. WhatsApp: {whatsapps}."
            )
        )
