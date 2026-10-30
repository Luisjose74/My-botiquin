from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario

from .alertas import sincronizar_alertas
from .models import Alerta, Categoria, Medicamento


class AlertasYPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="alertas_usuario", password="ClaveSegura123!"
        )
        cls.otro = Usuario.objects.create_user(
            username="alertas_otro", password="ClaveSegura123!"
        )
        cls.categoria = Categoria.objects.create(nombre="Categoria de alertas")

    def setUp(self):
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()

    def crear(self, nombre, dias, cantidad=5, usuario=None):
        return Medicamento.objects.create(
            usuario=usuario or self.usuario,
            categoria=self.categoria,
            nombre=nombre,
            cantidad=cantidad,
            fecha_vencimiento=self.hoy + timedelta(days=dias),
        )

    def test_sincroniza_un_tipo_de_alerta_por_estado(self):
        self.crear("Vigente", 200)
        self.crear("Por vencer", 10)
        self.crear("Vencido", -5)
        self.crear("Agotado", 200, cantidad=0)

        sincronizar_alertas(self.usuario)

        tipos = dict(
            Alerta.objects.filter(usuario=self.usuario).values_list(
                "medicamento__nombre", "tipo"
            )
        )
        self.assertEqual(
            tipos,
            {
                "Por vencer": "por_vencer",
                "Vencido": "vencido",
                "Agotado": "agotado",
            },
        )

    def test_sincronizar_no_duplica_alertas(self):
        self.crear("Repetido", 10)
        sincronizar_alertas(self.usuario)
        resultado = sincronizar_alertas(self.usuario)

        self.assertEqual(resultado, {"creadas": 0, "eliminadas": 0})
        self.assertEqual(Alerta.objects.filter(usuario=self.usuario).count(), 1)

    def test_alerta_leida_no_vuelve_a_crearse(self):
        medicamento = self.crear("Leido", 10)
        sincronizar_alertas(self.usuario)
        Alerta.objects.filter(usuario=self.usuario).update(leida=True)

        sincronizar_alertas(self.usuario)

        self.assertTrue(Alerta.objects.get(medicamento=medicamento).leida)

    def test_cambio_de_estado_reemplaza_la_alerta(self):
        medicamento = self.crear("Cambiante", 10)
        sincronizar_alertas(self.usuario)

        medicamento.fecha_vencimiento = self.hoy - timedelta(days=2)
        medicamento.save()
        resultado = sincronizar_alertas(self.usuario)

        self.assertEqual(resultado, {"creadas": 1, "eliminadas": 1})
        self.assertEqual(Alerta.objects.get(medicamento=medicamento).tipo, "vencido")

    def test_quitar_del_riesgo_elimina_la_alerta(self):
        medicamento = self.crear("Recuperado", -3)
        sincronizar_alertas(self.usuario)

        medicamento.fecha_vencimiento = self.hoy + timedelta(days=300)
        medicamento.save()
        sincronizar_alertas(self.usuario)

        self.assertFalse(Alerta.objects.filter(medicamento=medicamento).exists())

    def test_panel_muestra_resumen_y_alertas(self):
        self.crear("Panel vencido", -1)
        respuesta = self.client.get(reverse("inicio"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["total_alertas"], 1)
        self.assertContains(respuesta, "Panel vencido")
        self.assertContains(respuesta, "Requieren atención")

    def test_panel_requiere_login(self):
        self.client.logout()
        respuesta = self.client.get(reverse("inicio"))
        self.assertEqual(respuesta.status_code, 302)

    def test_marcar_leida_requiere_post(self):
        self.crear("Marcar", -1)
        sincronizar_alertas(self.usuario)
        alerta = Alerta.objects.get(usuario=self.usuario)
        url = reverse("botiquin:alerta_leida", args=[alerta.pk])

        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertFalse(Alerta.objects.get(pk=alerta.pk).leida)

        self.client.post(url)
        self.assertTrue(Alerta.objects.get(pk=alerta.pk).leida)

    def test_no_marca_alertas_de_otro_usuario(self):
        self.crear("Ajeno", -1, usuario=self.otro)
        sincronizar_alertas(self.otro)
        alerta = Alerta.objects.get(usuario=self.otro)

        respuesta = self.client.post(
            reverse("botiquin:alerta_leida", args=[alerta.pk])
        )
        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(Alerta.objects.get(pk=alerta.pk).leida)

    def test_marcar_todas_leidas(self):
        self.crear("Uno", -1)
        self.crear("Dos", 10)
        sincronizar_alertas(self.usuario)

        self.client.post(reverse("botiquin:alertas_leer_todas"))

        self.assertEqual(
            Alerta.objects.filter(usuario=self.usuario, leida=False).count(), 0
        )

    def test_redireccion_next_solo_interna(self):
        self.crear("Redir", -1)
        sincronizar_alertas(self.usuario)
        alerta = Alerta.objects.get(usuario=self.usuario)
        url = reverse("botiquin:alerta_leida", args=[alerta.pk])

        externo = self.client.post(url, {"next": "https://evil.example.com/"})
        self.assertEqual(externo.url, reverse("botiquin:alertas"))

        interno = self.client.post(url, {"next": reverse("inicio")})
        self.assertEqual(interno.url, reverse("inicio"))

    def test_comando_sincronizar_alertas(self):
        self.crear("Comando", -1)
        salida = StringIO()

        call_command("sincronizar_alertas", stdout=salida)

        self.assertIn("Alertas creadas: 1", salida.getvalue())
        self.assertTrue(
            Alerta.objects.filter(usuario=self.usuario, tipo="vencido").exists()
        )
