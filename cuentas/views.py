"""Vistas de autenticación y perfil de Mi Botiquín Digital."""
import io
import secrets

try:
    import qrcode
except ImportError:  # pragma: no cover
    qrcode = None
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from .forms import (
    CodigoVerificacionForm,
    LoginForm,
    MiembroHogarForm,
    UnirseHogarForm,
    NuevaPasswordForm,
    PerfilForm,
    RegistroForm,
    RestablecerPasswordForm,
)
from .models import Hogar, MiembroHogar, Usuario


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
            return redirect("inicio")
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


def _es_admin_principal(request):
    """Verifica si el usuario actual es el administrador principal de su hogar."""
    if request.user.hogar is None:
        return False
    return MiembroHogar.objects.filter(
        usuario=request.user, hogar=request.user.hogar, es_principal=True
    ).exists()


def _unir_usuario_a_hogar(usuario, hogar):
    """Vincula al usuario con el hogar indicado y crea su perfil de miembro."""
    if usuario.hogar_id == hogar.pk:
        return False, "Ya perteneces a este hogar."

    usuario.hogar = hogar
    usuario.save(update_fields=["hogar"])

    if not MiembroHogar.objects.filter(hogar=hogar, usuario=usuario).exists():
        nombre_base = usuario.get_full_name() or usuario.username
        nombre = nombre_base
        sufijo = 2
        while MiembroHogar.objects.filter(hogar=hogar, nombre__iexact=nombre).exists():
            nombre = f"{nombre_base} ({sufijo})"
            sufijo += 1

        # El usuario solo puede estar vinculado a un MiembroHogar. Si ya estaba
        # enlazado con otro hogar, se reutiliza ese registro cambiando el hogar.
        miembro_previo = MiembroHogar.objects.filter(usuario=usuario).first()
        if miembro_previo is not None:
            miembro_previo.hogar = hogar
            miembro_previo.nombre = nombre
            miembro_previo.relacion = "otro"
            miembro_previo.es_principal = False
            miembro_previo.save()
        else:
            MiembroHogar.objects.create(
                hogar=hogar,
                usuario=usuario,
                nombre=nombre,
                relacion="otro",
                es_principal=False,
            )

    return True, f"Te uniste a «{hogar.nombre}»."


@login_required
def unirse_hogar(request, codigo=None):
    """Unirse a un hogar con su código de invitación (GET pre-rellena el código)."""
    hogar_inicial = None
    if codigo:
        try:
            hogar_inicial = Hogar.objects.get(codigo_invitacion__iexact=codigo)
        except Hogar.DoesNotExist:
            messages.error(request, "Ese código de invitación no es válido.")

    if request.method == "POST":
        form = UnirseHogarForm(request.POST)
        if form.is_valid():
            hogar = form.cleaned_data["codigo"]
            cambio, mensaje = _unir_usuario_a_hogar(request.user, hogar)
            if cambio:
                messages.success(request, mensaje)
            else:
                messages.info(request, mensaje)
            return redirect("cuentas:familia")
    else:
        form = UnirseHogarForm(
            initial={"codigo": hogar_inicial.codigo_invitacion} if hogar_inicial else None
        )

    return render(
        request,
        "cuentas/unirse.html",
        {"form": form, "hogar_inicial": hogar_inicial},
    )


@login_required
@require_POST
def regenerar_codigo(request):
    """Regenera el código de invitación del hogar. Solo el administrador principal."""
    if not _es_admin_principal(request):
        messages.error(
            request,
            "Solo el administrador principal puede regenerar el código de invitación.",
        )
        return redirect("cuentas:familia")

    hogar = request.user.hogar
    if hogar is None:
        raise Http404

    hogar.codigo_invitacion = ""
    hogar.save()  # save() regenera el código si está vacío
    messages.success(
        request,
        f"Se generó un nuevo código de invitación: {hogar.codigo_invitacion}",
    )
    return redirect("cuentas:familia")


@login_required
@require_POST
def salir_hogar(request):
    """Permite a un miembro no principal abandonar voluntariamente el hogar."""
    hogar_actual = request.user.hogar
    if hogar_actual is None:
        messages.info(request, "No perteneces a ningún hogar.")
        return redirect("cuentas:familia")

    if _es_admin_principal(request):
        messages.error(
            request,
            "Eres el administrador de este hogar y no puedes abandonarlo. "
            "Puedes eliminar integrantes o regenerar el código, pero la cuenta "
            "principal debe permanecer.",
        )
        return redirect("cuentas:familia")

    # Eliminar el MiembroHogar vinculado al usuario en este hogar.
    MiembroHogar.objects.filter(
        hogar=hogar_actual, usuario=request.user
    ).delete()

    # Crear un hogar personal nuevo para el usuario (como al registrarse).
    nombre_completo = request.user.get_full_name() or request.user.username
    nuevo_hogar = Hogar.objects.create(nombre=f"Hogar de {nombre_completo}")
    request.user.hogar = nuevo_hogar
    request.user.save(update_fields=["hogar"])
    MiembroHogar.objects.create(
        hogar=nuevo_hogar,
        usuario=request.user,
        nombre=nombre_completo,
        relacion="principal",
        es_principal=True,
    )

    messages.success(
        request,
        "Saliste del hogar compartido. Tu botiquín personal se mantuvo intacto.",
    )
    return redirect("cuentas:familia")


