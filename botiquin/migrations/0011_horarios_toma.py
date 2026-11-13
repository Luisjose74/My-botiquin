"""Horarios múltiples de toma por pauta.

- Nuevo modelo `HorarioToma`: una pauta puede tener varias horas al día
  (07:00 y 19:00, tres tomas, esquema de mediodía…).
- `TomaRegistrada` pasa a referenciar el horario, de modo que cada horario
  tiene su propio registro y su propia confirmación.
- Los datos existentes se migran: la hora única de cada pauta se convierte
  en su primer horario y las tomas ya registradas se asocian a ese horario.
"""
import django.db.models.deletion
from django.db import migrations, models


def migrar_horarios(apps, schema_editor):
    """Crea los horarios a partir de la hora única de cada pauta."""
    PautaToma = apps.get_model("botiquin", "PautaToma")
    HorarioToma = apps.get_model("botiquin", "HorarioToma")
    TomaRegistrada = apps.get_model("botiquin", "TomaRegistrada")

    for pauta in PautaToma.objects.all().order_by("pk"):
        horarios = []
        hora = getattr(pauta, "hora", None)
        if hora is not None:
            horarios.append(
                HorarioToma.objects.create(pauta=pauta, hora=hora, orden=0)
            )
        # Toda pauta tiene al menos un horario (aunque no tenga hora fija).
        if not horarios:
            horarios.append(
                HorarioToma.objects.create(pauta=pauta, hora=None, orden=0)
            )

        # Las tomas registradas quedan asociadas al primer horario.
        for toma in TomaRegistrada.objects.filter(pauta=pauta):
            toma.horario_id = horarios[0].pk
            toma.save(update_fields=["horario"])


def revertir_horarios(apps, schema_editor):
    """Devuelve la hora de la pauta a partir de su primer horario."""
    PautaToma = apps.get_model("botiquin", "PautaToma")
    HorarioToma = apps.get_model("botiquin", "HorarioToma")

    for pauta in PautaToma.objects.all():
        horario = HorarioToma.objects.filter(pauta=pauta).order_by("orden", "hora").first()
        if horario is not None:
            pauta.hora = horario.hora
            pauta.save(update_fields=["hora"])


class Migration(migrations.Migration):

    dependencies = [
        ("botiquin", "0010_clasificacion_uso"),
    ]

    operations = [
        migrations.CreateModel(
            name="HorarioToma",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "hora",
                    models.TimeField(
                        blank=True,
                        help_text="Déjalo vacío si la toma no tiene hora fija.",
                        null=True,
                        verbose_name="Hora de la toma",
                    ),
                ),
                ("orden", models.PositiveSmallIntegerField(default=0, verbose_name="Orden")),
                (
                    "pauta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="horarios",
                        to="botiquin.pautatoma",
                        verbose_name="Pauta",
                    ),
                ),
            ],
            options={
                "verbose_name": "Horario de toma",
                "verbose_name_plural": "Horarios de toma",
                "ordering": ["orden", "hora"],
            },
        ),
        migrations.AddConstraint(
            model_name="horariotoma",
            constraint=models.UniqueConstraint(
                condition=models.Q(("hora__isnull", False)),
                fields=("pauta", "hora"),
                name="horario_unico_por_pauta",
            ),
        ),
        migrations.AddField(
            model_name="tomaregistrada",
            name="horario",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tomas",
                to="botiquin.horariotoma",
                verbose_name="Horario",
            ),
        ),
        migrations.RunPython(migrar_horarios, revertir_horarios),
        migrations.RemoveConstraint(
            model_name="tomaregistrada",
            name="toma_unica_por_pauta_fecha",
        ),
        migrations.AddConstraint(
            model_name="tomaregistrada",
            constraint=models.UniqueConstraint(
                fields=("horario", "fecha"),
                name="toma_unica_por_horario_fecha",
            ),
        ),
        migrations.AlterField(
            model_name="tomaregistrada",
            name="horario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tomas",
                to="botiquin.horariotoma",
                verbose_name="Horario",
            ),
        ),
        migrations.RemoveField(
            model_name="pautatoma",
            name="hora",
        ),
    ]
