"""Clasificación de uso de los medicamentos y registro detallado.

- Nuevo modelo `Clasificacion` (tratamiento crónico, antigripal, uso
  ocasional…) con su catálogo inicial.
- Nuevos campos en `Medicamento`: `concentracion`, `indicacion_prescrita` y
  la relación con `Clasificacion`.
"""
import django.db.models.deletion
from django.db import migrations, models

#: Catálogo inicial de clasificaciones de uso.
CLASIFICACIONES = [
    {
        "nombre": "Tratamiento crónico",
        "icono": "💊",
        "descripcion": "Medicamentos de uso prolongado para enfermedades crónicas.",
        "orden": 1,
    },
    {
        "nombre": "Antigripal",
        "icono": "🤧",
        "descripcion": "Para resfriados, gripe y síntomas de temporada.",
        "orden": 2,
    },
    {
        "nombre": "Uso ocasional",
        "icono": "🩹",
        "descripcion": "Para dolor, alergias o malestares puntuales.",
        "orden": 3,
    },
]


def crear_clasificaciones(apps, schema_editor):
    Clasificacion = apps.get_model("botiquin", "Clasificacion")
    for datos in CLASIFICACIONES:
        Clasificacion.objects.get_or_create(
            nombre=datos["nombre"],
            defaults={
                "icono": datos["icono"],
                "descripcion": datos["descripcion"],
                "orden": datos["orden"],
            },
        )


def eliminar_clasificaciones(apps, schema_editor):
    Clasificacion = apps.get_model("botiquin", "Clasificacion")
    Clasificacion.objects.filter(
        nombre__in=[d["nombre"] for d in CLASIFICACIONES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("botiquin", "0009_convertir_alertas_por_vencer"),
    ]

    operations = [
        migrations.CreateModel(
            name="Clasificacion",
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
                    "nombre",
                    models.CharField(
                        max_length=60, unique=True, verbose_name="Nombre"
                    ),
                ),
                (
                    "icono",
                    models.CharField(default="💊", max_length=10, verbose_name="Icono"),
                ),
                (
                    "descripcion",
                    models.CharField(
                        blank=True,
                        help_text="Se muestra como ayuda al elegir la clasificación.",
                        max_length=160,
                        verbose_name="Descripción",
                    ),
                ),
                ("orden", models.PositiveSmallIntegerField(default=0, verbose_name="Orden")),
            ],
            options={
                "verbose_name": "Clasificación de uso",
                "verbose_name_plural": "Clasificaciones de uso",
                "ordering": ["orden", "nombre"],
            },
        ),
        migrations.AddField(
            model_name="medicamento",
            name="concentracion",
            field=models.CharField(
                blank=True,
                help_text="Ej.: 500 mg, 125 mg/5 mL, 1 g.",
                max_length=60,
                verbose_name="Concentración",
            ),
        ),
        migrations.AddField(
            model_name="medicamento",
            name="indicacion_prescrita",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Registra solo lo que te indicó tu médico o tu regente de "
                    "farmacia. Mi Botiquín Digital no sugiere tratamientos ni "
                    "dosis."
                ),
                verbose_name="Indicación prescrita",
            ),
        ),
        migrations.AlterField(
            model_name="medicamento",
            name="notas",
            field=models.TextField(blank=True, verbose_name="Observaciones"),
        ),
        migrations.AlterField(
            model_name="medicamento",
            name="presentacion",
            field=models.CharField(
                choices=[
                    ("tableta", "Tabletas"),
                    ("comprimido", "Comprimido o gragea"),
                    ("capsula", "Cápsulas"),
                    ("suspension", "Suspensión"),
                    ("solucion", "Solución"),
                    ("crema", "Crema / ungüento"),
                    ("gota", "Gotas"),
                    ("aerosol", "Aerosol"),
                    ("inyectable", "Inyectable"),
                    ("supositorio", "Supositorio"),
                    ("parche", "Parche"),
                    ("polvo", "Polvo o sobre"),
                    ("otro", "Otro"),
                ],
                default="tableta",
                max_length=20,
                verbose_name="Forma farmacéutica",
            ),
        ),
        migrations.AlterField(
            model_name="medicamento",
            name="registro_sanitario",
            field=models.CharField(
                blank=True,
                help_text="Déjalo vacío si no lo tienes a la mano.",
                max_length=60,
                verbose_name="Registro INVIMA",
            ),
        ),
        migrations.AddField(
            model_name="medicamento",
            name="clasificacion",
            field=models.ForeignKey(
                blank=True,
                help_text="Tratamiento crónico, antigripal, uso ocasional…",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="medicamentos",
                to="botiquin.clasificacion",
                verbose_name="Clasificación de uso",
            ),
        ),
        migrations.RunPython(crear_clasificaciones, eliminar_clasificaciones),
    ]
