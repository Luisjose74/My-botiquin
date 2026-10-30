"""Señales de Mi Botiquín Digital."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Hogar, MiembroHogar, Usuario


@receiver(post_save, sender=Usuario)
def crear_hogar_y_perfil_principal(sender, instance, created, raw=False, **kwargs):
    """
    Al registrar un usuario se crea automáticamente:
      - su Hogar (cuenta familiar compartida), y
      - su MiembroHogar principal (la persona que usa los medicamentos).
    """
    if raw or not created:
        return

    nombre_completo = instance.get_full_name() or instance.username
    hogar = Hogar.objects.create(nombre=f"Hogar de {nombre_completo}")

    # update() evita volver a disparar post_save sobre el usuario
    Usuario.objects.filter(pk=instance.pk).update(hogar=hogar)
    instance.hogar = hogar

    MiembroHogar.objects.create(
        hogar=hogar,
        usuario=instance,
        nombre=nombre_completo,
        relacion="principal",
        es_principal=True,
    )
