"""Formularios del inventario de medicamentos."""
from django import forms
from django.core.files.uploadedfile import UploadedFile

from .models import Medicamento, PautaToma
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


class PautaTomaForm(forms.ModelForm):
    """Programación de tomas de un medicamento para un integrante."""

    class Meta:
        model = PautaToma
        fields = (
            "medicamento",
            "miembro",
            "dosis",
            "frecuencia",
            "intervalo_dias",
            "dias_mes",
            "dias_semana",
            "hora",
            "fecha_inicio",
            "fecha_fin",
            "activa",
        )
        widgets = {
            "medicamento": forms.Select(attrs={"class": "campo campo-select"}),
            "miembro": forms.Select(attrs={"class": "campo campo-select"}),
            "dosis": forms.NumberInput(attrs={"class": "campo", "min": 1}),
            "frecuencia": forms.Select(attrs={"class": "campo campo-select"}),
            "intervalo_dias": forms.NumberInput(attrs={"class": "campo", "min": 1}),
            "dias_mes": forms.TextInput(
                attrs={"class": "campo", "placeholder": "Ej.: 14, 20"}
            ),
            "dias_semana": forms.TextInput(
                attrs={"class": "campo", "placeholder": "Ej.: 0,2,4 (Lun,Mié,Vie)"}
            ),
            "hora": forms.TimeInput(attrs={"class": "campo", "type": "time"}),
            "fecha_inicio": forms.DateInput(
                attrs={"class": "campo", "type": "date"}, format="%Y-%m-%d"
            ),
            "fecha_fin": forms.DateInput(
                attrs={"class": "campo", "type": "date"}, format="%Y-%m-%d"
            ),
            "activa": forms.CheckboxInput(attrs={"class": "campo-checkbox"}),
        }
        labels = {
            "medicamento": "Medicamento",
            "miembro": "Integrante",
            "dosis": "Dosis por toma",
            "frecuencia": "Frecuencia",
            "intervalo_dias": "Cada N días",
            "dias_mes": "Días del mes",
            "dias_semana": "Días de la semana",
            "hora": "Hora",
            "fecha_inicio": "Fecha de inicio",
            "fecha_fin": "Fecha de fin (opcional)",
            "activa": "Pauta activa",
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        if usuario and usuario.hogar:
            self.fields["medicamento"].queryset = Medicamento.objects.filter(
                usuario__hogar=usuario.hogar, activo=True
            )
            self.fields["miembro"].queryset = usuario.hogar.miembros.all()
        else:
            self.fields["medicamento"].queryset = Medicamento.objects.none()
            self.fields["miembro"].queryset = (
                self.fields["miembro"].queryset.none()
            )
        self.fields["medicamento"].empty_label = "Selecciona un medicamento"
        self.fields["miembro"].empty_label = "Selecciona un integrante"
        self.fields["fecha_fin"].required = False
        self.fields["hora"].required = False

    def clean(self):
        cleaned = super().clean()
        frecuencia = cleaned.get("frecuencia")
        if frecuencia == "cada_n_dias" and not cleaned.get("intervalo_dias"):
            self.add_error("intervalo_dias", "Indica cada cuántos días.")
        if frecuencia == "dias_mes" and not cleaned.get("dias_mes"):
            self.add_error("dias_mes", "Indica los días del mes.")
        if frecuencia == "dias_semana" and not cleaned.get("dias_semana"):
            self.add_error("dias_semana", "Indica los días de la semana.")
        return cleaned
