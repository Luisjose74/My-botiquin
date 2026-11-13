"""Vistas del inventario de medicamentos, panel de alertas y CRUD."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from cuentas.models import MiembroHogar

from .alertas import sincronizar_alertas
from .forms import MedicamentoForm, PautaTomaForm
from cuentas.models import MiembroHogar
from .models import (
    Alerta,
    Categoria,
    Clasificacion,
    Medicamento,
    PautaToma,
    TomaRegistrada,
)
from .notificaciones import (
    notificar_asignacion,
    notificar_medicamento_asignado,
    verificar_token_confirmacion,
)


def _mismo_hogar(request, medicamento):
    """True si el medicamento pertenece al hogar del usuario."""
    if request.user.hogar is None:
        return medicamento.usuario_id == request.user.id
    return medicamento.usuario is not None and medicamento.usuario.hogar_id == request.user.hogar_id


def _es_admin_hogar(request):
    if request.user.hogar is None:
        return False
    return MiembroHogar.objects.filter(
        usuario=request.user, hogar=request.user.hogar, es_principal=True
    ).exists()

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

    if request.user.hogar is not None:
        base = Medicamento.objects.filter(usuario__hogar=request.user.hogar, activo=True)
    else:
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

    administrador = (
        request.user.hogar.miembros.filter(es_principal=True).first()
        if request.user.hogar is not None
        else None
    )

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
            "administrador": administrador,
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
    if request.user.hogar is not None:
        base = Medicamento.objects.filter(usuario__hogar=request.user.hogar, activo=True)
    else:
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

    clasificaciones = Clasificacion.objects.all()
    clasificacion_actual = None
    clasificacion_id = request.GET.get("clasificacion", "").strip()
    if clasificacion_id.isdigit():
        clasificacion_actual = clasificaciones.filter(pk=int(clasificacion_id)).first()
        if clasificacion_actual:
            medicamentos = medicamentos.filter(clasificacion=clasificacion_actual)

    q = request.GET.get("q", "").strip()
    if q:
        medicamentos = medicamentos.filter(
            Q(nombre__icontains=q)
            | Q(concentracion__icontains=q)
            | Q(lote__icontains=q)
            | Q(registro_sanitario__icontains=q)
        )

    medicamentos = medicamentos.order_by("fecha_vencimiento", "nombre")

    # Filtros que se mantienen al cambiar de estado (para los chips).
    filtros_activos = {}
    if categoria_actual:
        filtros_activos["categoria"] = categoria_actual.pk
    if clasificacion_actual:
        filtros_activos["clasificacion"] = clasificacion_actual.pk
    if miembro_actual:
        filtros_activos["miembro"] = miembro_actual.pk
    if q:
        filtros_activos["q"] = q
    filtros_base = urlencode(filtros_activos)

    return render(
        request,
        "botiquin/lista.html",
        {
            "medicamentos": medicamentos,
            "categorias": categorias,
            "clasificaciones": clasificaciones,
            "miembros": miembros,
            "miembro_actual": miembro_actual.pk if miembro_actual else "",
            "stats": stats,
            "estado_actual": estado,
            "estado_label": ESTADOS_LABELS[estado],
            "categoria_actual": categoria_actual.pk if categoria_actual else "",
            "clasificacion_actual": (
                clasificacion_actual.pk if clasificacion_actual else ""
            ),
            "filtros_base": filtros_base,
            "q": q,
        },
    )


@login_required
def detalle(request, pk):
    """Ficha completa de un medicamento."""
    medicamento = Medicamento.objects.select_related("categoria", "miembro").filter(pk=pk).first()
    if medicamento is None:
        raise Http404
    if not _mismo_hogar(request, medicamento):
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
            if medicamento.miembro is not None:
                try:
                    notificar_medicamento_asignado(medicamento, medicamento.miembro)
                except Exception:  # noqa: BLE001
                    pass
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
        {
            "form": form,
            "modo": "crear",
            "medicamento": None,
            "clasificaciones": Clasificacion.objects.all(),
        },
    )


@login_required
def editar(request, pk):
    """Edición de un medicamento existente."""
    medicamento = Medicamento.objects.filter(pk=pk).first()
    if medicamento is None:
        raise Http404
    if not (_mismo_hogar(request, medicamento) and (
        medicamento.usuario_id == request.user.id or _es_admin_hogar(request)
    )):
        raise PermissionDenied(
            "No tienes permiso para editar este medicamento."
        )

    if request.method == "POST":
        miembro_anterior = medicamento.miembro
        form = MedicamentoForm(
            request.POST,
            request.FILES,
            instance=medicamento,
            usuario=request.user,
        )
        if form.is_valid():
            form.save()
            medicamento.refresh_from_db()
            if (
                medicamento.miembro is not None
                and medicamento.miembro_id != (miembro_anterior.pk if miembro_anterior else None)
            ):
                try:
                    notificar_medicamento_asignado(medicamento, medicamento.miembro)
                except Exception:  # noqa: BLE001
                    pass
            messages.success(
                request, "Los datos del medicamento se actualizaron."
            )
            return redirect("botiquin:detalle", pk=medicamento.pk)
    else:
        form = MedicamentoForm(instance=medicamento, usuario=request.user)

    return render(
        request,
        "botiquin/formulario.html",
        {
            "form": form,
            "modo": "editar",
            "medicamento": medicamento,
            "clasificaciones": Clasificacion.objects.all(),
        },
    )


@login_required
def eliminar(request, pk):
    """Confirmación (GET) y eliminación definitiva (POST)."""
    medicamento = Medicamento.objects.filter(pk=pk).first()
    if medicamento is None:
        raise Http404
    if not (_mismo_hogar(request, medicamento) and (
        medicamento.usuario_id == request.user.id or _es_admin_hogar(request)
    )):
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


@login_required
def pautas_lista(request):
    """Listado de pautas de toma del hogar del usuario."""
    if request.user.hogar is None:
        pautas = PautaToma.objects.none()
    else:
        if request.user.hogar is not None:
            pautas = (
                PautaToma.objects.filter(medicamento__usuario__hogar=request.user.hogar)
                .select_related("medicamento", "miembro")
                .order_by("-creado")
            )
        else:
            pautas = (
                PautaToma.objects.filter(medicamento__usuario=request.user)
                .select_related("medicamento", "miembro")
                .order_by("-creado")
            )
    return render(request, "botiquin/pautas_lista.html", {"pautas": pautas})


@login_required
def pauta_crear(request):
    """Crear una nueva pauta de toma."""
    if request.method == "POST":
        form = PautaTomaForm(request.POST, usuario=request.user)
        if form.is_valid():
            pauta = form.save(commit=False)
            pauta.creado_por = request.user
            pauta.save()
            try:
                notificar_asignacion(pauta)
            except Exception:  # noqa: BLE001
                pass
            messages.success(
                request,
                f"Pauta creada: {pauta.medicamento.nombre} para {pauta.miembro.nombre}.",
            )
            return redirect("botiquin:pautas_lista")
    else:
        form = PautaTomaForm(usuario=request.user)
        med_id = request.GET.get("medicamento")
        if med_id and med_id.isdigit():
            form.initial["medicamento"] = int(med_id)

    return render(
        request, "botiquin/pauta_form.html", {"form": form, "modo": "crear"}
    )


@login_required
def pauta_editar(request, pk):
    pauta = get_object_or_404(PautaToma, pk=pk)
    if not (_mismo_hogar(request, pauta.medicamento) and (
        pauta.medicamento.usuario_id == request.user.id or _es_admin_hogar(request)
    )):
        raise PermissionDenied("No tienes permiso para editar esta pauta.")

    if request.method == "POST":
        form = PautaTomaForm(request.POST, instance=pauta, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "La pauta se actualizó.")
            return redirect("botiquin:pautas_lista")
    else:
        form = PautaTomaForm(instance=pauta, usuario=request.user)

    return render(
        request,
        "botiquin/pauta_form.html",
        {"form": form, "modo": "editar", "pauta": pauta},
    )


@login_required
def pauta_eliminar(request, pk):
    pauta = get_object_or_404(PautaToma, pk=pk)
    if not (_mismo_hogar(request, pauta.medicamento) and (
        pauta.medicamento.usuario_id == request.user.id or _es_admin_hogar(request)
    )):
        raise PermissionDenied("No tienes permiso para eliminar esta pauta.")

    if request.method == "POST":
        nombre = str(pauta)
        pauta.delete()
        messages.success(request, f"«{nombre}» se eliminó.")
        return redirect("botiquin:pautas_lista")

    return render(
        request, "botiquin/pauta_eliminar.html", {"pauta": pauta}
    )


@login_required
def tomas_hoy(request):
    """Listado de tomas del día para el hogar del usuario, con confirmación."""
    from django.utils import timezone as _tz

    hoy = _tz.localdate()

    if request.user.hogar is None:
        pautas_hoy = []
    else:
        if request.user.hogar is not None:
            qs = PautaToma.objects.filter(medicamento__usuario__hogar=request.user.hogar, activa=True)
        else:
            qs = PautaToma.objects.filter(medicamento__usuario=request.user, activa=True)
        pautas_hoy = [
            p
            for p in qs.select_related("medicamento", "miembro")
            if p._corresponde(hoy)
        ]

    # Mapa pauta_id -> TomaRegistrada (si existe)
    tomas = {
        t.pauta_id: t
        for t in TomaRegistrada.objects.filter(
            pauta__in=[p.pk for p in pautas_hoy], fecha=hoy
        )
    }

    items = []
    for pauta in pautas_hoy:
        toma = tomas.get(pauta.pk)
        items.append({"pauta": pauta, "toma": toma, "tomada": bool(toma and toma.tomada)})

    return render(
        request, "botiquin/tomas_hoy.html", {"items": items, "hoy": hoy}
    )


@login_required
@require_POST
def marcar_tomada(request, pk):
    """Marca (o desmarca) la toma de una pauta para hoy."""
    pauta = get_object_or_404(PautaToma, pk=pk)
    if not _mismo_hogar(request, pauta.medicamento):
        raise PermissionDenied("No tienes permiso para esta pauta.")

    from django.utils import timezone as _tz

    hoy = _tz.localdate()
    toma, _ = TomaRegistrada.objects.get_or_create(
        pauta=pauta, fecha=hoy, defaults={"registrado_por": request.user}
    )
    toma.tomada = not toma.tomada
    toma.registrado_por = request.user
    toma.save(update_fields=["tomada", "registrado_por"])

    estado = "tomada" if toma.tomada else "pendiente"
    messages.success(request, f"{pauta.medicamento.nombre}: marcada como {estado}.")
    return redirect("botiquin:tomas_hoy")


from datetime import date as _date
from django.core import signing as _signing


@require_GET
def confirmar_toma(request, token):
    """Confirma la toma de una pauta a partir de un token seguro (email/WhatsApp).

    Accesible sin iniciar sesión: el token contiene la pauta y la fecha,
    y es firmado criptográficamente para evitar suplantación.
    """
    try:
        pauta_id, fecha_str = verificar_token_confirmacion(token)
        fecha = _date.fromisoformat(fecha_str)
    except Exception:  # noqa: BLE001
        return render(
            request,
            "botiquin/token_invalido.html",
            status=400,
        )

    pauta = get_object_or_404(PautaToma, pk=pauta_id)
    toma, _ = TomaRegistrada.objects.get_or_create(
        pauta=pauta,
        fecha=fecha,
        defaults={"tomada": False, "notificada": False, "registrado_por": None},
    )
    toma.tomada = True
    toma.save(update_fields=["tomada"])

    messages.success(
        request, f"¡Listo! Se registró la toma de {pauta.medicamento.nombre}."
    )
    return render(
        request,
        "botiquin/tomas_confirmacion.html",
        {"pauta": pauta, "fecha": fecha},
    )
