from django.contrib import admin

from .models import (
    Alerta,
    Categoria,
    Clasificacion,
    HorarioToma,
    Medicamento,
    PautaToma,
)


@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre_completo",
        "clasificacion",
        "categoria",
        "usuario",
        "cantidad",
        "ubicacion",
        "fecha_vencimiento",
        "estado",
        "activo",
    )
    list_filter = (
        "condicion_almacenamiento",
        "presentacion",
        "clasificacion",
        "categoria",
        "activo",
    )
    search_fields = ("nombre", "concentracion", "registro_sanitario", "lote")
    list_editable = ("cantidad", "activo")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "icono")
    search_fields = ("nombre",)


@admin.register(Clasificacion)
class ClasificacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "icono", "orden")
    list_editable = ("orden",)
    search_fields = ("nombre",)
    ordering = ("orden", "nombre")


@admin.register(HorarioToma)
class HorarioTomaAdmin(admin.ModelAdmin):
    list_display = ("pauta", "hora", "orden")
    list_filter = ("hora",)
    ordering = ("pauta", "orden", "hora")


class HorarioTomaInline(admin.TabularInline):
    """Horarios de la pauta: se editan en línea desde la pauta."""

    model = HorarioToma
    extra = 1
    fields = ("hora", "orden")
    ordering = ("orden", "hora")


@admin.register(PautaToma)
class PautaTomaAdmin(admin.ModelAdmin):
    list_display = (
        "medicamento",
        "miembro",
        "frecuencia",
        "dosis",
        "resumen_horarios_admin",
        "activa",
    )
    list_filter = ("frecuencia", "activa")
    search_fields = ("medicamento__nombre", "miembro__nombre")
    inlines = [HorarioTomaInline]

    @admin.display(description="Horarios")
    def resumen_horarios_admin(self, obj):
        return obj.resumen_horarios


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "usuario", "tipo", "leida", "creada")
    list_filter = ("tipo", "leida")
    search_fields = ("titulo", "mensaje")
