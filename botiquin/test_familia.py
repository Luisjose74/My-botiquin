from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cuentas.models import MiembroHogar, Usuario

from .alertas import sincronizar_alertas
from .models import Categoria, Medicamento


class FiltroYResumenFamiliarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="familia_inv", password="ClaveSegura123!", first_name="Luis"
        )
        cls.otro = Usuario.objects.create_user(
            username="familia_inv_otro", password="ClaveSegura123!"
        )
        cls.categoria = Categoria.objects.create(nombre="Categoria familiar")
        cls.hijo = MiembroHogar.objects.create(
            hogar=cls.usuario.hogar, nombre="Hijo Pedro", relacion="hijo"
        )
        cls.madre = MiembroHogar.objects.create(
            hogar=cls.usuario.hogar, nombre="Madre Rosa", relacion="madre"
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()

    def crear(self, nombre, miembro, dias=200, cantidad=5):
        return Medicamento.objects.create(
            usuario=self.usuario,
            categoria=self.categoria,
            miembro=miembro,
            nombre=nombre,
            cantidad=cantidad,
            fecha_vencimiento=self.hoy + timedelta(days=dias),
        )

    def test_filtra_inventario_por_integrante(self):
        self.crear("Para el hijo", self.hijo)
        self.crear("Para la madre", self.madre)

        respuesta = self.client.get(reverse("botiquin:lista"), {"miembro": self.hijo.pk})

        nombres = [m.nombre for m in respuesta.context["medicamentos"]]
        self.assertEqual(nombres, ["Para el hijo"])
        self.assertEqual(respuesta.context["miembro_actual"], self.hijo.pk)
        self.assertContains(respuesta, "Limpiar")

    def test_filtro_con_integrante_de_otro_hogar_se_ignora(self):
        ajeno = MiembroHogar.objects.get(hogar=self.otro.hogar, es_principal=True)
        self.crear("Propio", self.hijo)

        respuesta = self.client.get(reverse("botiquin:lista"), {"miembro": ajeno.pk})

        self.assertEqual(respuesta.context["miembro_actual"], "")
        self.assertEqual(len(respuesta.context["medicamentos"]), 1)

    def test_panel_cuenta_atencion_por_integrante(self):
        self.crear("Vencido del hijo", self.hijo, dias=-3)
        self.crear("Stock bajo de la madre", self.madre, cantidad=2)
        self.crear("Sin alerta", self.madre)

        respuesta = self.client.get(reverse("inicio"))

        conteo = {
            item["miembro"].nombre: item["atencion"]
            for item in respuesta.context["integrantes"]
        }
        self.assertEqual(conteo["Hijo Pedro"], 1)
        self.assertEqual(conteo["Madre Rosa"], 1)
        self.assertContains(respuesta, "Mi familia")

    def test_alerta_muestra_el_integrante(self):
        self.crear("Ibuprofeno", self.hijo, dias=-1)
        sincronizar_alertas(self.usuario, notificar=False)

        respuesta = self.client.get(reverse("botiquin:alertas") + "?ver=todas")

        self.assertContains(respuesta, "Para Hijo Pedro")

    def test_correo_de_alerta_incluye_integrante(self):
        from django.core import mail
        from django.test import override_settings

        Usuario.objects.filter(pk=self.usuario.pk).update(
            canal_alertas="correo", email="familia@example.com"
        )
        self.usuario.refresh_from_db()
        self.crear("Jarabe", self.madre, dias=-2)

        with override_settings(
            MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
        ):
            sincronizar_alertas(self.usuario)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("(para Madre Rosa)", mail.outbox[0].body)
