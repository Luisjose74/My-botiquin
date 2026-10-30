"""URLs de la app cuentas."""
from django.urls import path, reverse_lazy

from . import views

app_name = "cuentas"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("login/", views.IniciarSesionView.as_view(), name="login"),
    path("logout/", views.cerrar_sesion, name="logout"),
    path("perfil/", views.perfil, name="perfil"),

    # Restablecimiento de contraseña por código de 6 dígitos (2 pasos)
    path(
        "password-reset/",
        views.SolicitarCodigoPasswordView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/verify/",
        views.VerificarCodigoPasswordView.as_view(),
        name="password_reset_verify",
    ),
    path(
        "password-reset/password/",
        views.NuevaPasswordView.as_view(),
        name="password_reset_password",
    ),
    path(
        "password-reset/complete/",
        views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
