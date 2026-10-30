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

from .models import Categoria, Medicamento

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
        self.assertEqual(detalle.status_code, 404)

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
