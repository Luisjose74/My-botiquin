import base64
import os
import shutil
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario

from .models import Categoria, Medicamento, PautaToma, TomaRegistrada

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="botiquin_test_")

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class MedicamentoCRUDTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="usuario_prueba", password="ClaveSegura123!"
        )
        cls.otro = Usuario.objects.create_user(
            username="otro_usuario", password="ClaveSegura123!"
        )
        cls.categoria = Categoria.objects.create(nombre="Categoria de prueba")
        cls.miembro = cls.usuario.hogar.miembros.first()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()

    def datos(self, **cambios):
        datos = {
            "nombre": "Paracetamol prueba",
            "categoria": self.categoria.pk,
            "presentacion": "tableta",
            "cantidad": 10,
            "lote": "L-TEST",
            "registro_sanitario": "INVIMA-TEST",
            "fecha_vencimiento": (self.hoy + timedelta(days=100)).isoformat(),
            "condicion_almacenamiento": "seco",
            "ubicacion": "Botiquin de prueba",
            "miembro": self.miembro.pk,
            "notas_conservacion": "",
            "notas": "",
        }
        datos.update(cambios)
        return datos

    def crear_medicamento(self, nombre, dias, cantidad=5, **extra):
        return Medicamento.objects.create(
            usuario=self.usuario,
            categoria=self.categoria,
            nombre=nombre,
            cantidad=cantidad,
            fecha_vencimiento=self.hoy + timedelta(days=dias),
            **extra,
        )

    def test_crear_medicamento_con_foto(self):
        respuesta = self.client.post(
            reverse("botiquin:crear"),
            self.datos(
                foto=SimpleUploadedFile(
                    "caja_prueba.png", PNG_1X1, content_type="image/png"
                )
            ),
        )

        medicamento = Medicamento.objects.get(nombre="Paracetamol prueba")
        self.assertRedirects(
            respuesta, reverse("botiquin:detalle", args=[medicamento.pk])
        )
        self.assertTrue(medicamento.foto)
        self.assertTrue(os.path.exists(medicamento.foto.path))

        detalle = self.client.get(
            reverse("botiquin:detalle", args=[medicamento.pk])
        )
        self.assertContains(detalle, "Paracetamol prueba")
        self.assertContains(detalle, "Botiquin de prueba")

    def test_formulario_invalido_no_crea_medicamento(self):
        respuesta = self.client.post(reverse("botiquin:crear"), {})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].errors)
        self.assertEqual(Medicamento.objects.count(), 0)

    def test_editar_conserva_la_foto_existente(self):
        medicamento = self.crear_medicamento(
            "Medicamento con foto",
            100,
            foto=SimpleUploadedFile(
                "caja_existente.png", PNG_1X1, content_type="image/png"
            ),
        )

        respuesta = self.client.post(
            reverse("botiquin:editar", args=[medicamento.pk]),
            self.datos(nombre="Medicamento editado", cantidad=8),
        )

        self.assertRedirects(
            respuesta, reverse("botiquin:detalle", args=[medicamento.pk])
        )
        medicamento.refresh_from_db()
        self.assertEqual(medicamento.nombre, "Medicamento editado")
        self.assertEqual(medicamento.cantidad, 8)
        self.assertTrue(medicamento.foto)

    def test_filtros_por_estado_categoria_y_busqueda(self):
        self.crear_medicamento("Medicamento optimo", 100)
        self.crear_medicamento("Medicamento por vencer", 10)
        self.crear_medicamento("Medicamento vencido", -10)
        self.crear_medicamento("Medicamento agotado", 100, cantidad=0)

        listado = self.client.get(reverse("botiquin:lista"))
        self.assertEqual(len(listado.context["medicamentos"]), 4)
        self.assertEqual(listado.context["stats"]["optimos"], 1)
        self.assertEqual(listado.context["stats"]["por_vencer"], 1)
        self.assertEqual(listado.context["stats"]["vencidos"], 1)
        self.assertEqual(listado.context["stats"]["agotados"], 1)

        casos = [
            ("optimos", "Medicamento optimo"),
            ("por_vencer", "Medicamento por vencer"),
            ("vencidos", "Medicamento vencido"),
            ("agotados", "Medicamento agotado"),
        ]
        for estado, nombre in casos:
            respuesta = self.client.get(
                reverse("botiquin:lista"), {"estado": estado}
            )
            self.assertEqual(len(respuesta.context["medicamentos"]), 1)
            self.assertContains(respuesta, nombre)

        por_categoria = self.client.get(
            reverse("botiquin:lista"), {"categoria": self.categoria.pk}
        )
        self.assertEqual(len(por_categoria.context["medicamentos"]), 4)

        busqueda = self.client.get(
            reverse("botiquin:lista"), {"q": "vencido"}
        )
        self.assertEqual(len(busqueda.context["medicamentos"]), 1)
        self.assertContains(busqueda, "Medicamento vencido")

    def test_no_accede_a_medicamentos_de_otro_usuario(self):
        medicamento = self.crear_medicamento("Medicamento privado", 100)

        self.client.force_login(self.otro)
        detalle = self.client.get(
            reverse("botiquin:detalle", args=[medicamento.pk])
        )
        self.assertEqual(detalle.status_code, 302)
        self.assertTrue(Medicamento.objects.filter(pk=medicamento.pk).exists())

        listado = self.client.get(reverse("botiquin:lista"))
        self.assertEqual(len(listado.context["medicamentos"]), 0)

    def test_eliminar_requiere_post(self):
        medicamento = self.crear_medicamento("Medicamento a eliminar", 100)
        url = reverse("botiquin:eliminar", args=[medicamento.pk])

        confirmacion = self.client.get(url)
        self.assertEqual(confirmacion.status_code, 200)
        self.assertTrue(Medicamento.objects.filter(pk=medicamento.pk).exists())

        respuesta = self.client.post(url)
        self.assertRedirects(respuesta, reverse("botiquin:lista"))
        self.assertFalse(Medicamento.objects.filter(pk=medicamento.pk).exists())


class PautaTomaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="pauta_user", password="ClaveSegura123!",
            first_name="Ana", last_name="Lopez",
        )
        cls.miembro = cls.usuario.hogar.miembros.get(es_principal=True)
        cls.medicamento = Medicamento.objects.create(
            usuario=cls.usuario, nombre="Paracetamol", cantidad=10,
            fecha_vencimiento="2031-01-01",
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_crear_pauta_diaria(self):
        respuesta = self.client.post(
            reverse("botiquin:pauta_crear"),
            {
                "medicamento": self.medicamento.pk,
                "miembro": self.miembro.pk,
                "dosis": 1,
                "frecuencia": "diaria",
                "intervalo_dias": 1,
                "hora": "08:00",
                "fecha_inicio": "2026-01-01",
                "activa": "on",
            },
        )
        self.assertRedirects(respuesta, reverse("botiquin:pautas_lista"))
        self.assertTrue(PautaToma.objects.filter(medicamento=self.medicamento).exists())

    def test_pauta_dias_mes(self):
        from datetime import date
        pauta = PautaToma.objects.create(
            medicamento=self.medicamento, miembro=self.miembro,
            frecuencia="dias_mes", dias_mes="14, 20", fecha_inicio=date(2026, 1, 1),
        )
        self.assertEqual(pauta.dias_mes_lista(), [14, 20])
        self.assertIn(date(2026, 1, 14), pauta.proximas_tomas(date(2026, 1, 1), 10))
        self.assertNotIn(date(2026, 1, 15), pauta.proximas_tomas(date(2026, 1, 1), 10))

    def test_pauta_cada_n_dias(self):
        from datetime import date
        pauta = PautaToma.objects.create(
            medicamento=self.medicamento, miembro=self.miembro,
            frecuencia="cada_n_dias", intervalo_dias=3,
            fecha_inicio=date(2026, 1, 1),
        )
        proximas = pauta.proximas_tomas(date(2026, 1, 1), 4)
        self.assertEqual(proximas, [date(2026, 1, 1), date(2026, 1, 4), date(2026, 1, 7), date(2026, 1, 10)])

    def test_no_puede_editar_pauta_ajena(self):
        otro = Usuario.objects.create_user(username="pauta_otro", password="ClaveSegura123!")
        otro_med = Medicamento.objects.create(
            usuario=otro, nombre="Ibuprofeno", cantidad=5, fecha_vencimiento="2031-01-01"
        )
        pauta = PautaToma.objects.create(
            medicamento=otro_med, miembro=otro.hogar.miembros.get(es_principal=True),
        )
        respuesta = self.client.get(reverse("botiquin:pauta_editar", args=[pauta.pk]))
        self.assertEqual(respuesta.status_code, 302)


class TomaRegistradaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="toma_user", password="ClaveSegura123!",
            first_name="Ana", last_name="Lopez",
        )
        cls.miembro = cls.usuario.hogar.miembros.get(es_principal=True)
        cls.medicamento = Medicamento.objects.create(
            usuario=cls.usuario, nombre="Paracetamol", cantidad=10,
            fecha_vencimiento="2031-01-01",
        )
        cls.pauta = PautaToma.objects.create(
            medicamento=cls.medicamento, miembro=cls.miembro,
            frecuencia="diaria", fecha_inicio=__import__("datetime").date(2020, 1, 1),
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_marcar_tomada_crea_registro(self):
        respuesta = self.client.post(
            reverse("botiquin:marcar_tomada", args=[self.pauta.pk])
        )
        self.assertRedirects(respuesta, reverse("botiquin:tomas_hoy"))
        self.assertTrue(
            TomaRegistrada.objects.filter(pauta=self.pauta, tomada=True).exists()
        )

    def test_marcar_tomada_desmarca(self):
        TomaRegistrada.objects.create(pauta=self.pauta, fecha=__import__("datetime").date.today(), tomada=True)
        self.client.post(reverse("botiquin:marcar_tomada", args=[self.pauta.pk]))
        toma = TomaRegistrada.objects.get(pauta=self.pauta, fecha=__import__("datetime").date.today())
        self.assertFalse(toma.tomada)

    def test_tomas_hoy_muestra_pauta(self):
        respuesta = self.client.get(reverse("botiquin:tomas_hoy"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Paracetamol")


class VisibilidadCompartidaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user(
            username="vis_admin", password="ClaveSegura123!",
            first_name="Admin", last_name="Hogar",
        )
        cls.miembro_user = Usuario.objects.create_user(
            username="vis_miembro", password="ClaveSegura123!",
            first_name="Miembro", last_name="Hogar",
        )
        # Vincular miembro al hogar del admin (no principal)
        cls.miembro_user.hogar = cls.admin.hogar
        cls.miembro_user.save(update_fields=["hogar"])
        miembro = cls.miembro_user.perfil_miembro
        miembro.hogar = cls.admin.hogar
        miembro.nombre = "Miembro Hogar"
        miembro.relacion = "otro"
        miembro.es_principal = False
        miembro.save()

        cls.categoria = Categoria.objects.create(nombre="Cat compartida")
        cls.med_admin = Medicamento.objects.create(
            usuario=cls.admin, nombre="Medicamento del admin", cantidad=5,
            fecha_vencimiento="2031-01-01", categoria=cls.categoria,
        )

    def test_miembro_ve_medicamentos_del_admin(self):
        self.client.force_login(self.miembro_user)
        respuesta = self.client.get(reverse("botiquin:lista"))
        self.assertEqual(respuesta.status_code, 200)
        nombres = [m.nombre for m in respuesta.context["medicamentos"]]
        self.assertIn("Medicamento del admin", nombres)

    def test_miembro_ve_detalle_de_medicamento_del_admin(self):
        self.client.force_login(self.miembro_user)
        respuesta = self.client.get(reverse("botiquin:detalle", args=[self.med_admin.pk]))
        self.assertEqual(respuesta.status_code, 200)

    def test_miembro_no_puede_editar_medicamento_del_admin(self):
        self.client.force_login(self.miembro_user)
        respuesta = self.client.post(
            reverse("botiquin:editar", args=[self.med_admin.pk]),
            {"nombre": "Cambiado", "categoria": self.med_admin.categoria.pk,
             "presentacion": "tableta", "cantidad": 5,
             "fecha_vencimiento": "2031-01-01", "condicion_almacenamiento": "seco"},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.med_admin.refresh_from_db()
        self.assertEqual(self.med_admin.nombre, "Medicamento del admin")

    def test_miembro_no_puede_eliminar_medicamento_del_admin(self):
        self.client.force_login(self.miembro_user)
        respuesta = self.client.post(reverse("botiquin:eliminar", args=[self.med_admin.pk]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Medicamento.objects.filter(pk=self.med_admin.pk).exists())

    def test_admin_puede_editar_medicamento_propio(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("botiquin:editar", args=[self.med_admin.pk]),
            {"nombre": "Medicamento editado", "categoria": self.med_admin.categoria.pk,
             "presentacion": "tableta", "cantidad": 5,
             "fecha_vencimiento": "2031-01-01", "condicion_almacenamiento": "seco"},
        )
        self.assertRedirects(respuesta, reverse("botiquin:detalle", args=[self.med_admin.pk]))
        self.med_admin.refresh_from_db()
        self.assertEqual(self.med_admin.nombre, "Medicamento editado")

    def test_pautas_compartidas_visibles(self):
        from .models import PautaToma
        pauta = PautaToma.objects.create(
            medicamento=self.med_admin,
            miembro=self.admin.hogar.miembros.get(es_principal=True),
            frecuencia="diaria",
        )
        self.client.force_login(self.miembro_user)
        respuesta = self.client.get(reverse("botiquin:pautas_lista"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Medicamento del admin")


class ConfirmacionTomaTokenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="tok_user", password="ClaveSegura123!",
            first_name="Ana", last_name="Lopez",
        )
        cls.miembro = cls.usuario.hogar.miembros.get(es_principal=True)
        cls.medicamento = Medicamento.objects.create(
            usuario=cls.usuario, nombre="Paracetamol", cantidad=10,
            fecha_vencimiento="2031-01-01",
        )
        cls.pauta = PautaToma.objects.create(
            medicamento=cls.medicamento, miembro=cls.miembro,
            frecuencia="diaria", fecha_inicio=__import__("datetime").date(2020, 1, 1),
        )

    def test_token_confirma_toma(self):
        from datetime import date
        from botiquin.notificaciones import generar_token_confirmacion
        hoy = date.today()
        token = generar_token_confirmacion(self.pauta.pk, hoy)
        respuesta = self.client.get(reverse("botiquin:confirmar_toma", args=[token]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Toma registrada")
        self.assertTrue(
            TomaRegistrada.objects.filter(pauta=self.pauta, fecha=hoy, tomada=True).exists()
        )

    def test_token_invalido_redirige(self):
        respuesta = self.client.get(reverse("botiquin:confirmar_toma", args=["token-invalido"]))
        self.assertEqual(respuesta.status_code, 302)
