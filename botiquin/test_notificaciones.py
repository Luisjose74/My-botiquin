from datetime import timedelta
from io import StringIO
from smtplib import SMTPException
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario

from .alertas import sincronizar_alertas
from .models import Alerta, Categoria, Medicamento

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=LOCMEM)
class StockBajoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="stock_usuario", password="ClaveSegura123!"
        )
        cls.categoria = Categoria.objects.create(nombre="Categoria de stock")

    def setUp(self):
        self.hoy = timezone.localdate()

    def crear(self, nombre, dias, cantidad):
        return Medicamento.objects.create(
            usuario=self.usuario,
            categoria=self.categoria,
            nombre=nombre,
            cantidad=cantidad,
            fecha_vencimiento=self.hoy + timedelta(days=dias),
        )

    def tipos(self):
        return dict(
            Alerta.objects.filter(usuario=self.usuario).values_list(
                "medicamento__nombre", "tipo"
            )
        )

    def test_stock_bajo_con_dos_unidades_o_menos(self):
        self.crear("Dos", 200, 2)
        self.crear("Uno", 200, 1)
        self.crear("Tres", 200, 3)
        self.crear("Cero", 200, 0)

        sincronizar_alertas(self.usuario, notificar=False)

        self.assertEqual(
            self.tipos(), {"Dos": "stock_bajo", "Uno": "stock_bajo", "Cero": "agotado"}
        )

    def test_por_vencer_tiene_prioridad_sobre_stock_bajo(self):
        self.crear("Prioritario", 10, 1)

        sincronizar_alertas(self.usuario, notificar=False)

        self.assertEqual(self.tipos(), {"Prioritario": "por_vencer_15"})

    def test_recuperar_stock_elimina_la_alerta(self):
        medicamento = self.crear("Repuesto", 200, 2)
        sincronizar_alertas(self.usuario, notificar=False)

        medicamento.cantidad = 5
        medicamento.save()
        resultado = sincronizar_alertas(self.usuario, notificar=False)

        self.assertEqual(resultado["archivadas"], 1)
        self.assertEqual(resultado["eliminadas"], 0)
        alerta = Alerta.objects.get(medicamento=medicamento)
        self.assertTrue(alerta.archivada)
        self.assertFalse(
            Alerta.objects.filter(usuario=self.usuario, leida=False).exists()
        )

    def test_panel_muestra_stock_bajo(self):
        self.crear("Pocas unidades", 200, 2)
        self.client.force_login(self.usuario)

        respuesta = self.client.get(reverse("inicio"))

        self.assertContains(respuesta, "Pocas unidades")
        self.assertContains(respuesta, "Quedan 2")
        self.assertContains(respuesta, "Stock bajo")


@override_settings(EMAIL_BACKEND=LOCMEM, SITE_URL="https://demo.ngrok-free.app")
class NotificacionesCorreoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nombre="Categoria de correo")
        cls.usuario = Usuario.objects.create_user(
            username="correo_usuario",
            password="ClaveSegura123!",
            email="paciente@example.com",
            first_name="Ana",
            canal_alertas="correo",
        )
        cls.otro = Usuario.objects.create_user(
            username="correo_otro",
            password="ClaveSegura123!",
            email="otro@example.com",
            canal_alertas="correo",
        )

    def setUp(self):
        self.hoy = timezone.localdate()
        mail.outbox = []

    def crear(self, nombre, dias, cantidad=5, usuario=None):
        return Medicamento.objects.create(
            usuario=usuario or self.usuario,
            categoria=self.categoria,
            nombre=nombre,
            cantidad=cantidad,
            fecha_vencimiento=self.hoy + timedelta(days=dias),
        )

    def test_envia_un_correo_con_las_alertas_nuevas(self):
        self.crear("Ibuprofeno", -2)
        self.crear("Amoxicilina", 10)

        sincronizar_alertas(self.usuario)

        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ["paciente@example.com"])
        self.assertIn("2 alertas nuevas", correo.subject)
        self.assertIn("Ibuprofeno: vencido", correo.body)
        self.assertIn("Amoxicilina: vence en 15 días", correo.body)
        self.assertIn("https://demo.ngrok-free.app/botiquin/alertas/", correo.body)
        self.assertEqual(len(correo.alternatives), 1)

    def test_no_reenvia_alertas_ya_notificadas(self):
        self.crear("Repetido", -1)
        sincronizar_alertas(self.usuario)
        sincronizar_alertas(self.usuario)

        self.assertEqual(len(mail.outbox), 1)

    def test_canal_notificacion_no_envia_correo(self):
        Usuario.objects.filter(pk=self.usuario.pk).update(
            canal_alertas="notificacion"
        )
        self.usuario.refresh_from_db()
        self.crear("Solo en app", -1)

        sincronizar_alertas(self.usuario)

        self.assertEqual(mail.outbox, [])
        self.assertEqual(Alerta.objects.filter(usuario=self.usuario).count(), 1)

    def test_sin_correo_no_falla(self):
        Usuario.objects.filter(pk=self.usuario.pk).update(email="")
        self.usuario.refresh_from_db()
        self.crear("Sin correo", -1)

        resultado = sincronizar_alertas(self.usuario)

        self.assertEqual(resultado["creadas"], 1)
        self.assertEqual(mail.outbox, [])

    def test_error_smtp_no_rompe_el_panel(self):
        self.crear("Con error", -1)
        self.client.force_login(self.usuario)

        with mock.patch(
            "django.core.mail.message.EmailMessage.send",
            side_effect=SMTPException("servidor no disponible"),
        ):
            respuesta = self.client.get(reverse("inicio"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(
            Alerta.objects.filter(usuario=self.usuario, medicamento__nombre="Con error").exists()
        )

    def test_correo_solo_incluye_alertas_del_propio_usuario(self):
        self.crear("Mio", -1)
        self.crear("Ajeno", -1, usuario=self.otro)

        sincronizar_alertas(self.usuario)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Mio", mail.outbox[0].body)
        self.assertNotIn("Ajeno", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["paciente@example.com"])

    def test_comando_envia_correos(self):
        self.crear("Por comando", -1)
        salida = StringIO()

        call_command("sincronizar_alertas", stdout=salida)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Alertas creadas: 1", salida.getvalue())
