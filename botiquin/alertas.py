"""Sincronización de alertas con el estado real del inventario.

Cada medicamento tiene como máximo una alerta activa, cuyo tipo corresponde a
su estado actual. Prioridad: agotado > vencido > próximo a vencer > stock bajo.

Los avisos de vencimiento se escalonan en tres hitos independientes (30, 15 y
5 días antes de la fecha de caducidad). Cuando el medicamento entra en una
ventana más próxima, el hito anterior queda archivado (sigue en el historial
como "leída") y se crea la alerta del nuevo hito. El aviso de "vencido" es
permanente: permanece en el panel hasta que el usuario disponga del
medicamento.

Las alertas nuevas se avisan en la app siempre y, además, por correo cuando el
usuario tiene como canal preferido "correo".
"""
import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Alerta, EstadoInventario, Medicamento

logger = logging.getLogger(__name__)

ESTADO_A_TIPO = {
    EstadoInventario.AGOTADO: "agotado",
    EstadoInventario.VENCIDO: "vencido",
}

#: Tipos de alerta que corresponden a un hito de vencimiento.
TIPOS_HITO = tuple(f"por_vencer_{hito}" for hito in Medicamento.HITOS_VENCIMIENTO)

#: Tipo heredado (un solo aviso a 30 días) que se reemplaza por los hitos.
TIPO_HEREDADO = "por_vencer"


def hito_por_vencer(dias):
    """Hito de aviso que corresponde a los días que faltan para vencer.

    Ventanas: 0-5 días -> hito 5; 6-15 días -> hito 15; 16-30 días -> hito 30.
    Devuelve None si el medicamento no está en ventana de aviso.
    """
    if dias is None or dias < 0:
        return None
    if dias <= 5:
        return 5
    if dias <= 15:
        return 15
    if dias <= 30:
        return 30
    return None


def tipo_de_alerta(medicamento):
    """Tipo de alerta que corresponde al estado actual, o None si no aplica."""
    if medicamento.cantidad <= 0:
        return ESTADO_A_TIPO[EstadoInventario.AGOTADO]
    dias = medicamento.dias_para_vencer
    if dias is not None and dias < 0:
        return ESTADO_A_TIPO[EstadoInventario.VENCIDO]
    hito = hito_por_vencer(dias)
    if hito:
        return f"por_vencer_{hito}"
    if medicamento.stock_bajo:
        return "stock_bajo"
    return None


def _textos(medicamento, tipo):
    """Título y mensaje de la alerta según su tipo."""
    fecha = medicamento.fecha_vencimiento_formateada
    dias = medicamento.dias_para_vencer
    nombre = medicamento.nombre_completo
    if tipo == "agotado":
        return (
            f"{nombre}: sin existencias",
            "No quedan unidades en tu botiquín. Considera reabastecerlo.",
        )
    if tipo == "vencido":
        return (
            f"{nombre}: vencido",
            f"Venció el {fecha}. No lo consumas y deséchalo de forma segura.",
        )
    if tipo == "stock_bajo":
        return (
            f"{nombre}: stock bajo",
            f"Quedan {medicamento.cantidad} unidad"
            f"{'es' if medicamento.cantidad != 1 else ''}. "
            "Considera reabastecerlo pronto.",
        )
    if tipo == "por_vencer_30":
        return (
            f"{nombre}: vence en 30 días",
            f"Vence el {fecha}, en {dias} días. Revisa si todavía lo necesitas.",
        )
    if tipo == "por_vencer_15":
        return (
            f"{nombre}: vence en 15 días",
            f"Vence el {fecha}, en {dias} días. Úsalo si está indicado y "
            "evita iniciar tratamientos nuevos con este lote.",
        )
    if tipo == "por_vencer_5":
        return (
            f"{nombre}: vence en 5 días",
            f"Vence el {fecha}, en {dias} días. Últimos días: úsalo si corresponde "
            "y retíralo del botiquín al vencerse.",
        )
    return (
        f"{nombre}: próximo a vencer",
        f"Vence el {fecha}, en {dias} días.",
    )


def _url_panel_alertas():
    base = getattr(settings, "SITE_URL", "").rstrip("/")
    return f"{base}{reverse('botiquin:alertas')}" if base else ""


def _url_puntos_azules():
    """URL absoluta del directorio de Puntos Azules (sección del directorio)."""
    from .notificaciones import url_base_sitio

    ruta = f"{reverse('publico:puntos_azules')}#directorio"
    base = getattr(settings, "SITE_URL", "").strip().rstrip("/")
    if not base:
        base = url_base_sitio()
    return f"{base}{ruta}"


def _usuario_notificacion(medicamento):
    """Devuelve el usuario que debe recibir la notificación de una alerta.

    Si el medicamento tiene un miembro asignado con usuario, se notifica a ese
    usuario. De lo contrario, se notifica al propietario del medicamento.
    """
    miembro = getattr(medicamento, "miembro", None)
    if miembro and miembro.usuario_id:
        return miembro.usuario
    return medicamento.usuario


