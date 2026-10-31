"""Vistas del inventario de medicamentos, panel de alertas y CRUD."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from cuentas.models import MiembroHogar

from .alertas import sincronizar_alertas
from .forms import MedicamentoForm
from .models import Alerta, Categoria, Medicamento

ESTADOS_VALIDOS = {"todos", "optimos", "por_vencer", "vencidos", "agotados"}

ESTADOS_LABELS = {
    "todos": "Todos",
    "optimos": "Óptimos",
    "por_vencer": "Por vencer",
    "vencidos": "Vencidos",
    "agotados": "Agotados",
}


def _estadisticas(base):
    return {
        "total": base.count(),
        "optimos": base.vigentes().count(),
        "por_vencer": base.por_vencer().count(),
        "vencidos": base.vencidos().count(),
        "agotados": base.agotados().count(),
    }


def _redirigir_seguro(request, por_defecto):
    """Vuelve a la página de origen solo si es una ruta interna."""
    destino = request.POST.get("next", "")
    if destino and url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(destino)
    return redirect(por_defecto)


@login_required
def inicio(request):
    """Panel principal: resumen del botiquín y alertas que requieren atención."""
    sincronizar_alertas(request.user)

    base = Medicamento.objects.filter(usuario=request.user, activo=True)
    alertas_pendientes = Alerta.objects.filter(
        usuario=request.user, leida=False
    ).select_related("medicamento__miembro")

    atencion_por_miembro = {
        fila["miembro"]: fila["total"]
        for fila in base.en_alerta()
        .filter(miembro__isnull=False)
        .values("miembro")
        .annotate(total=Count("pk"))
    }
    integrantes = [
        {"miembro": miembro, "atencion": atencion_por_miembro.get(miembro.pk, 0)}
        for miembro in request.user.hogar.miembros.all()
    ] if request.user.hogar is not None else []

    return render(
        request,
        "botiquin/inicio.html",
        {
            "stats": _estadisticas(base),
            "alertas": alertas_pendientes[:5],
            "total_alertas": alertas_pendientes.count(),
            "atencion": base.en_alerta()
            .select_related("categoria", "miembro")
            .order_by("fecha_vencimiento", "nombre")[:6],
            "integrantes": integrantes,
        },
    )


@login_required
def alertas(request):
    """Listado de alertas con filtro de pendientes o todas."""
    sincronizar_alertas(request.user)

    ver = request.GET.get("ver", "pendientes")
    if ver not in {"pendientes", "todas"}:
        ver = "pendientes"

    consulta = Alerta.objects.filter(usuario=request.user).select_related(
        "medicamento__miembro"
    )
    if ver == "pendientes":
        consulta = consulta.filter(leida=False)

    return render(
        request,
        "botiquin/alertas.html",
        {
            "alertas": consulta,
            "ver_actual": ver,
            "total_pendientes": Alerta.objects.filter(
                usuario=request.user, leida=False
            ).count(),
        },
    )


@login_required
@require_POST
def marcar_alerta_leida(request, pk):
    alerta = get_object_or_404(Alerta, pk=pk, usuario=request.user)
    alerta.leida = True
    alerta.save(update_fields=["leida"])
    return _redirigir_seguro(request, "botiquin:alertas")


@login_required
@require_POST
def marcar_todas_leidas(request):
    Alerta.objects.filter(usuario=request.user, leida=False).update(leida=True)
    messages.success(request, "Todas las alertas se marcaron como leídas.")
    return _redirigir_seguro(request, "botiquin:alertas")


@login_required
def lista(request):
    """Listado con estadísticas, búsqueda, filtros por estado y categoría."""
    base = Medicamento.objects.filter(usuario=request.user, activo=True)
    stats = _estadisticas(base)

    medicamentos = base.select_related("categoria", "miembro")

    miembros = (
        request.user.hogar.miembros.all()
        if request.user.hogar is not None
        else MiembroHogar.objects.none()
    )
    miembro_actual = None
    miembro_id = request.GET.get("miembro", "").strip()
    if miembro_id.isdigit():
        miembro_actual = miembros.filter(pk=int(miembro_id)).first()
        if miembro_actual:
            medicamentos = medicamentos.filter(miembro=miembro_actual)

    estado = request.GET.get("estado", "todos")
    if estado not in ESTADOS_VALIDOS:
        estado = "todos"

    if estado == "optimos":
        medicamentos = medicamentos.vigentes()
    elif estado == "por_vencer":
        medicamentos = medicamentos.por_vencer()
    elif estado == "vencidos":
        medicamentos = medicamentos.vencidos()
    elif estado == "agotados":
        medicamentos = medicamentos.agotados()

    categorias = Categoria.objects.all()
    categoria_actual = None
    categoria_id = request.GET.get("categoria", "").strip()
    if categoria_id.isdigit():
        categoria_actual = categorias.filter(pk=int(categoria_id)).first()
        if categoria_actual:
            medicamentos = medicamentos.filter(categoria=categoria_actual)

    q = request.GET.get("q", "").strip()
    if q:
        medicamentos = medicamentos.filter(
            Q(nombre__icontains=q)
            | Q(lote__icontains=q)
            | Q(registro_sanitario__icontains=q)
        )

    medicamentos = medicamentos.order_by("fecha_vencimiento", "nombre")

    return render(
        request,
        "botiquin/lista.html",
        {
            "medicamentos": medicamentos,
            "categorias": categorias,
            "miembros": miembros,
            "miembro_actual": miembro_actual.pk if miembro_actual else "",
            "stats": stats,
            "estado_actual": estado,
            "estado_label": ESTADOS_LABELS[estado],
            "categoria_actual": categoria_actual.pk if categoria_actual else "",
            "q": q,
        },
    )


@login_required
def detalle(request, pk):
    """Ficha completa de un medicamento."""
    medicamento = Medicamento.objects.select_related("categoria", "miembro").filter(pk=pk).first()
    if medicamento is None:
        raise Http404
    if medicamento.usuario_id != request.user.id:
        raise PermissionDenied(
            "No tienes permiso para ver este medicamento."
        )
    return render(
        request, "botiquin/detalle.html", {"medicamento": medicamento}
    )


@login_required
def crear(request):
    """Registro de una nueva caja de medicamento."""
    if request.method == "POST":
        form = MedicamentoForm(
            request.POST, request.FILES, usuario=request.user
        )
        if form.is_valid():
            medicamento = form.save(commit=False)
            medicamento.usuario = request.user
            medicamento.save()
            messages.success(
                request,
                f"«{medicamento.nombre}» se registró en tu botiquín.",
            )
            return redirect("botiquin:detalle", pk=medicamento.pk)
    else:
        form = MedicamentoForm(usuario=request.user)

    return render(
        request,
        "botiquin/formulario.html",
        {"form": form, "modo": "crear", "medicamento": None},
    )


@login_required
def editar(request, pk):
    """Edición de un medicamento existente."""
    medicamento = Medicamento.objects.filter(pk=pk).first()
    if medicamento is None:
        raise Http404
    if medicamento.usuario_id != request.user.id:
        raise PermissionDenied(
            "No tienes permiso para editar este medicamento."
        )

    if request.method == "POST":
        form = MedicamentoForm(
            request.POST,
            request.FILES,
            instance=medicamento,
            usuario=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(
                request, "Los datos del medicamento se actualizaron."
            )
            return redirect("botiquin:detalle", pk=medicamento.pk)
    else:
        form = MedicamentoForm(instance=medicamento, usuario=request.user)

    return render(
        request,
        "botiquin/formulario.html",
        {"form": form, "modo": "editar", "medicamento": medicamento},
    )


@login_required
def eliminar(request, pk):
    """Confirmación (GET) y eliminación definitiva (POST)."""
    medicamento = Medicamento.objects.filter(pk=pk).first()
    if medicamento is None:
        raise Http404
    if medicamento.usuario_id != request.user.id:
        raise PermissionDenied(
            "No tienes permiso para eliminar este medicamento."
        )

    if request.method == "POST":
        nombre = medicamento.nombre
        medicamento.delete()
        messages.success(request, f"«{nombre}» se eliminó del botiquín.")
        return redirect("botiquin:lista")

    return render(
        request,
        "botiquin/eliminar.html",
        {"medicamento": medicamento},
    )
