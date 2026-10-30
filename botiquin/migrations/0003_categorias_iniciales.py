from django.db import migrations

CATEGORIAS = [
    ("Analgésicos", "💊"),
    ("Antibióticos", "🦠"),
    ("Antiinflamatorios", "🔥"),
    ("Digestivos", "🍃"),
    ("Vitaminas", "🍊"),
    ("Alergias", "🤧"),
    ("Cuidado de la piel", "🧴"),
    ("Otros", "📦"),
]


def crear_categorias(apps, schema_editor):
    Categoria = apps.get_model("botiquin", "Categoria")
    for nombre, icono in CATEGORIAS:
        Categoria.objects.get_or_create(
            nombre=nombre, defaults={"icono": icono}
        )


def eliminar_categorias(apps, schema_editor):
    Categoria = apps.get_model("botiquin", "Categoria")
    Categoria.objects.filter(nombre__in=[n for n, _ in CATEGORIAS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("botiquin", "0002_medicamento_ubicacion"),
    ]

    operations = [
        migrations.RunPython(crear_categorias, eliminar_categorias),
    ]