def _asunto_alertas(alertas):
    """Asunto del correo según el tipo de aviso (hito de vencimiento)."""
    tipos = {alerta.tipo for alerta in alertas}
    if len(tipos) == 1:
        unico = tipos.pop()
        if unico == "vencido":
            return "Mi Botiquín: tienes un medicamento vencido"
        if unico in TIPOS_HITO:
            hito = unico.rsplit("_", 1)[-1]
            return f"Mi Botiquín: tu medicamento vence en {hito} días"
    total = len(alertas)
    return (
        f"Mi Botiquín: {total} alerta nueva"
        if total == 1
        else f"Mi Botiquín: {total} alertas nuevas"
    )


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
        # Enlace al directorio de Puntos Azules para el desecho seguro.
        "url_puntos_azules": _url_puntos_azules(),
        "hay_vencidos": any(alerta.tipo == "vencido" for alerta in alertas),
    }
    asunto = _asunto_alertas(alertas)
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
    """Crea las alertas pendientes y archiva las que ya no aplican.

    Procesa medicamentos del hogar del usuario: tanto los registrados por él
    como los asignados a él como miembro (miembro__usuario=usuario).

    - Se crea una alerta nueva por medicamento según su estado actual.
    - Cuando un medicamento pasa de un hito de vencimiento (30, 15, 5) a otro
      más próximo, la alerta del hito anterior queda archivada.
    - El aviso de "vencido" es permanente: se mantiene activo mientras el
      medicamento siga vencido en el inventario.

    Si `notificar` es True y el usuario prefiere el canal "correo", envía un
    correo con las alertas recién creadas (controlando duplicados vía
    Alerta.notificada).

    Devuelve un diccionario con la cantidad de alertas creadas, archivadas y
    eliminadas.
    """
    # Medicamentos del usuario: propios o asignados como miembro en su hogar
    medicamentos_qs = Medicamento.objects.filter(activo=True).filter(
        models.Q(usuario=usuario) | models.Q(miembro__usuario=usuario)
    ).distinct()

    actuales = {}
    for medicamento in medicamentos_qs:
        tipo = tipo_de_alerta(medicamento)
        if tipo:
            actuales[medicamento.pk] = (tipo, medicamento)

    existentes = list(
        Alerta.objects.filter(usuario=usuario, medicamento__isnull=False)
    )
    por_medicamento = {}
    for alerta in existentes:
        por_medicamento.setdefault(alerta.medicamento_id, []).append(alerta)

    nuevas = []
    archivadas = 0
    eliminadas = 0
    reactivadas = 0

    # Se revisan los medicamentos con alerta actual y también los que ya la
    # tenían (por ejemplo, si el usuario corrigió la fecha de vencimiento).
    for medicamento_id in set(actuales) | set(por_medicamento):
        tipo_actual, medicamento = actuales.get(medicamento_id, (None, None))
        vigente = None
        for alerta in por_medicamento.get(medicamento_id, []):
            if tipo_actual and alerta.tipo == tipo_actual and vigente is None:
                vigente = alerta
                # La alerta del hito vuelve a estar vigente (p. ej. el usuario
                # corrigió la fecha de vencimiento): se reactiva.
                if alerta.archivada:
                    alerta.archivada = False
                    alerta.leida = False
                    alerta.save(update_fields=["archivada", "leida"])
                    reactivadas += 1
                continue

            # La alerta ya no corresponde al estado actual.
            if alerta.tipo == TIPO_HEREDADO:
                # Aviso único de 30 días (versión anterior): se elimina.
                alerta.delete()
                eliminadas += 1
            elif not alerta.archivada:
                # Hito superado (30 -> 15 -> 5) o alerta ya resuelta:
                # se archiva, de modo que el panel muestre solo lo vigente.
                alerta.archivada = True
                alerta.leida = True
                alerta.save(update_fields=["archivada", "leida"])
                archivadas += 1

        if vigente is None and tipo_actual:
            titulo, mensaje = _textos(medicamento, tipo_actual)
            nuevas.append(
                Alerta.objects.create(
                    usuario=usuario,
                    medicamento=medicamento,
                    tipo=tipo_actual,
                    titulo=titulo[:120],
                    mensaje=mensaje[:255],
                )
            )

    if notificar and nuevas and usuario.canal_alertas == "correo":
        # Filtrar solo las que aún no han sido notificadas (evitar duplicados)
        por_notificar = [a for a in nuevas if not a.notificada]
        if por_notificar:
            if enviar_alertas_por_correo(usuario, por_notificar):
                # Marcar como notificadas para evitar reenvíos
                Alerta.objects.filter(pk__in=[a.pk for a in por_notificar]).update(
                    notificada=True
                )

    return {
        "creadas": len(nuevas),
        "archivadas": archivadas,
        "eliminadas": eliminadas,
        "reactivadas": reactivadas,
    }
