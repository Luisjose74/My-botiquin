from django.contrib import admin

from .models import Alerta, Categoria, Medicamento


@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "usuario",
        "cantidad",
        "fecha_vencimiento",
        "estado",
        "activo",
    )
    list_filter = ("condicion_almacenamiento", "presentacion", "activo")
    search_fields = ("nombre", "registro_sanitario", "lote")
    list_editable = ("cantidad", "activo")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "icono")
    search_fields = ("nombre",)


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "usuario", "tipo", "leida", "creada")
    list_filter = ("tipo", "leida")
    search_fields = ("titulo", "mensaje")
