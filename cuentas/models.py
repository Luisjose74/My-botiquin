"""Modelos de usuarios, hogar familiar y miembros de la familia."""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class Hogar(models.Model):
    """
    Cuenta familiar compartida (la encuesta mostró que el 67% quiere
    que varias personas de la familia usen la misma cuenta).
    """

    nombre = models.CharField("Nombre del hogar", max_length=80)
    codigo_invitacion = models.SlugField(
        "Código de invitación", max_length=12, unique=True, blank=True
    )
    creado = models.DateTimeField("Creado el", auto_now_add=True)

    class Meta:
        verbose_name = "Hogar"
        verbose_name_plural = "Hogares"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.codigo_invitacion:
            self.codigo_invitacion = uuid.uuid4().hex[:8]
        super().save(*args, **kwargs)


class Usuario(AbstractUser):
    """Usuario de Mi Botiquín Digital (extiende el auth de Django)."""

    telefono = models.CharField("Teléfono", max_length=20, blank=True)
    foto = models.ImageField(
        "Foto de perfil", upload_to="perfiles/", blank=True, null=True
    )
    # Preferencia de canal de alertas (encuesta: notificación 38%, WhatsApp 29%, correo 29%)
    CANAL_ALERTAS = [
        ("notificacion", "Notificación en la página"),
        ("whatsapp", "WhatsApp"),
        ("correo", "Correo electrónico"),
    ]
    canal_alertas = models.CharField(
        "Canal de alertas",
        max_length=20,
        choices=CANAL_ALERTAS,
        default="notificacion",
    )
    hogar = models.ForeignKey(
        Hogar,
        verbose_name="Hogar",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios",
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def iniciales(self):
        nombre = self.get_full_name() or self.username
        partes = nombre.split()
        return "".join(p[0].upper() for p in partes[:2])


class MiembroHogar(models.Model):
    """Persona que usa los medicamentos del hogar (padre, hijo, mamá...)."""

    RELACIONES = [
        ("principal", "Principal (yo)"),
        ("pareja", "Pareja"),
        ("hijo", "Hijo/a"),
        ("padre", "Padre"),
        ("madre", "Madre"),
        ("abuelo", "Abuelo/a"),
        ("cuidador", "Cuidador/a"),
        ("otro", "Otro"),
    ]

    hogar = models.ForeignKey(
        Hogar,
        verbose_name="Hogar",
        on_delete=models.CASCADE,
        related_name="miembros",
    )
    usuario = models.OneToOneField(
        Usuario,
        verbose_name="Cuenta vinculada",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfil_miembro",
    )
    nombre = models.CharField("Nombre", max_length=80)
    relacion = models.CharField(
        "Relación", max_length=20, choices=RELACIONES, default="principal"
    )
    es_principal = models.BooleanField("Es el perfil principal", default=False)
    creado = models.DateTimeField("Creado el", auto_now_add=True)

    class Meta:
        verbose_name = "Miembro de la familia"
        verbose_name_plural = "Miembros de la familia"
        ordering = ["-es_principal", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["hogar", "nombre"], name="miembro_unico_por_hogar"
            )
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_relacion_display()})"

    @property
    def iniciales(self):
        partes = self.nombre.split()
        return "".join(p[0].upper() for p in partes[:2])
