"""Widgets personalizados del inventario."""
from django.core.validators import EMPTY_VALUES
from django.forms.widgets import ClearableFileInput, TextInput


class FotoCajaInput(ClearableFileInput):
    """Selector de foto con vista previa y opción de quitar la actual."""

    template_name = "botiquin/widgets/foto.html"
    initial_text = "Foto actual"
    input_text = "Cambiar foto"
    clear_checkbox_label = "Quitar foto actual"


class HorariosWidget(TextInput):
    """Varios campos de hora (uno por toma del día) en una misma fila.

    Todos los inputs usan el mismo nombre (`horarios`), así que el formulario
    los recibe como una lista y cada valor se convierte en un horario
    independiente de la pauta.
    """

    template_name = "botiquin/widgets/horarios.html"

    def value_from_datadict(self, data, files, name):
        """Lee todos los valores enviados con el mismo nombre."""
        if hasattr(data, "getlist"):
            return data.getlist(name)
        value = data.get(name)
        if value in (None, ""):
            return []
        if isinstance(value, (list, tuple)):
            return list(value)
        return [value]

    def format_value(self, value):
        """Convierte las horas en texto HH:MM."""
        if value in EMPTY_VALUES:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]
        return [
            v.strftime("%H:%M") if hasattr(v, "strftime") else str(v)
            for v in value
            if v not in (None, "")
        ]

    def get_context(self, name, value, attrs):
        contexto = super().get_context(name, value, attrs)
        filas = self.format_value(value)
        # Siempre hay al menos un campo para escribir la primera hora.
        contexto["widget"]["filas"] = filas or [""]
        return contexto
