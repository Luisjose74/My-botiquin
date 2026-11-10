"""Formulario de contacto del sitio público."""
import time

from django import forms

CAMPOS = {"class": "campo"}
CAMPOS_SELECT = {"class": "campo campo-select"}

#: Motivos que puede elegir quien escribe.
ASUNTOS = (
    ("consulta", "Consulta sobre el uso de la aplicación"),
    ("sugerencia", "Sugerencia o mejora"),
    ("error", "Reportar un error"),
    ("institucional", "Asunto institucional o académico"),
    ("otro", "Otro asunto"),
)

#: Etiquetas legibles de cada motivo (para el correo).
ETIQUETAS_ASUNTO = dict(ASUNTOS)


class ContactoForm(forms.Form):
    """Datos para escribir al equipo del proyecto.

    Incluye dos protecciones sencillas contra el envío automatizado:
    un campo trampa invisible (`sitio_web`) y la marca de tiempo del
    formulario (`inicio`), que debe permanecer abierto unos segundos.
    """

    nombre = forms.CharField(
        label="Nombre",
        max_length=120,
        required=True,
        widget=forms.TextInput(
            attrs={**CAMPOS, "placeholder": "Tu nombre", "autocomplete": "name"}
        ),
    )
    correo = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(
            attrs={
                **CAMPOS,
                "placeholder": "tucorreo@ejemplo.com",
                "autocomplete": "email",
            }
        ),
    )
    asunto = forms.ChoiceField(
        label="Motivo",
        required=True,
        choices=ASUNTOS,
        widget=forms.Select(attrs=CAMPOS_SELECT),
    )
    mensaje = forms.CharField(
        label="Mensaje",
        max_length=2000,
        required=True,
        widget=forms.Textarea(
            attrs={
                **CAMPOS,
                "rows": 6,
                "placeholder": "Cuéntanos en qué podemos ayudarte.",
            }
        ),
    )
    # Campo trampa: invisible para las personas, relleno para los bots.
    sitio_web = forms.CharField(
        label="",
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "tabindex": "-1",
                "autocomplete": "off",
                "aria-hidden": "true",
            }
        ),
    )
    # Momento en que se pintó el formulario (anti-bot).
    inicio = forms.CharField(required=False, widget=forms.HiddenInput())

    #: Segundos mínimos que el formulario debe permanecer abierto.
    MINIMO_SEGUNDOS = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #: True si el envío parece provenir de un bot (no se envía el correo).
        self.envio_simulado = False

    def clean(self):
        datos = super().clean()

        if (datos.get("sitio_web") or "").strip():
            self.envio_simulado = True
            return datos

        marca = (datos.get("inicio") or "").strip()
        if marca.isdigit():
            if time.time() - int(marca) < self.MINIMO_SEGUNDOS:
                self.envio_simulado = True

        return datos