@login_required
def qr_invitacion(request):
    """Genera un código QR con el enlace para unirse al hogar del usuario."""
    if qrcode is None:
        return HttpResponse("qrcode no instalado", status=501, content_type="text/plain")
    if request.user.hogar is None:
        raise Http404

    url = request.build_absolute_uri(
        reverse("cuentas:unirse_hogar_codigo", args=[request.user.hogar.codigo_invitacion])
    )
    imagen = qrcode.make(url)
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    buffer.seek(0)
    respuesta = HttpResponse(buffer.getvalue(), content_type="image/png")
    respuesta["Cache-Control"] = "private, max-age=300"
    return respuesta


@login_required
def escanear_qr(request):
    """Pantalla para escanear un código QR de invitación con la cámara."""
    return render(request, "cuentas/escanear_qr.html", {})


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


def _miembro_del_hogar(request, pk):
    """Integrante del hogar del usuario.

    Lanza Http404 si no existe; PermissionDenied si pertenece a otro hogar.
    """
    from django.core.exceptions import PermissionDenied

    if request.user.hogar is None:
        raise Http404
    miembro = MiembroHogar.objects.filter(pk=pk).first()
    if miembro is None:
        raise Http404
    if miembro.hogar_id != request.user.hogar_id:
        raise PermissionDenied(
            "No tienes permiso para acceder a ese integrante de la familia."
        )
    return miembro


@login_required
def familia(request):
    """Lista de integrantes y alta de nuevos miembros.

    Solo el administrador principal puede agregar nuevos integrantes.
    """
    hogar = request.user.hogar
    es_principal = _es_admin_principal(request)

    if request.method == "POST" and hogar is not None:
        if not es_principal:
            messages.error(
                request,
                "Solo el administrador principal puede agregar integrantes a la familia.",
            )
            return redirect("cuentas:familia")

        form = MiembroHogarForm(request.POST, hogar=hogar)
        if form.is_valid():
            miembro = form.save(commit=False)
            miembro.hogar = hogar
            miembro.save()
            messages.success(request, f"«{miembro.nombre}» se agregó a tu familia.")
            return redirect("cuentas:familia")
    else:
        form = MiembroHogarForm(hogar=hogar)

    miembros = (
        hogar.miembros.annotate(total_medicamentos=Count("medicamentos"))
        if hogar is not None
        else MiembroHogar.objects.none()
    )

    administrador = (
        hogar.miembros.filter(es_principal=True).first()
        if hogar is not None
        else None
    )

    return render(
        request,
        "cuentas/familia.html",
        {
            "form": form,
            "miembros": miembros,
            "hogar": hogar,
            "es_principal": es_principal,
            "administrador": administrador,
        },
    )

    miembros = (
        hogar.miembros.annotate(total_medicamentos=Count("medicamentos"))
        if hogar is not None
        else MiembroHogar.objects.none()
    )

    return render(
        request,
        "cuentas/familia.html",
        {"form": form, "miembros": miembros, "hogar": hogar},
    )


@login_required
def editar_miembro(request, pk):
    miembro = _miembro_del_hogar(request, pk)

    if not _es_admin_principal(request):
        messages.error(
            request,
            "Solo el administrador principal puede editar integrantes de la familia.",
        )
        return redirect("cuentas:familia")

    if request.method == "POST":
        form = MiembroHogarForm(
            request.POST, instance=miembro, hogar=request.user.hogar
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Los datos del integrante se actualizaron.")
            return redirect("cuentas:familia")
    else:
        form = MiembroHogarForm(instance=miembro, hogar=request.user.hogar)

    return render(
        request,
        "cuentas/miembro_form.html",
        {"form": form, "miembro": miembro, "es_principal": True},
    )


@login_required
def eliminar_miembro(request, pk):
    """Confirmación (GET) y eliminación (POST). Los medicamentos quedan sin asignar.

    Solo el administrador principal puede eliminar integrantes.
    """
    miembro = _miembro_del_hogar(request, pk)

    if not _es_admin_principal(request):
        messages.error(
            request,
            "Solo el administrador principal puede eliminar integrantes de la familia.",
        )
        return redirect("cuentas:familia")

    if miembro.es_principal:
        messages.error(request, "El perfil principal no se puede eliminar.")
        return redirect("cuentas:familia")

    if request.method == "POST":
        nombre = miembro.nombre
        miembro.delete()
        messages.success(request, f"«{nombre}» se quitó de tu familia.")
        return redirect("cuentas:familia")

    return render(
        request,
        "cuentas/miembro_eliminar.html",
        {"miembro": miembro, "total_medicamentos": miembro.medicamentos.count()},
    )
