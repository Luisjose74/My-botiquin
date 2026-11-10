"""Pruebas de las páginas públicas e institucionales (Fase 6)."""
import time

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from cuentas.models import Usuario

FRASES_RECOMENDACIONES = [
    "No consumas medicamentos vencidos",
    "Evita la automedicación",
    "Respeta las condiciones de almacenamiento",
    "No compartas medicamentos",
    "Consulta al personal de salud",
]

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


class PaginasPublicasTests(TestCase):
    """Las páginas públicas se ven sin iniciar sesión."""

    def test_portada_responde_sin_sesion(self):
        respuesta = self.client.get(reverse("publico:portada"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Organiza, cuida")
        self.assertContains(respuesta, "Crear mi botiquín gratis")
        self.assertContains(respuesta, "Iniciar sesión")

    def test_raiz_del_sitio_es_la_portada_publica(self):
        respuesta = self.client.get("/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "publico/portada.html")

    def test_portada_muestra_las_funciones_y_los_hitos(self):
        respuesta = self.client.get(reverse("publico:portada"))

        self.assertContains(respuesta, "Inventario digital del botiquín")
        self.assertContains(respuesta, "Alertas escalonadas de vencimiento")
        self.assertContains(respuesta, "Aviso a 30 días")
        self.assertContains(respuesta, "Aviso a 15 días")
        self.assertContains(respuesta, "Aviso a 5 días")

    def test_portada_enlaza_a_las_paginas_publicas(self):
        respuesta = self.client.get(reverse("publico:portada"))

        self.assertContains(respuesta, reverse("publico:educacion"))
        self.assertContains(respuesta, reverse("publico:acerca_de"))
        self.assertContains(respuesta, reverse("publico:privacidad"))
        self.assertContains(respuesta, reverse("publico:terminos"))

    def test_portada_incluye_datos_para_seo(self):
        respuesta = self.client.get(reverse("publico:portada"))

        self.assertContains(respuesta, '<meta name="description"')
        self.assertContains(respuesta, 'rel="canonical"')
        self.assertContains(respuesta, 'property="og:title"')

    def test_educacion_reutiliza_las_recomendaciones_centralizadas(self):
        respuesta = self.client.get(reverse("publico:educacion"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Recomendaciones de Regencia de Farmacia")
        for frase in FRASES_RECOMENDACIONES:
            self.assertContains(respuesta, frase)

    def test_educacion_incluye_las_secciones_de_la_guia(self):
        respuesta = self.client.get(reverse("publico:educacion"))

        self.assertContains(respuesta, "Cómo almacenar correctamente")
        self.assertContains(respuesta, "Qué hacer con los medicamentos vencidos")
        self.assertContains(respuesta, "Señales de alarma")

    def test_educacion_advierte_que_no_reemplaza_la_consulta(self):
        respuesta = self.client.get(reverse("publico:educacion"))

        self.assertContains(respuesta, "no diagnostica")

    def test_acerca_de_muestra_los_creditos_institucionales(self):
        respuesta = self.client.get(reverse("publico:acerca_de"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Universidad Pedagógica y Tecnológica de Colombia")
        self.assertContains(respuesta, "Neidy Julieth Rodríguez Patiño")
        self.assertContains(respuesta, "202410310")
        self.assertContains(respuesta, "Regencia de Farmacia")

    def test_acerca_de_explica_el_alcance_del_servicio(self):
        respuesta = self.client.get(reverse("publico:acerca_de"))

        self.assertContains(respuesta, "Lo que sí hace")
        self.assertContains(respuesta, "Lo que no hace")
        self.assertContains(respuesta, "No diagnostica ni prescribe medicamentos")

    def test_privacidad_cumple_con_la_ley_1581(self):
        respuesta = self.client.get(reverse("publico:privacidad"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ley 1581 de 2012")
        self.assertContains(respuesta, "Superintendencia de Industria y Comercio")
        self.assertContains(respuesta, "Conocer")
        self.assertContains(respuesta, "Suprimir")

    def test_terminos_define_los_limites_y_la_legislacion(self):
        respuesta = self.client.get(reverse("publico:terminos"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No diagnostica, no prescribe")
        self.assertContains(respuesta, "República de Colombia")

    def test_las_paginas_publicas_solo_aceptan_get(self):
        for nombre in ("portada", "acerca_de", "educacion", "privacidad", "terminos"):
            with self.subTest(pagina=nombre):
                respuesta = self.client.post(reverse(f"publico:{nombre}"))
                self.assertEqual(respuesta.status_code, 405)

    def test_el_panel_privado_sigue_requiriendo_sesion(self):
        respuesta = self.client.get(reverse("inicio"))

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/cuentas/login/", respuesta["Location"])

    def test_usuario_autenticado_ve_el_enlace_al_panel(self):
        usuario = Usuario.objects.create_user(
            username="publico_usuario",
            password="ClaveSegura123!",
            email="panel@example.com",
            first_name="Ana",
        )
        self.client.force_login(usuario)

        respuesta = self.client.get(reverse("publico:portada"))

        self.assertContains(respuesta, "Ir a mi botiquín")
        self.assertContains(respuesta, reverse("inicio"))

    def test_el_pie_de_pagina_muestra_los_datos_institucionales(self):
        respuesta = self.client.get(reverse("publico:portada"))

        self.assertContains(respuesta, "Facultad de Estudios a Distancia")
        self.assertContains(respuesta, "Sogamoso, Boyacá")
        self.assertContains(respuesta, "no diagnostica")


@override_settings(EMAIL_BACKEND=LOCMEM)
class SitemapYRobotsTests(TestCase):
    """Archivos para los buscadores."""

    def test_sitemap_lista_las_paginas_publicas(self):
        respuesta = self.client.get("/sitemap.xml")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "/educacion/")
        self.assertContains(respuesta, "/acerca-de/")
        self.assertContains(respuesta, "/contacto/")

    def test_sitemap_no_incluye_el_panel_privado(self):
        respuesta = self.client.get("/sitemap.xml")

        self.assertNotContains(respuesta, "/app/")
        self.assertNotContains(respuesta, "/cuentas/")

    def test_robots_txt_esta_disponible(self):
        respuesta = self.client.get("/robots.txt")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("text/plain", respuesta["Content-Type"])
        self.assertContains(respuesta, "User-agent: *")
        self.assertContains(respuesta, "Disallow: /app/")
        self.assertContains(respuesta, "Sitemap: ")


@override_settings(EMAIL_BACKEND=LOCMEM)
class FormularioContactoTests(TestCase):
    """Formulario público de contacto."""

    def setUp(self):
        mail.outbox = []

    def datos_validos(self, **cambios):
        datos = {
            "nombre": "Ana Pérez",
            "correo": "ana@example.com",
            "asunto": "consulta",
            "mensaje": "¿Cómo puedo registrar una pauta de toma?",
            "sitio_web": "",
            "inicio": str(int(time.time()) - 30),
        }
        datos.update(cambios)
        return datos

    def test_el_formulario_se_muestra_sin_sesion(self):
        respuesta = self.client.get(reverse("publico:contacto"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Contáctanos")
        self.assertContains(respuesta, 'name="nombre"')
        self.assertContains(respuesta, 'name="mensaje"')

    def test_un_mensaje_valido_envia_el_correo(self):
        respuesta = self.client.post(
            reverse("publico:contacto"), self.datos_validos(), follow=True
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertIn("Ana Pérez", correo.body)
        self.assertIn("¿Cómo puedo registrar una pauta de toma?", correo.body)
        self.assertEqual(correo.reply_to, ["ana@example.com"])
        self.assertContains(respuesta, "Gracias por escribirnos")

    def test_el_asunto_del_correo_usa_el_motivo_elegido(self):
        self.client.post(reverse("publico:contacto"), self.datos_validos())

        self.assertIn("Consulta", mail.outbox[0].subject)

    def test_un_mensaje_incompleto_no_envia_correo(self):
        respuesta = self.client.post(
            reverse("publico:contacto"),
            self.datos_validos(correo="correo-invalido"),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(respuesta, "Revisa los campos marcados")

    def test_el_campo_trampa_descarta_el_envio_de_bots(self):
        respuesta = self.client.post(
            reverse("publico:contacto"),
            self.datos_validos(sitio_web="http://spam.example"),
            follow=True,
        )

        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(respuesta, "Gracias por escribirnos")

    def test_un_envio_instantaneo_se_ignora(self):
        respuesta = self.client.post(
            reverse("publico:contacto"),
            self.datos_validos(inicio=str(int(time.time()))),
            follow=True,
        )

        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(respuesta, "Gracias por escribirnos")
