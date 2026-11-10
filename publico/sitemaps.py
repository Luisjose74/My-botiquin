"""Mapa del sitio con las páginas públicas de Mi Botiquín Digital.

Las páginas privadas (panel, inventario, cuentas) no se incluyen: solo se
indexan las páginas públicas del sitio.
"""
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class PublicoSitemap(Sitemap):
    """Páginas públicas del sitio, con prioridad y frecuencia de cambio."""

    changefreq = "monthly"
    priority = 0.6

    #: Prioridad por página: la portada pesa más que los textos legales.
    PRIORIDADES = {
        "publico:portada": 0.9,
        "publico:educacion": 0.8,
        "publico:acerca_de": 0.7,
        "publico:contacto": 0.6,
        "publico:privacidad": 0.4,
        "publico:terminos": 0.4,
    }

    def items(self):
        return [
            "publico:portada",
            "publico:educacion",
            "publico:acerca_de",
            "publico:contacto",
            "publico:privacidad",
            "publico:terminos",
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self.PRIORIDADES.get(item, self.priority)

    def get_domain(self, site=None):
        """Usa el dominio de SITE_URL si está configurado."""
        base = getattr(settings, "SITE_URL", "").strip()
        if base:
            return urlsplit(base).netloc
        return super().get_domain(site)

    def get_protocol(self, protocol=None):
        """Usa el esquema de SITE_URL si está configurado."""
        base = getattr(settings, "SITE_URL", "").strip()
        if base:
            return urlsplit(base).scheme
        return super().get_protocol(protocol)
