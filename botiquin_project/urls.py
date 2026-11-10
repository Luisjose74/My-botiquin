"""
URL configuration for botiquin_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from botiquin.views import inicio
from publico.sitemaps import PublicoSitemap
from publico.views import robots_txt

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("cuentas.urls")),
    path("botiquin/", include("botiquin.urls")),
    # Panel privado de la aplicación (requiere iniciar sesión).
    path("app/", inicio, name="inicio"),
    # Archivos para los buscadores.
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": {"publico": PublicoSitemap}},
        name="sitemap",
    ),
    path("robots.txt", robots_txt, name="robots_txt"),
    # Páginas públicas e institucionales (portada, educación, legales).
    path("", include("publico.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
