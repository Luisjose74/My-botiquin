from django.test import TestCase
from django.urls import reverse

from .models import Hogar, MiembroHogar, Usuario


class InvitacionHogarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.titular = Usuario.objects.create_user(
            username="titular_inv", password="ClaveSegura123!", first_name="Titular"
        )
        cls.invitado = Usuario.objects.create_user(
            username="invitado_inv", password="ClaveSegura123!", first_name="Invitado"
        )
        cls.hogar_titular = cls.titular.hogar
        cls.codigo = cls.hogar_titular.codigo_invitacion

    def setUp(self):
        self.client.force_login(self.invitado)

    def test_codigo_invalido_no_permite_unirse(self):
        respuesta = self.client.post(
            reverse("cuentas:unirse_hogar"), {"codigo": "no-existe"}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ese código no corresponde")
        self.invitado.refresh_from_db()
        self.assertNotEqual(self.invitado.hogar_id, self.hogar_titular.pk)

    def test_unirse_por_codigo_cambia_el_hogar_y_crea_miembro(self):
        respuesta = self.client.post(
            reverse("cuentas:unirse_hogar"), {"codigo": self.codigo}
        )

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        self.invitado.refresh_from_db()
        self.assertEqual(self.invitado.hogar_id, self.hogar_titular.pk)
        self.assertTrue(
            MiembroHogar.objects.filter(
                hogar=self.hogar_titular, usuario=self.invitado
            ).exists()
        )

    def test_ya_perteneciente_no_duplica_miembro(self):
        self.invitado.hogar = self.hogar_titular
        self.invitado.save(update_fields=["hogar"])
        self.invitado.perfil_miembro.hogar = self.hogar_titular
        self.invitado.perfil_miembro.save(update_fields=["hogar"])
        self.invitado.hogar = self.hogar_titular
        self.invitado.save(update_fields=["hogar"])

        respuesta = self.client.post(
            reverse("cuentas:unirse_hogar"), {"codigo": self.codigo}
        )

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        self.assertEqual(
            MiembroHogar.objects.filter(
                hogar=self.hogar_titular, usuario=self.invitado
            ).count(),
            1,
        )

    def test_url_con_codigo_prefill(self):
        respuesta = self.client.get(
            reverse("cuentas:unirse_hogar_codigo", args=[self.codigo])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.codigo)

    def test_codigo_invalido_en_url_muestra_aviso(self):
        respuesta = self.client.get(
            reverse("cuentas:unirse_hogar_codigo", args=["zzzzzzzz"])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no es válido")

    def test_familia_muestra_codigo_de_invitacion(self):
        self.client.force_login(self.titular)

        respuesta = self.client.get(reverse("cuentas:familia"))

        self.assertContains(respuesta, self.codigo)

    def test_no_puede_unirse_sin_login(self):
        self.client.logout()

        respuesta = self.client.get(reverse("cuentas:unirse_hogar"))

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("cuentas:login"), respuesta.url)

    def test_nombre_duplicado_se_renombra(self):
        MiembroHogar.objects.create(
            hogar=self.hogar_titular, nombre="Invitado", relacion="otro"
        )

        respuesta = self.client.post(
            reverse("cuentas:unirse_hogar"), {"codigo": self.codigo}
        )

        self.assertRedirects(respuesta, reverse("cuentas:familia"))
        nuevo = MiembroHogar.objects.get(hogar=self.hogar_titular, usuario=self.invitado)
        self.assertNotEqual(nuevo.nombre, "Invitado")
