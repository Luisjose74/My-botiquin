"""Contenido educativo de Regencia de Farmacia en la app y en los correos.

La sección «Consejos para el cuidado de tu botiquín» (tres pilares:
conservación, uso seguro y desecho responsable) es la misma en el portal
público, en las vistas de apoyo de la app privada y en el correo de alertas.
"""
from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario

from .models import Categoria, Medicamento

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

#: Título de la sección educativa.
TITULO = "Consejos para el cuidado de tu botiquín"

#: Los tres pilares del enfoque de Regencia de Farmacia.
PILARES = ["Conservación", "Uso seguro", "Desecho responsable"]

#: Frases clave de cada pilar.
FRASES_POR_PILAR = {
    "Conservación": [
        "Según el empaque",
        "Humedad, luz y calor",
        "En su envase original",
        "Fuera del alcance de niños y mascotas",
    ],
    "Uso seguro": [
        "Respeta la dosis y el horario",
        "Verifica los vencimientos",
        "No compartas fármacos formulados",
        "Evita la automedicación con antibióticos",
        "Consulta al profesional de salud",
    ],
    "Desecho responsable": [
        "Separa los caducados para Puntos Azules",
        "Nunca al inodoro ni al lavamanos",
        "No los mezcles con la basura doméstica",
        "Elementos cortopunzantes aparte",
    ],
}

TODAS_FRASES = [
    frase
    for frases in FRASES_POR_PILAR.values()
    for frase in frases
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
        self.client.force_login(self.usuario)
        mail.outbox = []

    def crear(self, nombre, dias, cantidad=5):
        return Medicamento.objects.create(
            usuario=self.usuario,
            categoria=self.categoria,
            nombre=nombre,
            cantidad=cantidad,
            fecha_vencimiento=self.hoy + timedelta(days=dias),
        )

    def _comprobar(self, contenido):
        self.assertIn(TITULO, contenido)
        for pilar in PILARES:
            self.assertIn(pilar, contenido)
        for frase in TODAS_FRASES:
            self.assertIn(frase, contenido)

    def test_panel_de_alertas_incluye_los_consejos(self):
        self.crear("Vencido", -3)

        respuesta = self.client.get(reverse("botiquin:alertas"))

        self.assertEqual(respuesta.status_code, 200)
        self._comprobar(respuesta.content.decode("utf-8"))

    def test_dashboard_incluye_los_consejos(self):
        self.client.force_login(self.usuario)

        respuesta = self.client.get(reverse("inicio"))

        self.assertEqual(respuesta.status_code, 200)
        self._comprobar(respuesta.content.decode("utf-8"))

    def test_detalle_de_medicamento_vencido_incluye_los_consejos(self):
        self.client.force_login(self.usuario)
        medicamento = self.crear("Vencido", -5)

        respuesta = self.client.get(
            reverse("botiquin:detalle", args=[medicamento.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self._comprobar(respuesta.content.decode("utf-8"))

    def test_correo_de_alertas_incluye_los_consejos(self):
        from .alertas import sincronizar_alertas

        self.crear("Ibuprofeno", 12)
        sincronizar_alertas(self.usuario)

        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self._comprobar(correo.body)

        # La versión HTML también los incluye.
        html = correo.alternatives[0][0]
        self._comprobar(html)

    def test_el_consejo_de_desecho_responsable_enlaza_a_puntos_azules(self):
        from .alertas import sincronizar_alertas

        self.crear("Ibuprofeno", 12)
        sincronizar_alertas(self.usuario)

        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("puntos-azules", html)
        self.assertIn(
            "Ver el directorio de Puntos Azules en Sogamoso",
            mail.outbox[0].body,
        )
