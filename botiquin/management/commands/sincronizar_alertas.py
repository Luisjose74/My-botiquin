"""Recalcula las alertas de todos los usuarios con medicamentos registrados.

Uso: python manage.py sincronizar_alertas
Pensado para ejecutarse de forma periódica (tarea programada) además de
actualizarse automáticamente al abrir el panel.
"""
from django.core.management.base import BaseCommand

from cuentas.models import Usuario
from botiquin.alertas import sincronizar_alertas


class Command(BaseCommand):
    help = "Sincroniza las alertas de vencimiento y agotamiento de todos los usuarios."

    def handle(self, *args, **options):
        usuarios = Usuario.objects.filter(medicamentos__isnull=False).distinct()
        total_creadas = 0
        total_archivadas = 0
        total_eliminadas = 0
        for usuario in usuarios:
            resultado = sincronizar_alertas(usuario)
            total_creadas += resultado["creadas"]
            total_archivadas += resultado["archivadas"]
            total_eliminadas += resultado["eliminadas"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Alertas creadas: {total_creadas}. "
                f"Alertas archivadas: {total_archivadas}. "
                f"Alertas eliminadas: {total_eliminadas}."
            )
        )
