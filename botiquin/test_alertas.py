from datetime import timedelta
from io import StringIO
from unittest.mock import patch

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
                "Por vencer": "por_vencer_15",
                "Vencido": "vencido",
                "Agotado": "agotado",
            },
        )

    def test_cada_hito_de_vencimiento_tiene_su_alerta(self):
        """Los avisos se escalonan en 30, 15 y 5 días antes de caducar."""
        self.crear("A 30 días", 30)
        self.crear("A 15 días", 15)
        self.crear("A 5 días", 5)
        self.crear("A 6 días", 6)
        self.crear("A 31 días", 31)

        sincronizar_alertas(self.usuario)

        tipos = dict(
            Alerta.objects.filter(usuario=self.usuario).values_list(
                "medicamento__nombre", "tipo"
            )
        )
        self.assertEqual(
            tipos,
            {
                "A 30 días": "por_vencer_30",
                "A 15 días": "por_vencer_15",
                "A 5 días": "por_vencer_5",
                "A 6 días": "por_vencer_15",
            },
        )

    def test_hito_superado_se_archiva(self):
        """Al entrar en la ventana de 15 días, el aviso de 30 queda archivado."""
        medicamento = self.crear("Cambio de hito", 30)
        sincronizar_alertas(self.usuario)

        alerta_30 = Alerta.objects.get(medicamento=medicamento, tipo="por_vencer_30")
        self.assertFalse(alerta_30.archivada)

        medicamento.fecha_vencimiento = self.hoy + timedelta(days=12)
        medicamento.save()
        resultado = sincronizar_alertas(self.usuario)

        alerta_30.refresh_from_db()
        self.assertTrue(alerta_30.archivada)
        self.assertTrue(alerta_30.leida)
        self.assertEqual(resultado["archivadas"], 1)
        self.assertTrue(
            Alerta.objects.filter(
                medicamento=medicamento, tipo="por_vencer_15", archivada=False
            ).exists()
        )
        # En el panel solo queda vigente el aviso más próximo.
        pendientes = Alerta.objects.filter(
            usuario=self.usuario, leida=False, archivada=False
        )
        self.assertEqual(pendientes.count(), 1)
        self.assertEqual(pendientes.first().tipo, "por_vencer_15")

    def test_hito_5_se_activa_y_el_de_15_queda_archivado(self):
        medicamento = self.crear("Ultimos dias", 12)
        sincronizar_alertas(self.usuario)

        medicamento.fecha_vencimiento = self.hoy + timedelta(days=3)
        medicamento.save()
        sincronizar_alertas(self.usuario)

        self.assertTrue(
            Alerta.objects.filter(
                medicamento=medicamento, tipo="por_vencer_5", archivada=False
            ).exists()
        )
        self.assertTrue(
            Alerta.objects.filter(medicamento=medicamento, tipo="por_vencer_15").first().archivada
        )

    def test_alerta_vencida_es_permanente(self):
        """El aviso de vencido permanece hasta que el medicamento se disponga."""
        medicamento = self.crear("Vencido permanente", -10)
        sincronizar_alertas(self.usuario)
        sincronizar_alertas(self.usuario)

        alerta = Alerta.objects.get(medicamento=medicamento, tipo="vencido")
        self.assertFalse(alerta.archivada)
        self.assertFalse(alerta.leida)
        self.assertEqual(
            Alerta.objects.filter(medicamento=medicamento, tipo="vencido").count(), 1
        )

    def test_sincronizar_no_duplica_alertas(self):
        self.crear("Repetido", 10)
        sincronizar_alertas(self.usuario)
        resultado = sincronizar_alertas(self.usuario)

        self.assertEqual(
            resultado,
            {"creadas": 0, "archivadas": 0, "eliminadas": 0, "reactivadas": 0},
        )
        self.assertEqual(Alerta.objects.filter(usuario=self.usuario).count(), 1)

    def test_alerta_leida_no_vuelve_a_crearse(self):
        medicamento = self.crear("Leido", 10)
        sincronizar_alertas(self.usuario)
        Alerta.objects.filter(usuario=self.usuario).update(leida=True)

        sincronizar_alertas(self.usuario)

        self.assertTrue(Alerta.objects.get(medicamento=medicamento).leida)

    def test_cambio_de_estado_crea_alerta_nueva_y_archiva_la_anterior(self):
        medicamento = self.crear("Cambiante", 10)
        sincronizar_alertas(self.usuario)

        medicamento.fecha_vencimiento = self.hoy - timedelta(days=2)
        medicamento.save()
        resultado = sincronizar_alertas(self.usuario)

        self.assertEqual(resultado["creadas"], 1)
        self.assertEqual(resultado["archivadas"], 1)
        self.assertEqual(resultado["eliminadas"], 0)
        vencida = Alerta.objects.get(medicamento=medicamento, tipo="vencido")
        self.assertFalse(vencida.archivada)

    def test_quitar_del_riesgo_archiva_la_alerta(self):
        medicamento = self.crear("Recuperado", -3)
        sincronizar_alertas(self.usuario)

        medicamento.fecha_vencimiento = self.hoy + timedelta(days=300)
        medicamento.save()
        resultado = sincronizar_alertas(self.usuario)

        self.assertEqual(resultado["archivadas"], 1)
        alerta = Alerta.objects.get(medicamento=medicamento)
        self.assertTrue(alerta.archivada)
        self.assertFalse(
            Alerta.objects.filter(usuario=self.usuario, leida=False).exists()
        )

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


