from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Usuario


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
)
class RecuperacionPasswordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="recuperacion",
            password="ClaveSegura123!",
            email="persona@example.com",
            first_name="Persona",
        )

    def test_solicitar_codigo_envia_correo_y_avanza(self):
        respuesta = self.client.post(
            reverse("cuentas:password_reset"),
            {"email": "PERSONA@EXAMPLE.COM"},
        )

        self.assertRedirects(respuesta, reverse("cuentas:password_reset_verify"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("código", mail.outbox[0].subject.lower())
        self.assertIn("Tu código:", mail.outbox[0].body)
        self.assertEqual(
            self.client.session["password_reset_email"], "persona@example.com"
        )

    def test_correo_no_registrado_no_avanza(self):
        respuesta = self.client.post(
            reverse("cuentas:password_reset"),
            {"email": "no-existe@example.com"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no se encuentra registrado")
        self.assertEqual(len(mail.outbox), 0)

    def test_flujo_completo_con_codigo(self):
        self.client.post(
            reverse("cuentas:password_reset"),
            {"email": self.usuario.email},
        )
        codigo = mail.outbox[0].body.split("Tu código: ")[1].split()[0]

        respuesta = self.client.post(
            reverse("cuentas:password_reset_verify"), {"code": codigo}
        )
        self.assertRedirects(respuesta, reverse("cuentas:password_reset_password"))

        respuesta = self.client.post(
            reverse("cuentas:password_reset_password"),
            {
                "new_password1": "NuevaClaveSegura456!",
                "new_password2": "NuevaClaveSegura456!",
            },
        )
        self.assertRedirects(
            respuesta, reverse("cuentas:password_reset_complete")
        )
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("NuevaClaveSegura456!"))
