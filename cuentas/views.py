"""Vistas de autenticación y perfil de Mi Botiquín Digital."""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import LoginForm, PerfilForm, RegistroForm
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
            return redirect("cuentas:perfil")
    else:
        form = RegistroForm()

    return render(request, "registration/registro.html", {"form": form})


@require_POST
def cerrar_sesion(request):
    """Cierre de sesión seguro (solo por POST)."""
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("cuentas:login")


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
