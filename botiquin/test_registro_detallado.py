"""Registro detallado de medicamentos: clasificación de uso y campos nuevos."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario

from .forms import MedicamentoForm
from .models import Categoria, Clasificacion, Medicamento

CLASIFICACIONES_INICIALES = [
    "Tratamiento crónico",
    "Antigripal",
    "Uso ocasional",
]


class ClasificacionTests(TestCase):
    """Catálogo de clasificaciones de uso."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="clasif_usuario",
            password="ClaveSegura123!",
            email="clasif@example.com",
            first_name="Ana",
        )
        cls.categoria, _ = Categoria.objects.get_or_create(nombre="Analgésicos")

    def test_el_catalogo_inicial_existe(self):
        nombres = list(
            Clasificacion.objects.values_list("nombre", flat=True)
        )
        for nombre in CLASIFICACIONES_INICIALES:
            self.assertIn(nombre, nombres)

    def test_las_clasificaciones_traen_descripcion(self):
        for nombre in CLASIFICACIONES_INICIALES:
            clasificacion = Clasificacion.objects.get(nombre=nombre)
            self.assertTrue(clasificacion.descripcion)
            self.assertTrue(clasificacion.icono)

    def test_el_orden_de_las_clasificaciones_es_estable(self):
        orden = list(
            Clasificacion.objects.order_by("orden").values_list("nombre", flat=True)
        )
        self.assertEqual(orden, CLASIFICACIONES_INICIALES)

    def test_un_medicamento_puede_asignar_clasificacion(self):
        cronico = Clasificacion.objects.get(nombre="Tratamiento crónico")
        medicamento = Medicamento.objects.create(
            usuario=self.usuario,
            categoria=self.categoria,
            clasificacion=cronico,
            nombre="Metformina",
            concentracion="850 mg",
            cantidad=30,
            fecha_vencimiento=timezone.localdate() + timedelta(days=200),
        )

        self.assertEqual(medicamento.clasificacion, cronico)
        self.assertEqual(medicamento.concentracion, "850 mg")
        self.assertEqual(medicamento.nombre_completo, "Metformina 850 mg")

    def test_nombre_completo_sin_concentracion(self):
        medicamento = Medicamento.objects.create(
            usuario=self.usuario,
            categoria=self.categoria,
            nombre="Alcohol",
            cantidad=1,
            fecha_vencimiento=timezone.localdate() + timedelta(days=200),
        )

        self.assertEqual(medicamento.nombre_completo, "Alcohol")


