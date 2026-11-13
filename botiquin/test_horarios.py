"""Horarios múltiples de toma por pauta.

Verifica que una pauta pueda programar varias horas al día, que cada horario
genere su propio recordatorio y que las tomas se confirmen por separado.
"""
import datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario

from .forms import PautaTomaForm
from .models import HorarioToma, Medicamento, PautaToma, TomaRegistrada

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


class HorariosMultiplesTests(TestCase):
    """Programación de varias horas diarias en una misma pauta."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="horarios_usuario",
            password="ClaveSegura123!",
            email="horarios@example.com",
            first_name="Ana",
        )
        cls.miembro = cls.usuario.hogar.miembros.get(es_principal=True)
        cls.medicamento = Medicamento.objects.create(
            usuario=cls.usuario,
            nombre="Metformina",
            concentracion="850 mg",
            cantidad=30,
            fecha_vencimiento=timezone.localdate() + datetime.timedelta(days=200),
        )

    def datos(self, **cambios):
        base = {
            "medicamento": self.medicamento.pk,
            "miembro": self.miembro.pk,
            "dosis": 1,
            "frecuencia": "diaria",
            "intervalo_dias": 1,
            "dias_mes": "",
            "dias_semana": "",
            "fecha_inicio": timezone.localdate().isoformat(),
            "fecha_fin": "",
            "activa": "on",
        }
        base.update(cambios)
        return base

    # ------------------ Formulario ------------------
    def test_una_pauta_puede_crear_varios_horarios(self):
        form = PautaTomaForm(
            self.datos(horarios=["07:00", "12:00", "19:00"]),
            usuario=self.usuario,
        )

        self.assertTrue(form.is_valid(), form.errors)
        pauta = form.save()

        horas = [h.hora.strftime("%H:%M") for h in pauta.horarios.all()]
        self.assertEqual(horas, ["07:00", "12:00", "19:00"])
        self.assertEqual(pauta.numero_tomas, 3)
        self.assertEqual(pauta.resumen_horarios, "07:00, 12:00 y 19:00")

    def test_crear_la_pauta_desde_la_vista(self):
        self.client.force_login(self.usuario)

        respuesta = self.client.post(
            reverse("botiquin:pauta_crear"),
            self.datos(horarios=["07:00", "19:00"]),
        )

        self.assertRedirects(respuesta, reverse("botiquin:pautas_lista"))
        pauta = PautaToma.objects.get(medicamento=self.medicamento)
        self.assertEqual(pauta.horarios.count(), 2)

    def test_editar_agrega_y_quita_horarios(self):
        form = PautaTomaForm(
            self.datos(horarios=["07:00", "19:00"]), usuario=self.usuario
        )
        pauta = form.save()

        # Se cambia a tres horarios (añade el del mediodía).
        form = PautaTomaForm(
            self.datos(horarios=["07:00", "12:00", "19:00"]),
            instance=pauta,
            usuario=self.usuario,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        horas = [h.hora.strftime("%H:%M") for h in pauta.horarios.all()]
        self.assertEqual(horas, ["07:00", "12:00", "19:00"])

        # Se quita el del mediodía: solo quedan dos.
        form = PautaTomaForm(
            self.datos(horarios=["07:00", "19:00"]),
            instance=pauta,
            usuario=self.usuario,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        horas = [h.hora.strftime("%H:%M") for h in pauta.horarios.all()]
        self.assertEqual(horas, ["07:00", "19:00"])

    def test_no_se_aceptan_horas_repetidas(self):
        form = PautaTomaForm(
            self.datos(horarios=["07:00", "07:00"]), usuario=self.usuario
        )

        self.assertFalse(form.is_valid())
        self.assertIn("horarios", form.errors)

    def test_no_se_aceptan_horas_invalidas(self):
        form = PautaTomaForm(
            self.datos(horarios=["25:00"]), usuario=self.usuario
        )

        self.assertFalse(form.is_valid())
        self.assertIn("horarios", form.errors)

    def test_una_pauta_sin_horas_conserva_un_horario_sin_hora_fija(self):
        form = PautaTomaForm(self.datos(horarios=[]), usuario=self.usuario)

        self.assertTrue(form.is_valid(), form.errors)
        pauta = form.save()

        self.assertEqual(pauta.horarios.count(), 1)
        self.assertIsNone(pauta.horarios.first().hora)
        self.assertEqual(pauta.resumen_horarios, "Sin hora fija")

    def test_al_editar_se_muestran_los_horarios_existentes(self):
        form = PautaTomaForm(
            self.datos(horarios=["07:00", "19:00"]), usuario=self.usuario
        )
        pauta = form.save()

        form = PautaTomaForm(instance=pauta, usuario=self.usuario)

        self.assertEqual(
            [h.strftime("%H:%M") for h in form.initial["horarios"]],
            ["07:00", "19:00"],
        )

    def test_el_formulario_muestra_los_horarios_en_la_vista(self):
        self.client.force_login(self.usuario)

        respuesta = self.client.get(reverse("botiquin:pauta_crear"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Horarios de la toma")
        self.assertContains(respuesta, 'type="time"')
        self.assertContains(respuesta, "Añadir otro horario")


class ConfirmacionIndependienteTests(TestCase):
    """Cada horario se confirma por separado en el historial del día."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="indep_usuario",
            password="ClaveSegura123!",
            email="indep@example.com",
            first_name="Ana",
        )
        cls.miembro = cls.usuario.hogar.miembros.get(es_principal=True)
        cls.medicamento = Medicamento.objects.create(
            usuario=cls.usuario,
            nombre="Paracetamol",
            cantidad=20,
            fecha_vencimiento=timezone.localdate() + datetime.timedelta(days=300),
        )
        cls.pauta = PautaToma.objects.create(
            medicamento=cls.medicamento,
            miembro=cls.miembro,
            frecuencia="diaria",
            fecha_inicio=timezone.localdate(),
        )
        cls.manana = HorarioToma.objects.create(
            pauta=cls.pauta, hora=datetime.time(7, 0), orden=1
        )
        cls.mediodia = HorarioToma.objects.create(
            pauta=cls.pauta, hora=datetime.time(12, 0), orden=2
        )
        cls.noche = HorarioToma.objects.create(
            pauta=cls.pauta, hora=datetime.time(19, 0), orden=3
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()

    def test_el_historial_muestra_una_toma_por_horario(self):
        respuesta = self.client.get(reverse("botiquin:tomas_hoy"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "07:00")
        self.assertContains(respuesta, "12:00")
        self.assertContains(respuesta, "19:00")
        # Tres tarjetas, una por horario.
        self.assertContains(respuesta, "Marcar como tomada", count=3)

    def test_confirmar_una_toma_no_marca_las_demas(self):
        self.client.post(
            reverse("botiquin:marcar_tomada", args=[self.manana.pk])
        )

        self.assertTrue(
            TomaRegistrada.objects.filter(
                horario=self.manana, fecha=self.hoy, tomada=True
            ).exists()
        )
        for otro in (self.mediodia, self.noche):
            self.assertFalse(
                TomaRegistrada.objects.filter(
                    horario=otro, fecha=self.hoy, tomada=True
                ).exists()
            )

    def test_cada_horario_tiene_su_propia_toma_registrada(self):
        self.client.post(reverse("botiquin:marcar_tomada", args=[self.manana.pk]))
        self.client.post(reverse("botiquin:marcar_tomada", args=[self.noche.pk]))

        tomas = TomaRegistrada.objects.filter(pauta=self.pauta, fecha=self.hoy)
        self.assertEqual(tomas.count(), 2)
        self.assertEqual(
            sorted(t.horario.hora.strftime("%H:%M") for t in tomas),
            ["07:00", "19:00"],
        )

    def test_desmarcar_solo_affecta_a_su_horario(self):
        self.client.post(reverse("botiquin:marcar_tomada", args=[self.manana.pk]))
        self.client.post(reverse("botiquin:marcar_tomada", args=[self.noche.pk]))

        # Se desmarca la de la mañana.
        self.client.post(reverse("botiquin:marcar_tomada", args=[self.manana.pk]))

        self.assertFalse(
            TomaRegistrada.objects.filter(
                horario=self.manana, fecha=self.hoy, tomada=True
            ).exists()
        )
        self.assertTrue(
            TomaRegistrada.objects.filter(
                horario=self.noche, fecha=self.hoy, tomada=True
            ).exists()
        )

    def test_el_token_confirma_solo_su_horario(self):
        from botiquin.notificaciones import generar_token_confirmacion

        token = generar_token_confirmacion(
            self.pauta.pk, self.mediodia.pk, self.hoy
        )
        respuesta = self.client.get(reverse("botiquin:confirmar_toma", args=[token]))

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(
            TomaRegistrada.objects.filter(
                horario=self.mediodia, fecha=self.hoy, tomada=True
            ).exists()
        )
        self.assertFalse(
            TomaRegistrada.objects.filter(
                horario=self.manana, fecha=self.hoy, tomada=True
            ).exists()
        )


class RecordatoriosPorHorarioTests(TestCase):
    """Cada horario genera su propio recordatorio."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="record_usuario",
            password="ClaveSegura123!",
            email="record@example.com",
            first_name="Ana",
            canal_alertas="correo",
        )
        cls.miembro = cls.usuario.hogar.miembros.get(es_principal=True)
        cls.medicamento = Medicamento.objects.create(
            usuario=cls.usuario,
            nombre="Losartán",
            cantidad=30,
            fecha_vencimiento=timezone.localdate() + datetime.timedelta(days=200),
        )
        cls.pauta = PautaToma.objects.create(
            medicamento=cls.medicamento,
            miembro=cls.miembro,
            frecuencia="diaria",
            fecha_inicio=timezone.localdate(),
        )
        cls.manana = HorarioToma.objects.create(
            pauta=cls.pauta, hora=datetime.time(7, 0), orden=1
        )
        cls.noche = HorarioToma.objects.create(
            pauta=cls.pauta, hora=datetime.time(19, 0), orden=2
        )

    def setUp(self):
        from django.core import mail

        mail.outbox = []

    def test_cada_horario_genera_su_propio_recordatorio(self):
        from botiquin.notificaciones import enviar_recordatorio_hora

        ahora = timezone.localtime().replace(hour=7, minute=0)
        with patch(
            "botiquin.notificaciones._enviar_correo", return_value=True
        ) as mock_correo:
            correos, _ = enviar_recordatorio_hora(
                [(self.pauta, self.manana)], ahora
            )

        self.assertEqual(correos, 1)
        self.assertEqual(mock_correo.call_count, 1)
        # Solo se notifica el horario de esa hora.
        self.assertTrue(
            TomaRegistrada.objects.filter(
                horario=self.manana, fecha=ahora.date(), notificada=True
            ).exists()
        )
        self.assertFalse(
            TomaRegistrada.objects.filter(horario=self.noche).exists()
        )

    def test_notificar_un_horario_no_bloquea_el_otro(self):
        from botiquin.notificaciones import enviar_recordatorio_hora

        ahora = timezone.localtime().replace(hour=7, minute=0)
        with patch("botiquin.notificaciones._enviar_correo", return_value=True):
            enviar_recordatorio_hora([(self.pauta, self.manana)], ahora)

        # Más tarde se dispara el recordatorio del segundo horario.
        ahora_noche = timezone.localtime().replace(hour=19, minute=0)
        with patch(
            "botiquin.notificaciones._enviar_correo", return_value=True
        ) as mock_correo:
            correos, _ = enviar_recordatorio_hora(
                [(self.pauta, self.noche)], ahora_noche
            )

        self.assertEqual(correos, 1)
        self.assertEqual(mock_correo.call_count, 1)

    def test_el_mismo_horario_no_se_notifica_dos_veces(self):
        from botiquin.notificaciones import enviar_recordatorio_hora

        ahora = timezone.localtime().replace(hour=7, minute=0)
        with patch("botiquin.notificaciones._enviar_correo", return_value=True):
            enviar_recordatorio_hora([(self.pauta, self.manana)], ahora)
            correos, _ = enviar_recordatorio_hora([(self.pauta, self.manana)], ahora)

        self.assertEqual(correos, 0)

    def test_el_servicio_solo_selecciona_el_horario_de_la_hora_actual(self):
        from botiquin.servicio_recordatorios import horarios_de_ahora

        ahora = timezone.localtime().replace(hour=19, minute=0)
        pares = horarios_de_ahora(ahora)

        self.assertEqual(len(pares), 1)
        self.assertEqual(pares[0][1].pk, self.noche.pk)

    def test_el_correo_incluye_la_hora_del_horario(self):
        from botiquin.notificaciones import enviar_recordatorio_hora

        ahora = timezone.localtime().replace(hour=7, minute=0)
        with patch(
            "botiquin.notificaciones._enviar_correo", return_value=True
        ) as mock_correo:
            enviar_recordatorio_hora([(self.pauta, self.manana)], ahora)

        contexto = mock_correo.call_args[0][4]
        self.assertEqual(contexto["items"][0]["horario"].pk, self.manana.pk)
