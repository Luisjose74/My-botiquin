"""Formularios del inventario de medicamentos."""
from django import forms
from django.core.files.uploadedfile import UploadedFile

from .models import Medicamento
from .widgets import FotoCajaInput


class MedicamentoForm(forms.ModelForm):
    """Registro / edición de una caja de medicamento."""

    class Meta:
        model = Medicamento
        fields = (
            "nombre",
            "categoria",
            "presentacion",
            "cantidad",
            "lote",
            "registro_sanitario",
            "fecha_vencimiento",
            "condicion_almacenamiento",
            "ubicacion",
            "miembro",
            "notas_conservacion",
            "notas",
            "foto",
        )
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "campo",
                    "placeholder": "Ej.: Paracetamol 500 mg",
                    "autofocus": True,
                }
            ),
            "categoria": forms.Select(attrs={"class": "campo campo-select"}),
            "presentacion": forms.Select(attrs={"class": "campo campo-select"}),
            "cantidad": forms.NumberInput(
                attrs={"class": "campo", "min": 0, "placeholder": "0"}
            ),
            "lote": forms.TextInput(
                attrs={"class": "campo", "placeholder": "Ej.: L-2026A"}
            ),
            "registro_sanitario": forms.TextInput(
                attrs={"class": "campo", "placeholder": "Ej.: INVIMA 2024M-001"}
            ),
            "fecha_vencimiento": forms.DateInput(
                attrs={"class": "campo", "type": "date"},
                format="%Y-%m-%d",
            ),
            "condicion_almacenamiento": forms.Select(
                attrs={"class": "campo campo-select"}
            ),
            "ubicacion": forms.TextInput(
                attrs={
                    "class": "campo",
                    "placeholder": "Ej.: botiquín del baño",
                }
            ),
            "miembro": forms.Select(attrs={"class": "campo campo-select"}),
            "notas_conservacion": forms.Textarea(
                attrs={
                    "class": "campo",
                    "rows": 2,
                    "placeholder": "Ej.: no refrigerar, mantener en su caja original.",
                }
            ),
            "notas": forms.Textarea(
                attrs={
                    "class": "campo",
                    "rows": 3,
                    "placeholder": "Observaciones adicionales…",
                }
            ),
            "foto": FotoCajaInput(
                attrs={
                    "class": "campo campo-file",
                    "accept": "image/*",
                    "aria-label": "Foto de la caja",
                }
            ),
        }
        labels = {
            "fecha_vencimiento": "Fecha de vencimiento",
            "miembro": "¿Quién lo usa?",
        }
        help_texts = {
            "foto": "Formatos permitidos: JPG, PNG o WEBP. Máximo 5 MB.",
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

        self.fields["categoria"].required = True
        self.fields["categoria"].empty_label = "Selecciona una categoría"

        if usuario and usuario.hogar:
            self.fields["miembro"].queryset = usuario.hogar.miembros.all()
        else:
            self.fields["miembro"].queryset = (
                self.fields["miembro"].queryset.none()
            )
        self.fields["miembro"].empty_label = "Sin asignar"
        self.fields["miembro"].required = False
        self.fields["lote"].required = False
        self.fields["registro_sanitario"].required = False
        self.fields["ubicacion"].required = False

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")

        # En edición, si no se sube una imagen nueva, Django devuelve la
        # FieldFile existente: no hay que volver a validarla.
        if not isinstance(foto, UploadedFile):
            return foto

        if foto.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "La imagen no puede superar los 5 MB."
            )

        tipos = {"image/jpeg", "image/png", "image/webp"}
        if getattr(foto, "content_type", None) not in tipos:
            raise forms.ValidationError(
                "Sube una imagen en formato JPG, PNG o WEBP."
            )
        return foto
