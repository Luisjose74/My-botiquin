"""Programador en segundo plano para recordatorios de toma y alertas de vencimiento.

Arranca un hilo daemon que, en desarrollo (DEBUG=True), verifica cada 60
segundos si hay pautas programadas para el minuto actual y dispara los
correos/WhatsApp correspondientes, y también sincroniza las alertas de
vencimiento de todos los usuarios.

En producción se recomienda usar el Programador de tareas / cron invocando
`python manage.py enviar_recordatorios_hora` cada minuto y
`python manage.py sincronizar_alertas` periódicamente.
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

        try:
            from botiquin.servicio_alertas import sincronizar_alertas_todos

            sincronizar_alertas_todos()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error en el scheduler de alertas de vencimiento: %s", exc)

        time.sleep(60)


def iniciar_scheduler():
    global _scheduler_started
    if _scheduler_started:
        return
    if not getattr(settings, "DEBUG", False):
        return
    # Evitar arrancar dos veces (p. ej. en tests o con el reloader).
    if os.environ.get("DJANGO_SCHEDULER_DISABLED") == "1":
        return
    # En Windows, el reloader de Django puede duplicar procesos; solo arrancar
    # si estamos en el proceso principal o hijo de runserver.
    run_main = os.environ.get("RUN_MAIN", "")
    if run_main not in (None, "true"):
        return

    _scheduler_started = True
    hilo = threading.Thread(target=_loop, name="recordatorios-scheduler", daemon=True)
    hilo.start()
    print("[scheduler] Recordatorios y alertas en segundo plano iniciado (cada 60s).", flush=True)