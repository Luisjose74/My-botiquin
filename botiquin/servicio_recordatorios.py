"""Lógica compartida para disparar recordatorios de toma.

Usada tanto por el comando `enviar_recordatorios_hora` como por el
programador en segundo plano (scheduler) que arranca con el servidor.
"""
import logging
from datetime import timedelta

from django.utils import timezone

from .models import PautaToma
from .notificaciones import enviar_recordatorio_hora

logger = logging.getLogger(__name__)


def disparar_recordatorios_ahora():
    """Dispara los recordatorios cuya pauta coincide con la hora/minuto actual.

    Devuelve (cantidad_pautas, correos, whatsapps).
    """
    ahora = timezone.localtime()
    hoy = ahora.date()

    candidatas = [
        p
        for p in PautaToma.objects.filter(activa=True).select_related(
            "medicamento", "miembro", "miembro__usuario"
        )
        if p._corresponde(hoy)
        and p.hora is not None
        and p.hora.hour == ahora.hour
        and p.hora.minute == ahora.minute
    ]

    correos, whatsapps = enviar_recordatorio_hora(candidatas, ahora)
    print(
        f"[recordatorios] {ahora.strftime('%H:%M')}: {len(candidatas)} pautas, "
        f"{correos} correos, {whatsapps} WhatsApp",
        flush=True,
    )
    return len(candidatas), correos, whatsapps