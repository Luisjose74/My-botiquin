from django.test import TestCase
from django.urls import reverse

from botiquin.models import Medicamento

from .models import MiembroHogar, Usuario


class GestionFamiliarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="familia_titular", password="ClaveSegura123!",
            first_name="Ana", last_name="Lopez",
        )
        cls.otro = Usuario.objects.create_user(
            username="familia_ajena", password="ClaveSegura123!",
            first_name="Otra", last_name="Persona",
        )
        cls.principal = cls.usuario.hogar.miembros.get(es_principal=True)

    def setUp(self):
        self.client.force_login(self.usuario)

    def crear_miembro(self, nombre="Mamá", relacion="madre", hogar=None):
        return MiembroHogar.objects.create(
            hogar=hogar or self.usuario.hogar, nombre=nombre, relacion=relacion
        )

    def test_lista_muestra_principal_y_permite_agregar(self):
        respuesta = self.client.post(
            reverse("cuentas:familia"), {"nombre": "Papá", "relacion": "padre"}
        )

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        self.assertTrue(
            MiembroHogar.objects.filter(
                hogar=self.usuario.hogar, nombre="Papá", relacion="padre"
            ).exists()
        )
        self.assertContains(self.client.get(reverse("cuentas:familia")), "Papá")

    def test_no_permite_crear_otro_principal(self):
        respuesta = self.client.post(
            reverse("cuentas:familia"), {"nombre": "Nuevo", "relacion": "principal"}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(
            MiembroHogar.objects.filter(nombre="Nuevo").exists()
        )

    def test_nombre_duplicado_sin_distinguir_mayusculas(self):
        self.crear_miembro(nombre="Hijo")

        respuesta = self.client.post(
            reverse("cuentas:familia"), {"nombre": "  hijo ", "relacion": "hijo"}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ya tienes un integrante con ese nombre.")
        self.assertEqual(
            MiembroHogar.objects.filter(hogar=self.usuario.hogar, nombre__iexact="hijo").count(),
            1,
        )

    def test_editar_cambia_nombre_y_relacion(self):
        miembro = self.crear_miembro(nombre="Abuela", relacion="abuelo")

        respuesta = self.client.post(
            reverse("cuentas:familia_editar", args=[miembro.pk]),
            {"nombre": "Abuela Rosa", "relacion": "abuelo"},
        )

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        miembro.refresh_from_db()
        self.assertEqual(miembro.nombre, "Abuela Rosa")

    def test_no_edita_ni_elimina_integrante_de_otro_hogar(self):
        ajeno = MiembroHogar.objects.get(hogar=self.otro.hogar, es_principal=True)

        self.assertEqual(
            self.client.get(reverse("cuentas:familia_editar", args=[ajeno.pk])).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(reverse("cuentas:familia_eliminar", args=[ajeno.pk])).status_code,
            302,
        )
        self.assertTrue(MiembroHogar.objects.filter(pk=ajeno.pk).exists())

    def test_principal_no_se_puede_eliminar(self):
        self.client.post(reverse("cuentas:familia_eliminar", args=[self.principal.pk]))

        self.assertTrue(MiembroHogar.objects.filter(pk=self.principal.pk).exists())

    def test_eliminar_requiere_post_y_deja_medicamentos_sin_asignar(self):
        miembro = self.crear_miembro(nombre="Hermano", relacion="otro")
        medicamento = Medicamento.objects.create(
            usuario=self.usuario, miembro=miembro, nombre="Jarabe",
            cantidad=2, fecha_vencimiento="2031-01-01",
        )
        url = reverse("cuentas:familia_eliminar", args=[miembro.pk])

        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(MiembroHogar.objects.filter(pk=miembro.pk).exists())

        self.client.post(url)

        self.assertFalse(MiembroHogar.objects.filter(pk=miembro.pk).exists())
        medicamento.refresh_from_db()
        self.assertIsNone(medicamento.miembro)

    def test_formulario_de_medicamento_solo_ofrece_miembros_del_hogar(self):
        propio = self.crear_miembro(nombre="Propio")
        ajeno = MiembroHogar.objects.get(hogar=self.otro.hogar, es_principal=True)
        from botiquin.forms import MedicamentoForm

        form = MedicamentoForm(usuario=self.usuario)
        ids = list(form.fields["miembro"].queryset.values_list("pk", flat=True))

        self.assertIn(propio.pk, ids)
        self.assertNotIn(ajeno.pk, ids)

    def test_perfil_enlaza_a_familia_y_no_muestra_codigo(self):
        respuesta = self.client.get(reverse("cuentas:perfil"))

        self.assertContains(respuesta, reverse("cuentas:familia"))
        self.assertNotContains(respuesta, "Código de invitación")

    def test_relacion_es_obligatoria_al_agregar(self):
        respuesta = self.client.post(
            reverse("cuentas:familia"), {"nombre": "Sin relacion", "relacion": ""}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(MiembroHogar.objects.filter(nombre="Sin relacion").exists())


class GestionFamiliarPermisosTests(TestCase):
    """Verifica que solo el administrador principal gestione la familia."""

    @classmethod
    def setUpTestData(cls):
        cls.titular = Usuario.objects.create_user(
            username="perm_titular", password="ClaveSegura123!",
            first_name="Ana", last_name="Lopez",
        )
        cls.invitado = Usuario.objects.create_user(
            username="perm_invitado", password="ClaveSegura123!",
            first_name="Invitado", last_name="Test",
        )
        # Vincular al invitado al hogar del titular como no-principal
        cls.invitado.hogar = cls.titular.hogar
        cls.invitado.save(update_fields=["hogar"])
        # Reutilizar el MiembroHogar creado por la señal
        miembro = cls.invitado.perfil_miembro
        miembro.hogar = cls.titular.hogar
        miembro.nombre = "Invitado Test"
        miembro.relacion = "otro"
        miembro.es_principal = False
        miembro.save()

    def setUp(self):
        self.client.force_login(self.invitado)

    def test_no_principal_no_puede_agregar_miembro(self):
        respuesta = self.client.post(
            reverse("cuentas:familia"), {"nombre": "Nuevo", "relacion": "hijo"}
        )

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        self.assertFalse(
            MiembroHogar.objects.filter(
                hogar=self.titular.hogar, nombre="Nuevo"
            ).exists()
        )

    def test_no_principal_no_puede_editar_miembro(self):
        miembro = MiembroHogar.objects.create(
            hogar=self.titular.hogar, nombre="Editable", relacion="hijo"
        )
        respuesta = self.client.post(
            reverse("cuentas:familia_editar", args=[miembro.pk]),
            {"nombre": "Cambiado", "relacion": "hijo"},
        )

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        miembro.refresh_from_db()
        self.assertEqual(miembro.nombre, "Editable")

    def test_no_principal_no_puede_eliminar_miembro(self):
        miembro = MiembroHogar.objects.create(
            hogar=self.titular.hogar, nombre="Eliminable", relacion="hijo"
        )
        respuesta = self.client.post(
            reverse("cuentas:familia_eliminar", args=[miembro.pk])
        )

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        self.assertTrue(MiembroHogar.objects.filter(pk=miembro.pk).exists())

    def test_no_principal_no_puede_regenerar_codigo(self):
        codigo_anterior = self.titular.hogar.codigo_invitacion
        respuesta = self.client.post(reverse("cuentas:regenerar_codigo"))

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        self.titular.hogar.refresh_from_db()
        self.assertEqual(self.titular.hogar.codigo_invitacion, codigo_anterior)

    def test_no_principal_ve_solo_lectura_en_familia(self):
        respuesta = self.client.get(reverse("cuentas:familia"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Solo lectura")
        self.assertNotContains(respuesta, "Agregar integrante")


class SalirHogarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.titular = Usuario.objects.create_user(
            username="salir_titular", password="ClaveSegura123!",
            first_name="Ana", last_name="Lopez",
        )
        cls.invitado = Usuario.objects.create_user(
            username="salir_invitado", password="ClaveSegura123!",
            first_name="Invitado", last_name="Test",
        )
        cls.invitado.hogar = cls.titular.hogar
        cls.invitado.save(update_fields=["hogar"])
        miembro = cls.invitado.perfil_miembro
        miembro.hogar = cls.titular.hogar
        miembro.nombre = "Invitado Test"
        miembro.relacion = "otro"
        miembro.es_principal = False
        miembro.save()

    def test_miembro_puede_salir_del_hogar(self):
        self.client.force_login(self.invitado)
        hogar_anterior = self.invitado.hogar_id

        respuesta = self.client.post(reverse("cuentas:salir_hogar"))

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        self.invitado.refresh_from_db()
        self.assertNotEqual(self.invitado.hogar_id, hogar_anterior)
        self.assertIsNotNone(self.invitado.hogar_id)
        self.assertTrue(
            MiembroHogar.objects.filter(
                hogar=self.invitado.hogar, usuario=self.invitado, es_principal=True
            ).exists()
        )
        self.assertFalse(
            MiembroHogar.objects.filter(
                hogar_id=hogar_anterior, usuario=self.invitado
            ).exists()
        )

    def test_administrador_no_puede_salir_del_hogar(self):
        self.client.force_login(self.titular)
        hogar_id = self.titular.hogar_id

        respuesta = self.client.post(reverse("cuentas:salir_hogar"))

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        self.titular.refresh_from_db()
        self.assertEqual(self.titular.hogar_id, hogar_id)
