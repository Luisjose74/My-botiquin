"""Modelos del inventario del botiquín: categorías, medicamentos,
fechas de caducidad, estados de inventario y alertas."""
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


# --------------------------------------------------------------------------
# Estados de inventario (misma lógica que est() del HTML guía)
# --------------------------------------------------------------------------
class EstadoInventario(models.TextChoices):
    VIGENTE = "vigente", "Vigente"                 # más de 30 días
    PROXIMO = "proximo", "Próximo a vencer"        # 0 a 30 días
    VENCIDO = "vencido", "Vencido"                 # fecha pasada
    AGOTADO = "agotado", "Sin existencias"         # cantidad = 0


class Presentacion(models.TextChoices):
    TABLETA = "tableta", "Tabletas"
    CAPSULA = "capsula", "Cápsulas"
    SUSPENSION = "suspension", "Suspensión"
    CREMA = "crema", "Crema / ungüento"
    GOTA = "gota", "Gotas"
    AEROSOL = "aerosol", "Aerosol"
    INYECTABLE = "inyectable", "Inyectable"
    OTRO = "otro", "Otro"


class CondicionAlmacenamiento(models.TextChoices):
    SECO = "seco", "Lugar fresco y seco"
    REFRIGERADO = "refrigerado", "Refrigerado (2 °C - 8 °C)"
    PROTEGIDO_LUZ = "luz", "Protegido de la luz"
    TEMPERATURA_AMBIENTE = "ambiente", "Temperatura ambiente"
    FUERA_ALCANCE = "ninos", "Fuera del alcance de los niños"


# --------------------------------------------------------------------------
# Categorías (el estudio pide "organizar los medicamentos por categorías")
# --------------------------------------------------------------------------
class Categoria(models.Model):
    nombre = models.CharField("Nombre", max_length=60, unique=True)
    icono = models.CharField("Icono", max_length=10, default="💊")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# --------------------------------------------------------------------------
# QuerySet con las consultas de negocio (filtros del dashboard)
# --------------------------------------------------------------------------
class MedicamentoQuerySet(models.QuerySet):
    def vigentes(self):
        limite = timezone.localdate() + timedelta(days=self.model.UMBRAL_ALERTA_DIAS)
        return self.filter(fecha_vencimiento__gt=limite, cantidad__gt=0)

    def por_vencer(self, dias=None):
        dias = self.model.UMBRAL_ALERTA_DIAS if dias is None else dias
        hoy = timezone.localdate()
        return self.filter(
            fecha_vencimiento__lte=hoy + timedelta(days=dias),
            fecha_vencimiento__gte=hoy,
            cantidad__gt=0,
        )

    def vencidos(self):
        return self.filter(
            fecha_vencimiento__lt=timezone.localdate(), cantidad__gt=0
        )

    def agotados(self):
        return self.filter(cantidad=0)

    def en_alerta(self):
        """Medicamentos que deben aparecer en el panel de alertas."""
        hoy = timezone.localdate()
        return self.filter(
            models.Q(fecha_vencimiento__lt=hoy)            # vencidos
            | models.Q(
                fecha_vencimiento__lte=hoy
                + timedelta(days=self.model.UMBRAL_ALERTA_DIAS)
            )
            | models.Q(cantidad__lte=self.model.UMBRAL_STOCK_BAJO)
        )


