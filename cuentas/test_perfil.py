from django.test import TestCase
from django.urls import reverse

from .forms import PerfilForm
from .models import Usuario


class CanalAlertasPerfilTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="perfil_canal", password="ClaveSegura123!", email="p@example.com"
        )

    def test_whatsapp_no_aparece_como_opcion(self):
        form = PerfilForm(instance=self.usuario)
        valores = [valor for valor, _ in form.fields["canal_alertas"].choices]

        self.assertIn("notificacion", valores)
        self.assertIn("correo", valores)
        self.assertNotIn("whatsapp", valores)

    def test_no_acepta_whatsapp_al_guardar(self):
        form = PerfilForm(
            data={
                "first_name": "Ana",
                "last_name": "",
                "email": "p@example.com",
                "telefono": "",
                "canal_alertas": "whatsapp",
            },
            instance=self.usuario,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("canal_alertas", form.errors)

    def test_usuario_con_whatsapp_guardado_ve_notificacion(self):
        Usuario.objects.filter(pk=self.usuario.pk).update(canal_alertas="whatsapp")
        self.usuario.refresh_from_db()

        form = PerfilForm(instance=self.usuario)

        self.assertEqual(form["canal_alertas"].value(), "notificacion")

    def test_pagina_perfil_no_muestra_whatsapp(self):
        self.client.force_login(self.usuario)

        respuesta = self.client.get(reverse("cuentas:perfil"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "WhatsApp")
