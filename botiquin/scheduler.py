"""Programador en segundo plano para recordatorios de toma.

Arranca un hilo daemon que, en desarrollo (DEBUG=True), verifica cada 60
segundos si hay pautas programadas para el minuto actual y dispara los
correos/WhatsApp correspondientes, sin necesidad de abrir una terminal.

En producción se recomienda usar el Programador de tareas / cron invocando
`python manage.py enviar_recordatorios_hora` cada minuto.
"""
import logging
import os
import threading
import time

from django.conf import settings

logger = logging.getLogger(__name__)

_scheduler_started = False


def _loop():
    # Pequeña espera inicial para que Django termine de arrancar.
    time.sleep(5)
    while True:
        try:
            from botiquin.servicio_recordatorios import disparar_recordatorios_ahora

            disparar_recordatorios_ahora()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error en el scheduler de recordatorios: %s", exc)
        time.sleep(60)


def iniciar_scheduler():
    global _scheduler_started
    if _scheduler_started:
        return
    if not getattr(settings, "DEBUG", False):
        return
    # Solo arrancar en el proceso hijo del runserver (evita duplicados con el reloader).
    if os.environ.get("RUN_MAIN") not in (None, "true"):
        return
    # Evitar arrancar dos veces (p. ej. en tests).
    if os.environ.get("DJANGO_SCHEDULER_DISABLED") == "1":
        return

    _scheduler_started = True
    hilo = threading.Thread(target=_loop, name="recordatorios-scheduler", daemon=True)
    hilo.start()
    print("[scheduler] Recordatorios en segundo plano iniciado (cada 60s).", flush=True)