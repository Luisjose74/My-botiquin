"""Formularios de autenticación y perfil de Mi Botiquín Digital."""
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm as DjangoPasswordResetForm,
    UserCreationForm,
)
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import MiembroHogar, Usuario

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


class VerificarCodigoPasswordForm(forms.Form):
    """Verificación del código de 6 dígitos y nueva contraseña."""

    code = forms.CharField(
        label="Código de verificación",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                **CAMPOS,
                "placeholder": "123456",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
            }
        ),
    )
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={**CAMPOS, "placeholder": "Mínimo 8 caracteres", "autocomplete": "new-password"}
        ),
    )
    new_password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={**CAMPOS, "placeholder": "Repite tu contraseña", "autocomplete": "new-password"}
        ),
    )

    def __init__(self, *args, email=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.email = email

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError("Ingresa un código de 6 dígitos.")
        if not self.email:
            raise forms.ValidationError("No hay una solicitud de recuperación activa.")
        stored = cache.get("password_reset_code:{}".format(self.email.lower()))
        if not stored or stored != code:
            raise forms.ValidationError("El código es inválido o ha expirado.")
        return code

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("new_password1")
        password2 = cleaned.get("new_password2")
        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "Las dos contraseñas no coinciden.")
        if password1 and self.email:
            usuario = Usuario.objects.filter(email__iexact=self.email).first()
            if usuario:
                try:
                    password_validation.validate_password(password1, usuario)
                except DjangoValidationError as error:
                    self.add_error("new_password1", error)
        return cleaned


class CodigoVerificacionForm(forms.Form):
    """Paso 1: validación del código de 6 dígitos."""

    code = forms.CharField(
        label="Código de verificación",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                **CAMPOS,
                "placeholder": "123456",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
            }
        ),
    )

    def __init__(self, *args, email=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.email = email

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError("Ingresa un código de 6 dígitos.")
        if not self.email:
            raise forms.ValidationError("No hay una solicitud de recuperación activa.")
        stored = cache.get("password_reset_code:{}".format(self.email.lower()))
        if not stored or stored != code:
            raise forms.ValidationError("El código es inválido o ha expirado.")
        return code


class NuevaPasswordForm(forms.Form):
    """Paso 2: nueva contraseña y confirmación."""

    new_password1 = forms.CharField(
        label="Nueva contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={**CAMPOS, "placeholder": "Mínimo 8 caracteres", "autocomplete": "new-password"}
        ),
    )
    new_password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={**CAMPOS, "placeholder": "Repite tu contraseña", "autocomplete": "new-password"}
        ),
    )

    def __init__(self, *args, email=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.email = email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("new_password1")
        password2 = cleaned.get("new_password2")
        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "Las dos contraseñas no coinciden.")
        if password1 and self.email:
            usuario = Usuario.objects.filter(email__iexact=self.email).first()
            if usuario:
                try:
                    password_validation.validate_password(password1, usuario)
                except DjangoValidationError as error:
                    self.add_error("new_password1", error)
        return cleaned


class MiembroHogarForm(forms.ModelForm):
    """Alta y edición de un integrante de la familia.

    El perfil principal conserva su relación; no se puede crear otro principal.
    """

    class Meta:
        model = MiembroHogar
        fields = ("nombre", "relacion")
        labels = {"nombre": "Nombre", "relacion": "Relación"}
        widgets = {
            "nombre": forms.TextInput(
                attrs={**CAMPOS, "placeholder": "Ej. Mamá", "autocomplete": "off"}
            ),
            "relacion": forms.Select(attrs=CAMPOS_SELECT),
        }

    def __init__(self, *args, hogar=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.hogar = hogar
        es_principal = self.instance.pk is not None and self.instance.es_principal
        if es_principal:
            self.fields["relacion"].choices = list(MiembroHogar.RELACIONES)
            self.fields["relacion"].disabled = True
        else:
            self.fields["relacion"].choices = [("", "Selecciona una relación")] + [
                (valor, etiqueta)
                for valor, etiqueta in MiembroHogar.RELACIONES
                if valor != "principal"
            ]

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if not nombre:
            raise forms.ValidationError("Escribe el nombre de la persona.")
        if self.hogar is not None:
            existe = (
                MiembroHogar.objects.filter(hogar=self.hogar, nombre__iexact=nombre)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if existe:
                raise forms.ValidationError(
                    "Ya tienes un integrante con ese nombre."
                )
        return nombre


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # WhatsApp se oculta hasta que exista el envío. El modelo lo conserva.
        self.fields["canal_alertas"].choices = [
            (valor, etiqueta)
            for valor, etiqueta in Usuario.CANAL_ALERTAS
            if valor != "whatsapp"
        ]
        if self.instance.pk and self.instance.canal_alertas == "whatsapp":
            self.initial["canal_alertas"] = "notificacion"

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