# --------------------------------------------------------------------------
# Medicamento (registro de caja: datos básicos + foto opcional)
# --------------------------------------------------------------------------
class Medicamento(models.Model):
    UMBRAL_ALERTA_DIAS = 30  # días previos al vencimiento para alertar
    UMBRAL_STOCK_BAJO = 2  # unidades o menos (y mayores que cero) = stock bajo

    # Quién registra y quién lo usa
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Registrado por",
        on_delete=models.CASCADE,
        related_name="medicamentos",
    )
    miembro = models.ForeignKey(
        "cuentas.MiembroHogar",
        verbose_name="Quién lo usa",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medicamentos",
    )
    categoria = models.ForeignKey(
        Categoria,
        verbose_name="Categoría",
        on_delete=models.PROTECT,
        related_name="medicamentos",
        null=True,
        blank=True,
    )

    # Datos de la caja
    nombre = models.CharField("Nombre del medicamento", max_length=120)
    presentacion = models.CharField(
        "Presentación",
        max_length=20,
        choices=Presentacion.choices,
        default=Presentacion.TABLETA,
    )
    cantidad = models.PositiveIntegerField(
        "Cantidad disponible",
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Unidades o cajas disponibles en el botiquín.",
    )
    lote = models.CharField("Número de lote", max_length=40, blank=True)
    registro_sanitario = models.CharField(
        "Registro sanitario (INVIMA)",
        max_length=60,
        blank=True,
        help_text="Déjalo vacío si no lo tienes a la mano.",
    )

    # Fechas de caducidad
    fecha_vencimiento = models.DateField("Fecha de vencimiento")
    fecha_registro = models.DateTimeField("Registrado el", auto_now_add=True)
    fecha_actualizacion = models.DateTimeField("Actualizado el", auto_now=True)

    # Conservación
    condicion_almacenamiento = models.CharField(
        "Condición de almacenamiento",
        max_length=20,
        choices=CondicionAlmacenamiento.choices,
        default=CondicionAlmacenamiento.SECO,
    )
    ubicacion = models.CharField(
        "Ubicación en el hogar",
        max_length=80,
        blank=True,
        help_text="Ej.: botiquín del baño, cajón de la cocina.",
    )
    notas_conservacion = models.TextField(
        "Notas de conservación",
        blank=True,
        help_text="Ej.: no refrigerar, mantener en su caja original.",
    )

    # Registro por foto (90% de los encuestados prefieren registrar por foto)
    foto = models.ImageField(
        "Foto de la caja", upload_to="medicamentos/", blank=True, null=True
    )
    notas = models.TextField("Notas adicionales", blank=True)
    activo = models.BooleanField("Activo en el botiquín", default=True)

    objects = MedicamentoQuerySet.as_manager()

    class Meta:
        verbose_name = "Medicamento"
        verbose_name_plural = "Medicamentos"
        ordering = ["nombre", "fecha_vencimiento"]
        indexes = [
            models.Index(fields=["fecha_vencimiento"]),
            models.Index(fields=["usuario", "activo"]),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.cantidad} und.)"

    # ------------------ Lógica de fechas y estados ------------------
    @property
    def dias_para_vencer(self):
        """Días restantes. Negativo = ya venció."""
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - timezone.localdate()).days

    @property
    def estado(self) -> str:
        """Estado calculado: no se almacena para evitar datos desfasados."""
        if self.cantidad <= 0:
            return EstadoInventario.AGOTADO
        dias = self.dias_para_vencer
        if dias is None:
            return EstadoInventario.VIGENTE
        if dias < 0:
            return EstadoInventario.VENCIDO
        if dias <= self.UMBRAL_ALERTA_DIAS:
            return EstadoInventario.PROXIMO
        return EstadoInventario.VIGENTE

    @property
    def estado_label(self) -> str:
        return EstadoInventario(self.estado).label

    @property
    def dias_vencido(self) -> int:
        """Días transcurridos desde el vencimiento (0 si aún no vence)."""
        dias = self.dias_para_vencer
        return abs(dias) if dias is not None and dias < 0 else 0

    @property
    def stock_bajo(self) -> bool:
        """Queda poco stock, pero todavía hay unidades."""
        return 0 < self.cantidad <= self.UMBRAL_STOCK_BAJO

    @property
    def esta_en_alerta(self) -> bool:
        return self.stock_bajo or self.estado in (
            EstadoInventario.PROXIMO,
            EstadoInventario.VENCIDO,
            EstadoInventario.AGOTADO,
        )

    @property
    def fecha_vencimiento_formateada(self):
        return self.fecha_vencimiento.strftime("%d/%m/%Y")

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.cantidad is not None and self.cantidad < 0:
            raise ValidationError(
                {"cantidad": "La cantidad no puede ser negativa."}
            )


# --------------------------------------------------------------------------
# Alertas de vencimiento (función más demandada en la encuesta: 67%)
# --------------------------------------------------------------------------
class Alerta(models.Model):
    TIPOS = [
        ("vencido", "Medicamento vencido"),
        ("por_vencer", "Próximo a vencer"),
        ("agotado", "Sin existencias"),
        ("stock_bajo", "Stock bajo"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Usuario",
        on_delete=models.CASCADE,
        related_name="alertas",
    )
    medicamento = models.ForeignKey(
        Medicamento,
        verbose_name="Medicamento",
        on_delete=models.CASCADE,
        related_name="alertas",
        null=True,
        blank=True,
    )
    tipo = models.CharField("Tipo", max_length=20, choices=TIPOS)
    titulo = models.CharField("Título", max_length=120)
    mensaje = models.CharField("Mensaje", max_length=255)
    leida = models.BooleanField("Leída", default=False)
    creada = models.DateTimeField("Creada el", auto_now_add=True)

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ["leida", "-creada"]
        indexes = [models.Index(fields=["usuario", "leida"])]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo}"


