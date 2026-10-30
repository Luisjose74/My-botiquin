"""Vistas del inventario de medicamentos (CRUD completo)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MedicamentoForm
from .models import Categoria, Medicamento

ESTADOS_VALIDOS = {"todos", "optimos", "por_vencer", "vencidos", "agotados"}

ESTADOS_LABELS = {
    "todos": "Todos",
    "optimos": "Óptimos",
    "por_vencer": "Por vencer",
    "vencidos": "Vencidos",
    "agotados": "Agotados",
}


@login_required
def lista(request):
    """Listado con estadísticas, búsqueda, filtros por estado y categoría."""
    base = Medicamento.objects.filter(usuario=request.user, activo=True)
    stats = {
        "total": base.count(),
        "optimos": base.vigentes().count(),
        "por_vencer": base.por_vencer().count(),
        "vencidos": base.vencidos().count(),
        "agotados": base.agotados().count(),
    }

    medicamentos = base.select_related("categoria", "miembro")

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
    medicamento = get_object_or_404(
        Medicamento.objects.select_related("categoria", "miembro"),
        pk=pk,
        usuario=request.user,
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
    medicamento = get_object_or_404(
        Medicamento, pk=pk, usuario=request.user
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
    medicamento = get_object_or_404(
        Medicamento, pk=pk, usuario=request.user
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
