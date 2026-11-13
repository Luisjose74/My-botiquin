"""Integración del directorio de Puntos Azules en el flujo del panel privado.

Comprueba que el usuario autenticado encuentre dónde entregar los
medicamentos vencidos: en la barra de navegación, en las alertas de
vencimiento y en el correo de notificación.
"""
from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario

from .alertas import sincronizar_alertas
from .models import Categoria, Medicamento

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

TEXTO_ENLACE = "Ver Puntos Azules en Sogamoso para su desecho seguro"


@override_settings(EMAIL_BACKEND=LOCMEM)
class IntegracionPuntosAzulesTests(TestCase):
    """El directorio de Puntos Azules dentro de la app autenticada."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="azules_usuario",
            password="ClaveSegura123!",
            email="azules@example.com",
            first_name="Ana",
            canal_alertas="correo",
        )
        cls.categoria = Categoria.objects.create(nombre="Categoría de prueba")

    def setUp(self):
        self.client.force_login(self.usuario)
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

    # ------------------ 1. Barra de navegación ------------------
    def test_la_barra_del_panel_enlaza_al_directorio(self):
        respuesta = self.client.get(reverse("inicio"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, reverse("publico:puntos_azules"))
        self.assertContains(respuesta, "Puntos Azules")

    def test_la_barra_del_panel_aparece_en_las_paginas_privadas(self):
        for nombre in ("botiquin:alertas", "botiquin:lista", "botiquin:tomas_hoy"):
            with self.subTest(pagina=nombre):
                respuesta = self.client.get(reverse(nombre))
                self.assertContains(respuesta, reverse("publico:puntos_azules"))

    # ------------------ 2. Alertas de vencidos ------------------
    def test_la_alerta_de_vencido_muestra_el_enlace(self):
        self.crear("Vencido", -5)
        sincronizar_alertas(self.usuario)

        respuesta = self.client.get(reverse("botiquin:alertas"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, TEXTO_ENLACE)
        self.assertContains(
            respuesta, f'{reverse("publico:puntos_azules")}#directorio'
        )

    def test_el_panel_principal_tambien_muestra_el_enlace(self):
        self.crear("Vencido", -5)
        sincronizar_alertas(self.usuario)

        respuesta = self.client.get(reverse("inicio"))

        self.assertContains(respuesta, TEXTO_ENLACE)

    def test_las_otras_alertas_no_muestran_el_enlace(self):
        self.crear("Por vencer", 10)
        self.crear("Agotado", 200, cantidad=0)

        sincronizar_alertas(self.usuario)

        respuesta = self.client.get(reverse("botiquin:alertas"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, TEXTO_ENLACE)

    def test_la_ficha_del_medicamento_vencido_muestra_el_enlace(self):
        vencido = self.crear("Vencido", -5)

        respuesta = self.client.get(reverse("botiquin:detalle", args=[vencido.pk]))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, TEXTO_ENLACE)

    def test_la_ficha_de_un_medicamento_vigente_no_muestra_el_enlace(self):
        vigente = self.crear("Vigente", 200)

        respuesta = self.client.get(reverse("botiquin:detalle", args=[vigente.pk]))

        self.assertNotContains(respuesta, TEXTO_ENLACE)

    # ------------------ 3. Correo de vencimiento ------------------
    def test_el_correo_de_vencimiento_incluye_el_enlace(self):
        self.crear("Vencido", -5)

        sincronizar_alertas(self.usuario)

        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertIn(TEXTO_ENLACE, correo.body)
        self.assertIn("puntos-azules", correo.body)

        html = correo.alternatives[0][0]
        self.assertIn(TEXTO_ENLACE, html)
        self.assertIn("puntos-azules", html)

    def test_el_correo_sin_vencidos_no_incluye_el_enlace(self):
        self.crear("Por vencer", 10)

        sincronizar_alertas(self.usuario)

        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn(TEXTO_ENLACE, mail.outbox[0].body)
        self.assertNotIn(TEXTO_ENLACE, mail.outbox[0].alternatives[0][0])

    def test_el_correo_usa_la_url_absoluta_del_directorio(self):
        self.crear("Vencido", -5)

        with override_settings(SITE_URL="https://demo.example.com"):
            sincronizar_alertas(self.usuario)

        self.assertEqual(len(mail.outbox), 1)
        cuerpo = mail.outbox[0].body
        self.assertIn(
            "https://demo.example.com/puntos-azules/#directorio",
            cuerpo,
        )
