"""Pobla la base de datos con datos de demostración para Mi Botiquín Digital.

Crea:
  * 1 usuario de prueba con datos realistas.
  * 20 medicamentos asociados a ese usuario con estados variados:
      - vigentes (mas de 30 dias para vencer)
      - proximos a vencer en 30, 15 y 5 dias
      - vencidos (fecha ya pasada)
  * Una imagen limpia generada con Pillow (PIL) en media/medicamentos/ para
    cada medicamento, vinculada al campo `foto`.
  * Una pauta de tomas con horarios diarios para cada medicamento, para que
    el modulo de administracion y control de tomas quede operativo.

Ejecuta con:  venv/Scripts/python.exe scripts/poblar_datos_iniciales.py
"""
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "botiquin_project.settings")
django.setup()

from cuentas.models import Usuario, Hogar, MiembroHogar
from botiquin.models import (
    Medicamento,
    Categoria,
    Clasificacion,
    EstadoInventario,
    Presentacion,
    CondicionAlmacenamiento,
    PautaToma,
    HorarioToma,
)

MEDIA_MEDICAMENTOS = "media/medicamentos"

# ---------------------------------------------------------------------------
# Usuario de prueba (una sola cuenta)
# ---------------------------------------------------------------------------
USUARIO_DATOS = {
    "username": "luis.silva",
    "email": "senaluissilva883@gmail.com",
    "password": "MiBotiquin2026!",
    "first_name": "Luis",
    "last_name": "Silva",
}

# ---------------------------------------------------------------------------
# 20 medicamentos: (nombre, concentracion, dias_desde_hoy, cantidad, presentacion)
# dias_desde_hoy > 0 : futuro (vigente / proximo a vencer)
# dias_desde_hoy < 0 : ya vencido
# ---------------------------------------------------------------------------
MEDICAMENTOS = [
    # Vigentes (mas de 30 dias)
    ("Paracetamol", "500 mg", 60, 20, "tableta"),
    ("Omeprazol", "20 mg", 120, 14, "capsula"),
    ("Loratadina", "10 mg", 365, 30, "tableta"),
    ("Metformina", "850 mg", 90, 60, "tableta"),
    ("Losartan", "50 mg", 180, 30, "tableta"),
    # Proximos a vencer en 30 dias
    ("Amoxicilina", "500 mg", 30, 12, "capsula"),
    ("Cetirizina", "10 mg", 30, 15, "tableta"),
    # Proximos a vencer en 15 dias
    ("Ibuprofeno", "400 mg", 15, 8, "tableta"),
    ("Ranitidina", "150 mg", 15, 10, "tableta"),
    # Proximos a vencer en 5 dias
    ("Clorfenamina", "4 mg", 5, 20, "tableta"),
    ("Dexametasona", "4 mg", 5, 4, "tableta"),
    # Vencidos
    ("Aspirina", "100 mg", -2, 1, "tableta"),
    ("Azitromicina", "500 mg", -7, 6, "tableta"),
    ("Diclofenaco", "50 mg", -14, 1, "tableta"),
    ("Naproxeno", "250 mg", -1, 2, "tableta"),
    ("Atorvastatina", "20 mg", -3, 1, "tableta"),
    ("Enalapril", "10 mg", -10, 7, "tableta"),
    ("Cefalexina", "500 mg", -20, 5, "capsula"),
    ("Hidrocortisona", "1 %", -60, 1, "crema"),
    ("Salbutamol", "100 mcg", -45, 1, "aerosol"),
]


def fuente_tamano(tamanos):
    rutas = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for ruta in rutas:
        if os.path.exists(ruta):
            for tam in tamanos:
                try:
                    return ImageFont.truetype(ruta, tam)
                except OSError:
                    continue
    return ImageFont.load_default()


