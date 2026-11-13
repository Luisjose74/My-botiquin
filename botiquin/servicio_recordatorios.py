"""Lógica compartida para disparar recordatorios de toma.

Usada tanto por el comando `enviar_recordatorios_hora` como por el
programador en segundo plano (scheduler) que arranca con el servidor.
"""
import logging

from django.utils import timezone

from .models import HorarioToma, PautaToma
from .notificaciones import enviar_recordatorio_hora

logger = logging.getLogger(__name__)


def horarios_de_ahora(ahora=None):
    """Pares (pauta, horario) cuya hora coincide con el momento actual.

    Cada horario de cada pauta es una toma independiente: el de las 07:00 y el
    de las 19:00 generan recordatorios separados.
    """
    if ahora is None:
        ahora = timezone.localtime()
    hoy = ahora.date()

    pares = []
    pautas = PautaToma.objects.filter(activa=True).select_related(
        "medicamento", "miembro", "miembro__usuario"
    ).prefetch_related("horarios")

    for pauta in pautas:
        if not pauta._corresponde(hoy):
            continue
        for horario in pauta.horarios.all():
            if horario.hora is None:
                continue
            if horario.hora.hour == ahora.hour and horario.hora.minute == ahora.minute:
                pares.append((pauta, horario))
    return pares


def disparar_recordatorios_ahora():
    """Dispara los recordatorios cuya hora/minuto coincide con el actual.

    Devuelve (cantidad_tomas, correos, whatsapps).
    """
    ahora = timezone.localtime()
    pares = horarios_de_ahora(ahora)

    correos, whatsapps = enviar_recordatorio_hora(pares, ahora)
    print(
        f"[recordatorios] {ahora.strftime('%H:%M')}: {len(pares)} tomas, "
        f"{correos} correos, {whatsapps} WhatsApp",
        flush=True,
    )
    return len(pares), correos, whatsapps
