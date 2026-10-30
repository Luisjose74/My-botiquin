"""Widgets personalizados del inventario."""
from django.forms.widgets import ClearableFileInput


class FotoCajaInput(ClearableFileInput):
    """Selector de foto con vista previa y opción de quitar la actual."""

    template_name = "botiquin/widgets/foto.html"
    initial_text = "Foto actual"
    input_text = "Cambiar foto"
    clear_checkbox_label = "Quitar foto actual"