def generar_imagen_medicamento(ruta, nombre, concentracion, presentacion, estado, fecha_venc):
    ancho, alto = 640, 420
    colores_estado = {
        EstadoInventario.VIGENTE: (34, 139, 34),
        EstadoInventario.PROXIMO: (255, 165, 0),
        EstadoInventario.VENCIDO: (178, 34, 34),
        EstadoInventario.AGOTADO: (128, 128, 128),
    }
    fondo = colores_estado.get(estado, (70, 130, 180))

    imagen = Image.new("RGB", (ancho, alto), fondo)
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle([10, 10, ancho - 11, alto - 11], outline=(255, 255, 255), width=4)

    titulo_font = fuente_tamano([40, 36, 32])
    texto_font = fuente_tamano([28, 26, 24])
    fecha_font = fuente_tamano([30, 28, 26])
    pie_font = fuente_tamano([22, 20, 18])

    nombre_completo = f"{nombre} {concentracion}".strip()
    nombre_ajustado = nombre_completo
    while dibujo.textlength(nombre_ajustado, font=titulo_font) > ancho - 120 and len(nombre_ajustado) > 6:
        nombre_ajustado = nombre_ajustado[:-1]
    dibujo.text((40, 40), nombre_ajustado, font=titulo_font, fill=(255, 255, 255))

    etiqueta_estado = {
        EstadoInventario.VIGENTE: "VIGENTE",
        EstadoInventario.PROXIMO: "PROXIMO A VENCER",
        EstadoInventario.VENCIDO: "VENCIDO",
        EstadoInventario.AGOTADO: "AGOTADO",
    }[estado]
    dibujo.text((40, 110), etiqueta_estado, font=texto_font, fill=(255, 255, 0))

    dibujo.text((40, 160), f"Vencimiento: {fecha_venc.strftime('%d/%m/%Y')}", font=fecha_font, fill=(255, 255, 255))
    dibujo.text((40, 210), f"Presentacion: {Presentacion(presentacion).label}", font=texto_font, fill=(255, 255, 255))

    dibujo.text((40, alto - 50), "Mi Botiquín Digital - imagen generada con Pillow", font=pie_font, fill=(240, 240, 240))

    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    imagen.convert("RGB").save(ruta, "JPEG", quality=85)
    return ruta


def estado_para_dias(dias):
    if dias < 0:
        return EstadoInventario.VENCIDO
    if dias <= 30:
        return EstadoInventario.PROXIMO
    return EstadoInventario.VIGENTE


@transaction.atomic
def poblar():
    hoy = timezone.localdate()

    # Usuario
    usuario = Usuario.objects.create_user(
        username=USUARIO_DATOS["username"],
        email=USUARIO_DATOS["email"],
        password=USUARIO_DATOS["password"],
        first_name=USUARIO_DATOS["first_name"],
        last_name=USUARIO_DATOS["last_name"],
    )
    usuario.refresh_from_db()
    hogar = usuario.hogar
    miembro = usuario.perfil_miembro

    # Clasificaciones de uso (seguro si ya existen)
    nombres_clasificaciones = ("Tratamiento cronico", "Uso ocasional", "Antigripal", "Control de presion", "Vitaminas")
    clasificaciones = []
    for nombre in nombres_clasificaciones:
        clasificaciones.append(Clasificacion.objects.get_or_create(nombre=nombre)[0])

    categorias = list(Categoria.objects.all())
    if not categorias:
        raise RuntimeError("No hay categorias. Ejecuta migrate primero.")

    resultados = []

    for nro, (nombre, concentracion, dias, cantidad, presentacion) in enumerate(MEDICAMENTOS, start=1):
        fecha_venc = hoy + timedelta(days=dias)
        estado = estado_para_dias(dias)

        slug = "".join(c.lower() if c.isalnum() else "_" for c in nombre)[:25]
        nombre_archivo = f"med_{nro:02d}_{slug}.jpg"
        ruta_imagen = os.path.join(MEDIA_MEDICAMENTOS, nombre_archivo)
        generar_imagen_medicamento(ruta_imagen, nombre, concentracion, presentacion, estado, fecha_venc)

        med = Medicamento(
            usuario=usuario,
            miembro=miembro,
            categoria=categorias[(nro - 1) % len(categorias)],
            clasificacion=clasificaciones[(nro - 1) % len(clasificaciones)],
            nombre=nombre,
            concentracion=concentracion,
            presentacion=presentacion,
            cantidad=cantidad,
            lote=f"LOT-{nro:02d}",
            registro_sanitario=f"INVIMA-{nro:02d}-2026",
            indicacion_prescrita="Uso bajo indicacion medica.",
            fecha_vencimiento=fecha_venc,
            condicion_almacenamiento=CondicionAlmacenamiento.SECO,
            ubicacion="Botiquin principal",
            notas="Medicamento generado por script de datos iniciales.",
            foto=f"medicamentos/{nombre_archivo}",
            activo=True,
        )
        med.full_clean()
        med.save()

        # Pauta de tomas con horarios diarios (recordatorios independientes)
        pauta = PautaToma.objects.create(
            medicamento=med,
            miembro=miembro,
            dosis=1,
            frecuencia="diaria",
            intervalo_dias=1,
            fecha_inicio=hoy,
            activa=True,
            creado_por=usuario,
        )
        # Horarios de toma: 08:00 y 20:00 (dos recordatorios independientes)
        HorarioToma.objects.create(pauta=pauta, hora="08:00", orden=1)
        HorarioToma.objects.create(pauta=pauta, hora="20:00", orden=2)

        resultados.append((med, dias, fecha_venc, pauta))

    return usuario, resultados


