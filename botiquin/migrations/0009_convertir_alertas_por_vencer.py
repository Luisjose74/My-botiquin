"""Convierte los avisos antiguos de "próximo a vencer" (un único aviso a 30 días)
en el hito de vencimiento que corresponde según los días que faltan.

Las alertas que ya no aplican (medicamentos vigentes o vencidos) se eliminan:
el aviso de vencimiento se vuelve a crear en la siguiente sincronización.
"""
from django.db import migrations
from django.utils import timezone


def hito_por_vencer(dias):
    if dias is None or dias < 0:
        return None
    if dias <= 5:
        return 5
    if dias <= 15:
        return 15
    if dias <= 30:
        return 30
    return None


def convertir_alertas(apps, schema_editor):
    Alerta = apps.get_model("botiquin", "Alerta")
    Medicamento = apps.get_model("botiquin", "Medicamento")

    hoy = timezone.localdate()
    for alerta in Alerta.objects.filter(tipo="por_vencer").select_related("medicamento"):
        medicamento = alerta.medicamento
        if medicamento is None:
            alerta.delete()
            continue
        dias = (medicamento.fecha_vencimiento - hoy).days
        hito = hito_por_vencer(dias)
        if hito is None:
            # Ya venció o falta más de 30 días: no aplica este aviso.
            alerta.delete()
            continue
        alerta.tipo = f"por_vencer_{hito}"
        alerta.save(update_fields=["tipo"])


def revertir_alertas(apps, schema_editor):
    Alerta = apps.get_model("botiquin", "Alerta")
    Alerta.objects.filter(tipo__startswith="por_vencer_").update(tipo="por_vencer")


class Migration(migrations.Migration):
    dependencies = [
        ("botiquin", "0008_alerta_archivada_alter_alerta_tipo"),
    ]

    operations = [
        migrations.RunPython(convertir_alertas, revertir_alertas),
    ]
