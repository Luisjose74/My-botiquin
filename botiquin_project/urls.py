"""
URL configuration for botiquin_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from botiquin.views import inicio

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("cuentas.urls")),
    path("botiquin/", include("botiquin.urls")),
    # Panel privado de la aplicación (requiere iniciar sesión).
    path("app/", inicio, name="inicio"),
    # Páginas públicas e institucionales (portada, educación, legales).
    path("", include("publico.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
