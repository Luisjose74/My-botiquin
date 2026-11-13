"""Envía recordatorios de toma para los horarios del minuto actual.

Uso: python manage.py enviar_recordatorios_hora

Filtra los horarios de las pautas activas cuya hora/minuto coincide con el
momento actual (y que correspondan al día de hoy) y dispara los
correos/WhatsApp. Cada horario genera su propio recordatorio.
Pensado para ejecutarse cada minuto mediante tarea programada, o por el
programador en segundo plano que arranca con el servidor en desarrollo.
"""
import logging

from django.core.management.base import BaseCommand

from botiquin.servicio_recordatorios import disparar_recordatorios_ahora

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Envía recordatorios de toma para las pautas del minuto actual."

    def handle(self, *args, **options):
        cantidad, correos, whatsapps = disparar_recordatorios_ahora()
        ahora = __import__("django.utils.timezone", fromlist=["localtime"]).localtime()
        self.stdout.write(
            self.style.SUCCESS(
                f"Tomas a las {ahora.strftime('%H:%M')}: {cantidad}. "
                f"Correos: {correos}. WhatsApp: {whatsapps}."
            )
        )