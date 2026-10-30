"""Sincronización de alertas con el estado real del inventario.

Cada medicamento tiene como máximo una alerta activa, cuyo tipo corresponde a
su estado actual (agotado, vencido o próximo a vencer). Las alertas se crean,
reemplazan o eliminan según cambie ese estado, así que nunca quedan datos viejos.
"""
from .models import Alerta, EstadoInventario, Medicamento

ESTADO_A_TIPO = {
    EstadoInventario.AGOTADO: "agotado",
    EstadoInventario.VENCIDO: "vencido",
    EstadoInventario.PROXIMO: "por_vencer",
}


def tipo_de_alerta(medicamento):
    """Tipo de alerta que corresponde al estado actual, o None si no aplica."""
    return ESTADO_A_TIPO.get(medicamento.estado)


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
    return (
        f"{medicamento.nombre}: próximo a vencer",
        f"Vence el {fecha}, en {medicamento.dias_para_vencer} días.",
    )


def sincronizar_alertas(usuario):
    """Crea las alertas pendientes y elimina las que ya no aplican.

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

    creadas = 0
    for medicamento_id, (tipo, medicamento) in actuales.items():
        if medicamento_id in vigentes:
            continue
        titulo, mensaje = _textos(medicamento, tipo)
        Alerta.objects.create(
            usuario=usuario,
            medicamento=medicamento,
            tipo=tipo,
            titulo=titulo[:120],
            mensaje=mensaje[:255],
        )
        creadas += 1

    return {"creadas": creadas, "eliminadas": eliminadas}
