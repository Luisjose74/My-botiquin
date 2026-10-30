from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Hogar, MiembroHogar, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "email", "hogar", "canal_alertas", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Botiquín",
            {"fields": ("telefono", "foto", "canal_alertas", "hogar")},
        ),
    )


@admin.register(Hogar)
class HogarAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo_invitacion", "creado")
    search_fields = ("nombre", "codigo_invitacion")


@admin.register(MiembroHogar)
class MiembroHogarAdmin(admin.ModelAdmin):
    list_display = ("nombre", "hogar", "relacion", "es_principal")
    list_filter = ("relacion", "es_principal")
    search_fields = ("nombre", "hogar__nombre")