def main():
    print("=" * 70)
    print("POBLADOR DE DATOS INICIALES - Mi Botiquín Digital")
    print("=" * 70)

    usuario, medicamentos = poblar()

    print("\nCUENTA DE USUARIO CREADA")
    print("-" * 70)
    print(f"  Nombre de usuario: {usuario.username}")
    print(f"  Correo electronico: {usuario.email}")
    print(f"  Contrasena: {USUARIO_DATOS['password']}")
    print(f"  Hogar: {usuario.hogar.nombre if usuario.hogar else '-'}")
    print("-" * 70)

    print("\nMEDICAMENTOS CREADOS (20 en total)")
    print("-" * 70)
    hoy = timezone.localdate()
    resumen = {}
    for idx, (med, dias, fecha_venc, pauta) in enumerate(medicamentos, start=1):
        estado = med.estado
        etiqueta = {
            EstadoInventario.VIGENTE: "VIGENTE",
            EstadoInventario.PROXIMO: "PROXIMO A VENCER",
            EstadoInventario.VENCIDO: "VENCIDO",
        }.get(estado, estado)
        resumen[estado] = resumen.get(estado, 0) + 1
        dias_txt = f"{dias} dias" if dias >= 0 else f"hace {abs(dias)} dias"
        print(f"  {idx:02d}. {med.nombre_completo} ({med.presentacion}) - {etiqueta} - "
              f"vence {fecha_venc.strftime('%d/%m/%Y')} ({dias_txt}) - "
              f"pauta: {pauta.get_frecuencia_display()} 08:00 y 20:00 - foto: {med.foto.name}")
    print("-" * 70)
    print("Resumen por estado:")
    for estado in (EstadoInventario.VIGENTE, EstadoInventario.PROXIMO, EstadoInventario.VENCIDO):
        print(f"  {EstadoInventario(estado).label}: {resumen.get(estado, 0)}")
    print(f"  Total: {len(medicamentos)}")

    print("\nCREDENCIALES DE ACCESO")
    print("=" * 70)
    print(f"  Correo:    {usuario.email}")
    print(f"  Usuario:   {usuario.username}")
    print(f"  Contrasena: {USUARIO_DATOS['password']}")
    print("=" * 70)
    print("\nListo. Puedes iniciar sesion con las credenciales de arriba.")


if __name__ == "__main__":
    main()