# --------------------------------------------------------------------------
# Pauta de toma: programación de administración de un medicamento a un miembro
# --------------------------------------------------------------------------
class PautaToma(models.Model):
    """Programación de tomas de un medicamento asignado a un integrante."""

    FRECUENCIAS = [
        ("diaria", "Diariamente"),
        ("cada_n_dias", "Cada N días"),
        ("semanal", "Una vez por semana"),
        ("dias_mes", "Días específicos del mes"),
        ("dias_semana", "Días de la semana seleccionados"),
    ]

    DIAS_SEMANA = [
        (0, "Lunes"),
        (1, "Martes"),
        (2, "Miércoles"),
        (3, "Jueves"),
        (4, "Viernes"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]

    medicamento = models.ForeignKey(
        "Medicamento",
        verbose_name="Medicamento",
        on_delete=models.CASCADE,
        related_name="pautas",
    )
    miembro = models.ForeignKey(
        "cuentas.MiembroHogar",
        verbose_name="Integrante",
        on_delete=models.CASCADE,
        related_name="pautas",
    )
    dosis = models.PositiveIntegerField(
        "Dosis por toma",
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Unidades a tomar en cada toma.",
    )
    frecuencia = models.CharField(
        "Frecuencia",
        max_length=20,
        choices=FRECUENCIAS,
        default="diaria",
    )
    intervalo_dias = models.PositiveIntegerField(
        "Cada N días",
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Solo para 'Cada N días'.",
    )
    dias_mes = models.CharField(
        "Días del mes",
        max_length=120,
        blank=True,
        help_text="Días del mes separados por coma (ej.: 14, 20).",
    )
    dias_semana = models.CharField(
        "Días de la semana",
        max_length=20,
        blank=True,
        help_text="Números 0-6 (Lun-Dom) separados por coma (ej.: 0,2,4).",
    )
    hora = models.TimeField("Hora de la toma", null=True, blank=True)
    fecha_inicio = models.DateField("Fecha de inicio", default=timezone.localdate)
    fecha_fin = models.DateField("Fecha de fin", null=True, blank=True)
    activa = models.BooleanField("Pauta activa", default=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Asignado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pautas_creadas",
    )
    creado = models.DateTimeField("Creado el", auto_now_add=True)

    class Meta:
        verbose_name = "Pauta de toma"
        verbose_name_plural = "Pautas de toma"
        ordering = ["-creado"]
        indexes = [
            models.Index(fields=["medicamento", "miembro"]),
            models.Index(fields=["activa"]),
        ]

    def __str__(self):
        return f"{self.medicamento.nombre} → {self.miembro.nombre} ({self.get_frecuencia_display()})"

    def dias_mes_lista(self):
        resultado = []
        for parte in (self.dias_mes or "").split(","):
            parte = parte.strip()
            if parte.isdigit():
                dia = int(parte)
                if 1 <= dia <= 31:
                    resultado.append(dia)
        return resultado

    def dias_semana_lista(self):
        resultado = []
        for parte in (self.dias_semana or "").split(","):
            parte = parte.strip()
            if parte.isdigit():
                dia = int(parte)
                if 0 <= dia <= 6:
                    resultado.append(dia)
        return resultado

    def proximas_tomas(self, desde=None, cantidad=5):
        """Devuelve una lista de fechas (date) de las próximas tomas."""
        from datetime import date, timedelta

        if desde is None:
            desde = timezone.localdate()
        if self.fecha_fin and desde > self.fecha_fin:
            return []

        resultado = []
        cursor = max(desde, self.fecha_inicio)
        tope = self.fecha_fin or (desde + timedelta(days=60))

        while cursor <= tope and len(resultado) < cantidad:
            if self._corresponde(cursor):
                resultado.append(cursor)
            cursor = cursor + timedelta(days=1)
            if cursor > tope:
                break
            # optimización: no iterar más de 90 días
            if (cursor - desde).days > 90:
                break
        return resultado

    def _corresponde(self, fecha):
        if fecha < self.fecha_inicio:
            return False
        if self.fecha_fin and fecha > self.fecha_fin:
            return False

        if self.frecuencia == "diaria":
            return True
        if self.frecuencia == "cada_n_dias":
            delta = (fecha - self.fecha_inicio).days
            return delta % max(1, self.intervalo_dias) == 0
        if self.frecuencia == "semanal":
            return fecha.weekday() == self.fecha_inicio.weekday()
        if self.frecuencia == "dias_mes":
            return fecha.day in self.dias_mes_lista()
        if self.frecuencia == "dias_semana":
            return fecha.weekday() in self.dias_semana_lista()
        return False


# --------------------------------------------------------------------------
# Registro de toma: confirmación de que una dosis fue administrada
# --------------------------------------------------------------------------
class TomaRegistrada(models.Model):
    """Confirmación de que la dosis de una pauta se tomó en una fecha."""

    pauta = models.ForeignKey(
        "PautaToma",
        verbose_name="Pauta",
        on_delete=models.CASCADE,
        related_name="tomas",
    )
    fecha = models.DateField("Fecha de la toma")
    tomada = models.BooleanField("Tomada", default=False)
    notificada = models.BooleanField("Notificación enviada", default=False)
    fecha_registro = models.DateTimeField("Registrado el", auto_now_add=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Registrado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tomas_registradas",
    )

    class Meta:
        verbose_name = "Toma registrada"
        verbose_name_plural = "Tomas registradas"
        ordering = ["-fecha", "-fecha_registro"]
        constraints = [
            models.UniqueConstraint(
                fields=["pauta", "fecha"], name="toma_unica_por_pauta_fecha"
            )
        ]
        indexes = [
            models.Index(fields=["fecha", "tomada"]),
        ]

    def __str__(self):
        estado = "tomada" if self.tomada else "pendiente"
        notificada = " (notificada)" if self.notificada else ""
        return f"{self.pauta} — {self.fecha} ({estado}{notificada})"