class FormularioRegistroDetalladoTests(TestCase):
    """El formulario recoge los datos detallados del medicamento."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="form_detallado",
            password="ClaveSegura123!",
            email="detallado@example.com",
            first_name="Ana",
        )
        cls.categoria, _ = Categoria.objects.get_or_create(nombre="Analgésicos")
        cls.cronico, _ = Clasificacion.objects.get_or_create(
            nombre="Tratamiento crónico",
            defaults={"icono": "💊", "descripcion": "Uso prolongado.", "orden": 1},
        )

    def datos(self, **cambios):
        base = {
            "nombre": "Paracetamol",
            "concentracion": "500 mg",
            "presentacion": "tableta",
            "cantidad": 20,
            "clasificacion": self.cronico.pk,
            "categoria": self.categoria.pk,
            "fecha_vencimiento": (timezone.localdate() + timedelta(days=300)).isoformat(),
            "lote": "L-2026A",
            "registro_sanitario": "INVIMA 2024M-00123",
            "condicion_almacenamiento": "seco",
            "ubicacion": "Botiquín del baño",
            "notas_conservacion": "Mantener en su caja original.",
            "indicacion_prescrita": "Dolor de cabeza y fiebre, según indicación médica.",
            "notas": "Caja casi nueva.",
            "miembro": "",
        }
        base.update(cambios)
        return base

    def test_el_formulario_tiene_los_campos_detallados(self):
        form = MedicamentoForm(usuario=self.usuario)

        for campo in (
            "nombre",
            "concentracion",
            "presentacion",
            "clasificacion",
            "categoria",
            "fecha_vencimiento",
            "lote",
            "registro_sanitario",
            "indicacion_prescrita",
            "notas",
        ):
            self.assertIn(campo, form.fields)

    def test_la_clasificacion_es_obligatoria(self):
        form = MedicamentoForm(self.datos(clasificacion=""), usuario=self.usuario)

        self.assertFalse(form.is_valid())
        self.assertIn("clasificacion", form.errors)

    def test_registra_todos_los_datos_detallados(self):
        form = MedicamentoForm(self.datos(), usuario=self.usuario)

        self.assertTrue(form.is_valid(), form.errors)
        medicamento = form.save(commit=False)
        medicamento.usuario = self.usuario
        medicamento.save()

        self.assertEqual(medicamento.nombre, "Paracetamol")
        self.assertEqual(medicamento.concentracion, "500 mg")
        self.assertEqual(medicamento.get_presentacion_display(), "Tabletas")
        self.assertEqual(medicamento.clasificacion, self.cronico)
        self.assertEqual(medicamento.categoria, self.categoria)
        self.assertEqual(medicamento.lote, "L-2026A")
        self.assertEqual(medicamento.registro_sanitario, "INVIMA 2024M-00123")
        self.assertIn("Dolor de cabeza", medicamento.indicacion_prescrita)
        self.assertEqual(medicamento.notas, "Caja casi nueva.")

    def test_avisa_si_la_concentracion_ya_esta_en_el_nombre(self):
        form = MedicamentoForm(
            self.datos(nombre="Paracetamol 500 mg"), usuario=self.usuario
        )

        self.assertFalse(form.is_valid())
        self.assertIn("concentracion", form.errors)

    def test_la_indicacion_prescrita_es_opcional(self):
        form = MedicamentoForm(
            self.datos(indicacion_prescrita=""), usuario=self.usuario
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_el_formulario_no_sugiere_tratamientos(self):
        form = MedicamentoForm(usuario=self.usuario)

        ayuda = form.fields["indicacion_prescrita"].help_text
        self.assertIn("no sugiere tratamientos", ayuda)

    def test_la_forma_farmaceutica_tiene_varias_opciones(self):
        form = MedicamentoForm(usuario=self.usuario)

        etiquetas = [
            etiqueta for _valor, etiqueta in form.fields["presentacion"].choices
        ]
        self.assertIn("Cápsulas", etiquetas)
        self.assertIn("Suspensión", etiquetas)
        self.assertIn("Inyectable", etiquetas)
        self.assertIn("Supositorio", etiquetas)


class VistasRegistroDetalladoTests(TestCase):
    """Las vistas muestran y filtran los datos nuevos."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="vistas_detallado",
            password="ClaveSegura123!",
            email="vistas@example.com",
            first_name="Ana",
        )
        cls.categoria, _ = Categoria.objects.get_or_create(nombre="Analgésicos")
        cls.cronico, _ = Clasificacion.objects.get_or_create(
            nombre="Tratamiento crónico",
            defaults={"icono": "💊", "orden": 1},
        )
        cls.antigripal, _ = Clasificacion.objects.get_or_create(
            nombre="Antigripal",
            defaults={"icono": "🤧", "orden": 2},
        )
        cls.med_cronico = Medicamento.objects.create(
            usuario=cls.usuario,
            categoria=cls.categoria,
            clasificacion=cls.cronico,
            nombre="Metformina",
            concentracion="850 mg",
            cantidad=30,
            fecha_vencimiento=timezone.localdate() + timedelta(days=200),
            indicacion_prescrita="Control de la diabetes, según indicación médica.",
        )
        cls.med_antigripal = Medicamento.objects.create(
            usuario=cls.usuario,
            categoria=cls.categoria,
            clasificacion=cls.antigripal,
            nombre="Paracetamol",
            concentracion="500 mg",
            cantidad=10,
            fecha_vencimiento=timezone.localdate() + timedelta(days=300),
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_el_formulario_de_registro_muestra_las_clasificaciones(self):
        respuesta = self.client.get(reverse("botiquin:crear"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Clasificación de uso")
        self.assertContains(respuesta, "Indicación prescrita")
        self.assertContains(respuesta, "no sugiere qué medicamento")

    def test_la_ficha_muestra_los_datos_detallados(self):
        respuesta = self.client.get(
            reverse("botiquin:detalle", args=[self.med_cronico.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Metformina 850 mg")
        self.assertContains(respuesta, "Tratamiento crónico")
        self.assertContains(respuesta, "Registro INVIMA")
        self.assertContains(respuesta, "Control de la diabetes")

    def test_el_listado_filtra_por_clasificacion(self):
        respuesta = self.client.get(
            reverse("botiquin:lista"), {"clasificacion": self.cronico.pk}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Metformina")
        self.assertNotContains(respuesta, "Paracetamol")

    def test_el_listado_conserva_el_filtro_al_cambiar_de_estado(self):
        respuesta = self.client.get(
            reverse("botiquin:lista"), {"clasificacion": self.cronico.pk}
        )

        self.assertContains(respuesta, f"clasificacion={self.cronico.pk}")

    def test_la_busqueda_encuentra_por_concentracion(self):
        respuesta = self.client.get(reverse("botiquin:lista"), {"q": "500 mg"})

        self.assertContains(respuesta, "Paracetamol")
        self.assertNotContains(respuesta, "Metformina")
