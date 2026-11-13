from django.contrib import admin

from .models import Alerta, Categoria, Clasificacion, Medicamento


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


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "usuario", "tipo", "leida", "creada")
    list_filter = ("tipo", "leida")
    search_fields = ("titulo", "mensaje")
