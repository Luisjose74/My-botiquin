"""Middleware para manejar permisos denegados de forma amigable."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class PermisoDenegadoMiddleware:
    """Convierte PermissionDenied en una redirección con mensaje amigable."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, PermissionDenied):
            return None
        mensaje = str(exception) or "No tienes permiso para realizar esta acción."
        messages.error(request, mensaje)
        destino = request.META.get("HTTP_REFERER")
        if not destino:
            destino = "/"
        return redirect(destino)