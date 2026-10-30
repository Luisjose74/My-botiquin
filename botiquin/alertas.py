"""Sincronización de alertas con el estado real del inventario.

Cada medicamento tiene como máximo una alerta activa, cuyo tipo corresponde a
su estado actual. Prioridad: agotado > vencido > próximo a vencer > stock bajo.
Las alertas se crean, reemplazan o eliminan según cambie ese estado.

Las alertas nuevas se avisan en la app siempre y, además, por correo cuando el
usuario tiene como canal preferido "correo".
"""
import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Alerta, EstadoInventario, Medicamento

logger = logging.getLogger(__name__)

ESTADO_A_TIPO = {
    EstadoInventario.AGOTADO: "agotado",
    EstadoInventario.VENCIDO: "vencido",
    EstadoInventario.PROXIMO: "por_vencer",
}


def tipo_de_alerta(medicamento):
    """Tipo de alerta que corresponde al estado actual, o None si no aplica."""
    tipo = ESTADO_A_TIPO.get(medicamento.estado)
    if tipo:
        return tipo
    if medicamento.stock_bajo:
        return "stock_bajo"
    return None


def _textos(medicamento, tipo):
    fecha = medicamento.fecha_vencimiento_formateada
    if tipo == "agotado":
        return (
            f"{medicamento.nombre}: sin existencias",
            "No quedan unidades en tu botiquín. Considera reabastecerlo.",
        )
    if tipo == "vencido":
        return (
            f"{medicamento.nombre}: vencido",
            f"Venció el {fecha}. No lo consumas y deséchalo de forma segura.",
        )
    if tipo == "stock_bajo":
        return (
            f"{medicamento.nombre}: stock bajo",
            f"Quedan {medicamento.cantidad} unidad"
            f"{'es' if medicamento.cantidad != 1 else ''}. "
            "Considera reabastecerlo pronto.",
        )
    return (
        f"{medicamento.nombre}: próximo a vencer",
        f"Vence el {fecha}, en {medicamento.dias_para_vencer} días.",
    )


def _url_panel_alertas():
    base = getattr(settings, "SITE_URL", "").rstrip("/")
    return f"{base}{reverse('botiquin:alertas')}" if base else ""


def enviar_alertas_por_correo(usuario, alertas):
    """Envía un único correo con las alertas nuevas del usuario.

    Devuelve True si el correo se envió. Los errores de SMTP se registran y no
    se propagan, para que el panel nunca falle por culpa del correo.
    """
    if not usuario.email:
        logger.warning("Usuario %s sin correo: no se envían alertas.", usuario.pk)
        return False

    total = len(alertas)
    contexto = {
        "usuario": usuario,
        "alertas": alertas,
        "total": total,
        "url_panel": _url_panel_alertas(),
    }
    asunto = (
        f"Mi Botiquín: {total} alerta nueva"
        if total == 1
        else f"Mi Botiquín: {total} alertas nuevas"
    )
    texto = render_to_string("botiquin/emails/alertas.txt", contexto)
    html = render_to_string("botiquin/emails/alertas.html", contexto)

    mensaje = EmailMultiAlternatives(
        subject=asunto,
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[usuario.email],
    )
    mensaje.attach_alternative(html, "text/html")
    try:
        mensaje.send()
    except (smtplib.SMTPException, OSError):
        logger.exception("No se pudo enviar el correo de alertas al usuario %s.", usuario.pk)
        return False
    return True


def sincronizar_alertas(usuario, notificar=True):
    """Crea las alertas pendientes y elimina las que ya no aplican.

    Si `notificar` es True y el usuario prefiere el canal "correo", envía un
    correo con las alertas recién creadas.

    Devuelve un diccionario con la cantidad de alertas creadas y eliminadas.
    """
    actuales = {}
    for medicamento in Medicamento.objects.filter(usuario=usuario, activo=True):
        tipo = tipo_de_alerta(medicamento)
        if tipo:
            actuales[medicamento.pk] = (tipo, medicamento)

    existentes = list(
        Alerta.objects.filter(usuario=usuario, medicamento__isnull=False)
    )
    vigentes = set()
    eliminadas = 0
    for alerta in existentes:
        actual = actuales.get(alerta.medicamento_id)
        if actual is None or actual[0] != alerta.tipo:
            alerta.delete()
            eliminadas += 1
        else:
            vigentes.add(alerta.medicamento_id)

    nuevas = []
    for medicamento_id, (tipo, medicamento) in actuales.items():
        if medicamento_id in vigentes:
            continue
        titulo, mensaje = _textos(medicamento, tipo)
        nuevas.append(
            Alerta.objects.create(
                usuario=usuario,
                medicamento=medicamento,
                tipo=tipo,
                titulo=titulo[:120],
                mensaje=mensaje[:255],
            )
        )

    if notificar and nuevas and usuario.canal_alertas == "correo":
        enviar_alertas_por_correo(usuario, nuevas)

    return {"creadas": len(nuevas), "eliminadas": eliminadas}
