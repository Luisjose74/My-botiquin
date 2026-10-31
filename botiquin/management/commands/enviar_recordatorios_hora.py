"""Envía recordatorios de toma para las pautas programadas en la hora actual.

Uso: python manage.py enviar_recordatorios_hora

Filtra las pautas activas cuya hora coincide con la hora actual (y que
correspondan al día de hoy) y dispara los correos/WhatsApp correspondientes.
Pensado para ejecutarse cada hora mediante tarea programada.
"""
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from botiquin.models import PautaToma
from botiquin.notificaciones import enviar_recordatorio_hora

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Envía recordatorios de toma para las pautas de la hora actual."

    def handle(self, *args, **options):
        ahora = timezone.localtime()
        hoy = ahora.date()
        hora_actual = ahora.hour

        candidatas = [
            p
            for p in PautaToma.objects.filter(activa=True).select_related(
                "medicamento", "miembro", "miembro__usuario"
            )
            if p._corresponde(hoy)
            and p.hora is not None
            and p.hora.hour == hora_actual
        ]

        correos, whatsapps = enviar_recordatorio_hora(candidatas, ahora)

        self.stdout.write(
            self.style.SUCCESS(
                f"Pautas de la hora {hora_actual}: {len(candidatas)}. "
                f"Correos: {correos}. WhatsApp: {whatsapps}."
            )
        )