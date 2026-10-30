"""URLs de la app cuentas."""
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import forms, views

app_name = "cuentas"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("login/", views.IniciarSesionView.as_view(), name="login"),
    path("logout/", views.cerrar_sesion, name="logout"),
    path("perfil/", views.perfil, name="perfil"),

    # Restablecimiento de contraseña
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            form_class=forms.RestablecerPasswordForm,
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            html_email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("cuentas:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("cuentas:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
