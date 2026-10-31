"""Lógica compartida para sincronizar alertas de vencimiento.

Usada tanto por el comando `sincronizar_alertas` como por el
programador en segundo plano (scheduler) que arranca con el servidor.
"""
import logging
from django.db import models

from django.utils import timezone

from cuentas.models import Usuario
from botiquin.alertas import sincronizar_alertas

logger = logging.getLogger(__name__)


def sincronizar_alertas_todos():
    """Ejecuta sincronizar_alertas para todos los usuarios con medicamentos.

    Devuelve (total_creadas, total_eliminadas).
    """
    ahora = timezone.localtime()
    usuarios = Usuario.objects.filter(
        models.Q(medicamentos__isnull=False) | models.Q(perfil_miembro__medicamentos__isnull=False)
    ).distinct()

    total_creadas = 0
    total_eliminadas = 0
    for usuario in usuarios:
        try:
            resultado = sincronizar_alertas(usuario)
            total_creadas += resultado["creadas"]
            total_eliminadas += resultado["eliminadas"]
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error sincronizando alertas de %s: %s", usuario.pk, exc)

    logger.info(
        "Alertas vencimiento %s: creadas=%d, eliminadas=%d",
        ahora.strftime("%H:%M"), total_creadas, total_eliminadas,
    )
    print(
        f"[alertas-vencimiento] {ahora.strftime('%H:%M')}: "
        f"creadas={total_creadas}, eliminadas={total_eliminadas}",
        flush=True,
    )
    return total_creadas, total_eliminadas
