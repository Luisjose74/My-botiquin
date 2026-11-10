"""Contenido educativo de Regencia de Farmacia en la app y en los correos."""
from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario

from .models import Categoria, Medicamento

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

FRASES_ESPERADAS = [
    "No consumas medicamentos vencidos",
    "Evita la automedicación",
    "Respeta las condiciones de almacenamiento",
    "No compartas medicamentos",
    "Consulta al personal de salud",
]


@override_settings(EMAIL_BACKEND=LOCMEM)
class ContenidoEducativoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="educativo_usuario",
            password="ClaveSegura123!",
            email="paciente@example.com",
            first_name="Ana",
            canal_alertas="correo",
        )
        cls.categoria = Categoria.objects.create(nombre="Categoria educativa")

    def setUp(self):
        self.hoy = timezone.localdate()
        mail.outbox = []

    def crear(self, nombre, dias, cantidad=5):
        return Medicamento.objects.create(
            usuario=self.usuario,
            categoria=self.categoria,
            nombre=nombre,
            cantidad=cantidad,
            fecha_vencimiento=self.hoy + timedelta(days=dias),
        )

    def test_panel_de_alertas_incluye_las_recomendaciones(self):
        self.client.force_login(self.usuario)
        self.crear("Vencido", -3)

        respuesta = self.client.get(reverse("botiquin:alertas"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Recomendaciones de Regencia de Farmacia")
        for frase in FRASES_ESPERADAS:
            self.assertContains(respuesta, frase)

    def test_dashboard_incluye_las_recomendaciones(self):
        self.client.force_login(self.usuario)

        respuesta = self.client.get(reverse("inicio"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Recomendaciones de Regencia de Farmacia")
        for frase in FRASES_ESPERADAS:
            self.assertContains(respuesta, frase)

    def test_detalle_de_medicamento_vencido_incluye_recomendaciones(self):
        self.client.force_login(self.usuario)
        medicamento = self.crear("Vencido", -5)

        respuesta = self.client.get(
            reverse("botiquin:detalle", args=[medicamento.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Recomendaciones de Regencia de Farmacia")
        self.assertContains(respuesta, "No consumas medicamentos vencidos")

    def test_correo_de_alertas_incluye_las_recomendaciones(self):
        from .alertas import sincronizar_alertas

        self.crear("Ibuprofeno", 12)
        sincronizar_alertas(self.usuario)

        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertIn("RECOMENDACIONES DE REGENCIA DE FARMACIA", correo.body.upper())
        for frase in FRASES_ESPERADAS:
            self.assertIn(frase, correo.body)
        # La versión HTML también las incluye.
        html = correo.alternatives[0][0]
        self.assertIn("Recomendaciones de Regencia de Farmacia", html)
        for frase in FRASES_ESPERADAS:
            self.assertIn(frase, html)