class AlertasAsignacionMiembroTests(TestCase):
    """Alertas para medicamentos asignados a miembros del hogar."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user(
            username="alertas_admin", password="ClaveSegura123!",
            first_name="Admin", last_name="Hogar",
        )
        cls.miembro_user = Usuario.objects.create_user(
            username="alertas_miembro", password="ClaveSegura123!",
            first_name="Miembro", last_name="Hogar",
            email="miembro@example.com",
            canal_alertas="correo",
        )
        # Vincular miembro al hogar del admin
        cls.miembro_user.hogar = cls.admin.hogar
        cls.miembro_user.save(update_fields=["hogar"])
        miembro = cls.miembro_user.perfil_miembro
        miembro.hogar = cls.admin.hogar
        miembro.nombre = "Miembro Hogar"
        miembro.relacion = "otro"
        miembro.es_principal = False
        miembro.save()

        cls.categoria = Categoria.objects.create(nombre="Cat alertas")

    def setUp(self):
        self.hoy = timezone.localdate()

    def test_alerta_para_medicamento_asignado_a_miembro(self):
        """Un medicamento vencido asignado a un miembro genera alerta para ese miembro."""
        med = Medicamento.objects.create(
            usuario=self.admin,
            categoria=self.categoria,
            nombre="Medicamento asignado",
            cantidad=5,
            fecha_vencimiento=self.hoy - timedelta(days=2),
            miembro=self.miembro_user.perfil_miembro,
        )

        sincronizar_alertas(self.miembro_user)

        self.assertTrue(
            Alerta.objects.filter(
                usuario=self.miembro_user, medicamento=med, tipo="vencido"
            ).exists()
        )

    def test_alerta_no_duplica_para_mismo_medicamento(self):
        """Llamar sincronizar_alertas dos veces no crea alertas duplicadas."""
        med = Medicamento.objects.create(
            usuario=self.admin,
            categoria=self.categoria,
            nombre="Sin duplicar",
            cantidad=5,
            fecha_vencimiento=self.hoy - timedelta(days=2),
            miembro=self.miembro_user.perfil_miembro,
        )

        r1 = sincronizar_alertas(self.miembro_user)
        r2 = sincronizar_alertas(self.miembro_user)

        self.assertEqual(r1["creadas"], 1)
        self.assertEqual(r2["creadas"], 0)
        self.assertEqual(
            Alerta.objects.filter(usuario=self.miembro_user, medicamento=med).count(),
            1,
        )

    def test_notificada_evita_reenvio_correo(self):
        """Una alerta ya notificada no se vuelve a notificar por correo."""
        from botiquin.alertas import sincronizar_alertas as sinc

        med = Medicamento.objects.create(
            usuario=self.admin,
            categoria=self.categoria,
            nombre="Notificada",
            cantidad=5,
            fecha_vencimiento=self.hoy - timedelta(days=2),
            miembro=self.miembro_user.perfil_miembro,
        )

        sinc(self.miembro_user)
        alerta = Alerta.objects.get(usuario=self.miembro_user, medicamento=med)
        alerta.notificada = True
        alerta.save(update_fields=["notificada"])

        with patch("botiquin.alertas.enviar_alertas_por_correo") as mock_correo:
            sinc(self.miembro_user, notificar=True)
            mock_correo.assert_not_called()

    def test_notificada_se_marca_despues_de_enviar(self):
        """Después de enviar el correo, la alerta queda marcada como notificada."""
        from botiquin.alertas import sincronizar_alertas as sinc

        med = Medicamento.objects.create(
            usuario=self.admin,
            categoria=self.categoria,
            nombre="Marca notificada",
            cantidad=5,
            fecha_vencimiento=self.hoy - timedelta(days=2),
            miembro=self.miembro_user.perfil_miembro,
        )

        with patch("botiquin.alertas.enviar_alertas_por_correo", return_value=True):
            sinc(self.miembro_user, notificar=True)

        alerta = Alerta.objects.get(usuario=self.miembro_user, medicamento=med)
        self.assertTrue(alerta.notificada)
