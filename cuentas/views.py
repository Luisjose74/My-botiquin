"""Vistas de autenticación y perfil de Mi Botiquín Digital."""
import secrets
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.crypto import get_random_string
from django.shortcuts import redirect, render
from django.views.generic import FormView, TemplateView
from django.views.decorators.http import require_POST

from .forms import (
    LoginForm,
    PerfilForm,
    RegistroForm,
    CodigoVerificacionForm,
    NuevaPasswordForm,
    RestablecerPasswordForm,
)
from .models import MiembroHogar, Usuario
from .models import MiembroHogar


class IniciarSesionView(LoginView):
    """Inicio de sesión con plantilla y formulario propios."""

    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        usuario = form.get_user()
        nombre = usuario.first_name or usuario.username
        messages.success(self.request, f"¡Hola de nuevo, {nombre}! 👋")
        return super().form_valid(form)


def registro(request):
    """Registro de usuario. La señal crea su Hogar y MiembroHogar principal."""
    if request.user.is_authenticated:
        return redirect("cuentas:perfil")

    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            messages.success(
                request,
                "¡Tu botiquín digital está listo! Ya puedes empezar a "
                "registrar tus medicamentos.",
            )
            return redirect("botiquin:lista")
    else:
        form = RegistroForm()

    return render(request, "registration/registro.html", {"form": form})


@require_POST
def cerrar_sesion(request):
    """Cierre de sesión seguro (solo por POST)."""
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("cuentas:login")



def _generar_codigo_verificacion():
    """Genera un código numérico de 6 dígitos."""
    return "{:06d}".format(secrets.randbelow(900000) + 100000)


def _enviar_codigo_password(email, codigo):
    """Envía el código de verificación por correo (texto + HTML)."""
    contexto = {
        "codigo": codigo,
        "email": email,
        "minutos": 10,
    }
    texto = render_to_string("registration/password_reset_email.txt", contexto)
    html = render_to_string("registration/password_reset_email.html", contexto)
    mensaje = EmailMultiAlternatives(
        subject="Tu código de verificación - Mi Botiquín Digital",
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    mensaje.attach_alternative(html, "text/html")
    mensaje.send()


class SolicitarCodigoPasswordView(FormView):
    """Solicita el correo y envía un código de verificación de 6 dígitos."""

    template_name = "registration/password_reset_form.html"
    form_class = RestablecerPasswordForm
    success_url = reverse_lazy("cuentas:password_reset_verify")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        codigo = _generar_codigo_verificacion()
        cache.set(
            "password_reset_code:{}".format(email.lower()), codigo, timeout=600
        )
        self.request.session["password_reset_email"] = email
        _enviar_codigo_password(email, codigo)
        messages.success(
            self.request,
            "Te enviamos un código de verificación de 6 dígitos a tu correo.",
        )
        return super().form_valid(form)


class VerificarCodigoPasswordView(FormView):
    """Paso 1: valida el código de 6 dígitos."""

    template_name = "registration/password_reset_verify.html"
    form_class = CodigoVerificacionForm
    success_url = reverse_lazy("cuentas:password_reset_password")

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("password_reset_email"):
            return redirect("cuentas:password_reset")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["email"] = self.request.session.get("password_reset_email")
        return kwargs

    def form_valid(self, form):
        self.request.session["password_reset_code_verified"] = True
        return super().form_valid(form)


class NuevaPasswordView(FormView):
    """Paso 2: establece la nueva contraseña."""

    template_name = "registration/password_reset_password.html"
    form_class = NuevaPasswordForm
    success_url = reverse_lazy("cuentas:password_reset_complete")

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("password_reset_email"):
            return redirect("cuentas:password_reset")
        if not request.session.get("password_reset_code_verified"):
            return redirect("cuentas:password_reset_verify")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["email"] = self.request.session.get("password_reset_email")
        return kwargs

    def form_valid(self, form):
        email = self.request.session.get("password_reset_email")
        usuario = Usuario.objects.filter(email__iexact=email).first()
        if usuario is None:
            form.add_error(None, "No se encontró un usuario con ese correo.")
            return self.form_invalid(form)

        usuario.set_password(form.cleaned_data["new_password1"])
        usuario.save()
        cache.delete("password_reset_code:{}".format(email.lower()))
        self.request.session.pop("password_reset_email", None)
        self.request.session.pop("password_reset_code_verified", None)
        messages.success(
            self.request, "Tu contraseña se actualizó correctamente."
        )
        return super().form_valid(form)


class PasswordResetCompleteView(TemplateView):
    """Pantalla final tras restablecer la contraseña."""

    template_name = "registration/password_reset_complete.html"


@login_required
def perfil(request):
    """Vista de perfil: datos del usuario, hogar y sus miembros."""
    if request.method == "POST":
        form = PerfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("cuentas:perfil")
    else:
        form = PerfilForm(instance=request.user)

    hogar = request.user.hogar
    miembros = hogar.miembros.all() if hogar else MiembroHogar.objects.none()

    return render(
        request,
        "cuentas/perfil.html",
        {"form": form, "hogar": hogar, "miembros": miembros},
    )
