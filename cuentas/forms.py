"""Formularios de autenticación y perfil de Mi Botiquín Digital."""
from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm as DjangoPasswordResetForm,
    UserCreationForm,
)

from .models import Usuario

CAMPOS = {"class": "campo"}
CAMPOS_SELECT = {"class": "campo campo-select"}
CAMPOS_FILE = {"class": "campo campo-file"}


class RegistroForm(UserCreationForm):
    """Registro de una cuenta nueva (crea Hogar y perfil principal vía signal)."""

    first_name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={**CAMPOS, "placeholder": "Ej. Juan", "autocomplete": "off"}),
    )
    last_name = forms.CharField(
        label="Apellido",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={**CAMPOS, "placeholder": "Pérez", "autocomplete": "off"}),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(
            attrs={**CAMPOS, "placeholder": "tucorreo@ejemplo.com", "autocomplete": "off"}
        ),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={**CAMPOS, "placeholder": "300 123 4567", "autocomplete": "off"}
        ),
    )

    class Meta:
        model = Usuario
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "telefono",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {**CAMPOS, "placeholder": "juan_perez", "autocomplete": "off"}
        )
        self.fields["password1"].widget.attrs.update(
            {**CAMPOS, "placeholder": "Mínimo 8 caracteres", "autocomplete": "off"}
        )
        self.fields["password1"].help_text = ""
        self.fields["password2"].widget.attrs.update(
            {**CAMPOS, "placeholder": "Repite tu contraseña", "autocomplete": "off"}
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este correo electrónico."
            )
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.email = self.cleaned_data["email"]
        usuario.first_name = self.cleaned_data["first_name"]
        usuario.last_name = self.cleaned_data["last_name"]
        usuario.telefono = self.cleaned_data["telefono"]
        if commit:
            usuario.save()
        return usuario


class LoginForm(AuthenticationForm):
    """Inicio de sesión con estilos propios."""

    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(
            attrs={
                **CAMPOS,
                "autofocus": True,
                "placeholder": "Tu nombre de usuario",
                "autocomplete": "off",
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={**CAMPOS, "placeholder": "Tu contraseña", "autocomplete": "off"}
        ),
    )


class RestablecerPasswordForm(DjangoPasswordResetForm):
    """Restablecimiento con validación estricta de correo registrado."""

    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(
            attrs={
                **CAMPOS,
                "placeholder": "tucorreo@ejemplo.com",
                "autocomplete": "off",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Este correo no se encuentra registrado."
            )
        return email


class PerfilForm(forms.ModelForm):
    """Edición de los datos personales y preferencias del usuario."""

    class Meta:
        model = Usuario
        fields = (
            "first_name",
            "last_name",
            "email",
            "telefono",
            "foto",
            "canal_alertas",
        )
        widgets = {
            "first_name": forms.TextInput(attrs=CAMPOS),
            "last_name": forms.TextInput(attrs=CAMPOS),
            "email": forms.EmailInput(attrs=CAMPOS),
            "telefono": forms.TextInput(attrs=CAMPOS),
            "foto": forms.ClearableFileInput(attrs=CAMPOS_FILE),
            "canal_alertas": forms.Select(attrs=CAMPOS_SELECT),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email:
            return email
        existe = (
            Usuario.objects.filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if existe:
            raise forms.ValidationError(
                "Ya existe otra cuenta registrada con este correo electrónico."
            )
        return email
