"""Genera datos de prueba para Mi Botiquín Digital.

Crea:
  * 2 usuarios nuevos (con sus hogares y perfiles principales).
  * 20 medicamentos (10 por usuario) con estados variados:
      - vigentes (mas de 30 dias para vencer)
      - proximos a vencer en 30 / 15 / 5 dias
      - vencidos (fecha ya pasada)
  * Una imagen generada con Pillow (PIL) en media/medicamentos/ para cada
    medicamento, asignada al campo `foto`.

Ejecuta con:  venv/Scripts/python.exe scripts/generar_datos_prueba.py
"""
import os
import sys

# Asegura que la raiz del proyecto (donde vive botiquin_project/) este en sys.path,
# ya que al ejecutar este script directamente sys.path[0] es la carpeta scripts/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "botiquin_project.settings")
django.setup()

from django.db import transaction
from django.utils import timezone

from PIL import Image, ImageDraw, ImageFont

from cuentas.models import Usuario
from botiquin.models import (
    Medicamento,
    Categoria,
    Clasificacion,
    EstadoInventario,
    Presentacion,
    CondicionAlmacenamiento,
)

MEDIA_MEDICAMENTOS = "media/medicamentos"

# ---------------------------------------------------------------------------
# Usuarios de prueba
# ---------------------------------------------------------------------------
USUARIOS = [
    {
        "username": "neidy.rodriguez",
        "email": "neidy.rodriguez@email.com",
        "password": "Botiquin_Neidy_2026",
        "first_name": "Neidy Julieth",
        "last_name": "Rodriguez Patino",
        "hogar": "Hogar Rodriguez Patiño",
        "miembro": "Neidy (titular)",
    },
    {
        "username": "carlos.ruiz",
        "email": "carlos.ruiz@email.com",
        "password": "Botiquin_Carlos_2026",
        "first_name": "Carlos",
        "last_name": "Ruiz Gomez",
        "hogar": "Hogar Ruiz Gomez",
        "miembro": "Carlos (titular)",
    },
]

# ---------------------------------------------------------------------------
# Medicamentos de prueba: (nombre, concentracion, dias_desde_hoy, cantidad)
# dias_desde_hoy > 0 : futuro (vigente / proximo a vencer)
# dias_desde_hoy < 0 : ya vencio
# ---------------------------------------------------------------------------
MEDICAMENTOS_POR_USUARIO = [
    # Usuario 1: Neidy (10 medicamentos)
    [
        ("Paracetamol", "500 mg", 60, 20, "tableta", "vigente"),
        ("Omeprazol", "20 mg", 120, 14, "capsula", "vigente"),
        ("Loratadina", "10 mg", 365, 30, "tableta", "vigente"),
        ("Amoxicilina", "500 mg", 30, 12, "capsula", "proximo_30"),
        ("Ibuprofeno", "400 mg", 15, 8, "tableta", "proximo_15"),
        ("Clorfenamina", "4 mg", 5, 20, "tableta", "proximo_5"),
        ("Aspirina", "100 mg", -2, 1, "tableta", "vencido"),
        ("Azitromicina", "500 mg", -7, 6, "tableta", "vencido"),
        ("Diclofenaco", "50 mg", -14, 1, "tableta", "vencido"),
        ("Salbutamol", "100 mcg", -45, 1, "aerosol", "vencido"),
    ],
    # Usuario 2: Carlos (10 medicamentos)
    [
        ("Metformina", "850 mg", 90, 60, "tableta", "vigente"),
        ("Losartan", "50 mg", 180, 30, "tableta", "vigente"),
        ("Cetirizina", "10 mg", 30, 15, "tableta", "proximo_30"),
        ("Ranitidina", "150 mg", 15, 10, "tableta", "proximo_15"),
        ("Dexametasona", "4 mg", 5, 4, "tableta", "proximo_5"),
        ("Naproxeno", "250 mg", -1, 2, "tableta", "vencido"),
        ("Atorvastatina", "20 mg", -3, 1, "tableta", "vencido"),
        ("Enalapril", "10 mg", -10, 7, "tableta", "vencido"),
        ("Cefalexina", "500 mg", -20, 5, "capsula", "vencido"),
        ("Hidrocortisona", "1 %", -60, 1, "crema", "vencido"),
    ],
]


def fuente_tamano(tamanos):
    """Devuelve una fuente TrueType si hay una disponible, si no la por defecto."""
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


def generar_imagen_medicamento(ruta, nombre, estado, fecha_venc):
    """Genera una imagen JPEG tipo etiqueta de medicamento con Pillow."""
    ancho, alto = 640, 420
    colores_estado = {
        EstadoInventario.VIGENTE: (34, 139, 34),      # verde bosque
        EstadoInventario.PROXIMO: (255, 165, 0),      # naranja
        EstadoInventario.VENCIDO: (178, 34, 34),      # rojo fuego
        EstadoInventario.AGOTADO: (128, 128, 128),    # gris
    }
    fondo = colores_estado.get(estado, (70, 130, 180))

    imagen = Image.new("RGB", (ancho, alto), fondo)
    dibujo = ImageDraw.Draw(imagen)

    # Borde decorativo
    dibujo.rectangle([10, 10, ancho - 11, alto - 11], outline=(255, 255, 255), width=4)

    titulo_font = fuente_tamano([40, 36, 32])
    texto_font = fuente_tamano([28, 26, 24])
    fecha_font = fuente_tamano([30, 28, 26])

    # Nombre del medicamento (ajuste de tamano si es muy largo)
    nombre_ajustado = nombre
    while dibujo.textlength(nombre_ajustado, font=titulo_font) > ancho - 120 and len(nombre_ajustado) > 6:
        nombre_ajustado = nombre_ajustado[:-1]
    dibujo.text((40, 40), nombre_ajustado, font=titulo_font, fill=(255, 255, 255))

    # Estado
    etiqueta_estado = {
        EstadoInventario.VIGENTE: "VIGENTE",
        EstadoInventario.PROXIMO: "PROXIMO A VENCER",
        EstadoInventario.VENCIDO: "VENCIDO",
        EstadoInventario.AGOTADO: "AGOTADO",
    }[estado]
    dibujo.text((40, 110), etiqueta_estado, font=texto_font, fill=(255, 255, 0))

    # Fecha de vencimiento
    fecha_texto = fecha_venc.strftime("%d/%m/%Y")
    dibujo.text((40, 160), f"Vencimiento: {fecha_texto}", font=fecha_font, fill=(255, 255, 255))

    # Pie de pagina
    pie_font = fuente_tamano([22, 20, 18])
    dibujo.text((40, alto - 50), "Mi Botiquín Digital - imagen de prueba generada con Pillow",
                font=pie_font, fill=(240, 240, 240))

    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    imagen.convert("RGB").save(ruta, "JPEG", quality=85)
    return ruta


@transaction.atomic
def poblar():
    hoy = timezone.localdate()
    creada = []
    resultados_medicamentos = []

    # Categorias y clasificaciones de uso (ya existen tras migrate; get_or_create es seguro)
    categorias = list(Categoria.objects.all())
    clasificaciones = list(Clasificacion.objects.all())
    if not clasificaciones:
        for nombre in ("Tratamiento cronico", "Uso ocasional", "Antigripal", "Control de presion", "Vitaminas"):
            clasificaciones.append(Clasificacion.objects.get_or_create(nombre=nombre)[0])

    for idx, datos in enumerate(USUARIOS):
        usuario = Usuario.objects.create_user(
            username=datos["username"],
            email=datos["email"],
            password=datos["password"],
            first_name=datos["first_name"],
            last_name=datos["last_name"],
        )
        # La senal post_save de Usuario ya creo el Hogar y el MiembroHogar principal.
        usuario.refresh_from_db()
        hogar = usuario.hogar
        miembro = usuario.perfil_miembro
        creada.append((usuario, datos["password"]))

        for nro, (nombre, concentracion, dias, cantidad, presentacion, estado_clave) in enumerate(
            MEDICAMENTOS_POR_USUARIO[idx], start=1
        ):
            fecha_venc = hoy + timedelta(days=dias)

            if estado_clave == "vigente":
                estado = EstadoInventario.VIGENTE
            elif estado_clave.startswith("proximo"):
                estado = EstadoInventario.PROXIMO
            else:
                estado = EstadoInventario.VENCIDO

            slug_nombre = "".join(c.lower() if c.isalnum() else "_" for c in nombre)[:25]
            nombre_archivo = f"med_{idx:02d}_{nro:02d}_{slug_nombre}.jpg"
            ruta_imagen = os.path.join(MEDIA_MEDICAMENTOS, nombre_archivo)
            generar_imagen_medicamento(ruta_imagen, nombre, estado, fecha_venc)

            med = Medicamento(
                usuario=usuario,
                miembro=miembro,
                categoria=categorias[nro % len(categorias)] if categorias else None,
                clasificacion=clasificaciones[nro % len(clasificaciones)] if clasificaciones else None,
                nombre=nombre,
                concentracion=concentracion,
                presentacion=presentacion,
                cantidad=cantidad,
                lote=f"LOT-{idx:02d}{nro:02d}",
                registro_sanitario=f"INVIMA-{idx:02d}{nro:02d}-2026",
                indicacion_prescrita="Uso bajo indicacion medica.",
                fecha_vencimiento=fecha_venc,
                condicion_almacenamiento=CondicionAlmacenamiento.SECO,
                ubicacion="Botiquin principal",
                notas="Medicamento generado por script de datos de prueba.",
                foto=f"medicamentos/{nombre_archivo}",
                activo=True,
            )
            med.full_clean()
            med.save()
            resultados_medicamentos.append((usuario, med, dias, fecha_venc))

    return creada, resultados_medicamentos


def main():
    print("=" * 70)
    print("GENERADOR DE DATOS DE PRUEBA - Mi Botiquín Digital")
    print("=" * 70)
    creada, medicamentos = poblar()

    print("\nUSUARIOS CREADOS")
    print("-" * 70)
    for usuario, password in creada:
        print(f"  Nombre de usuario: {usuario.username}")
        print(f"  Correo electronico: {usuario.email}")
        print(f"  Contrasena: {password}")
        print(f"  Hogar: {usuario.hogar.nombre if usuario.hogar else '-'}")
        print("-" * 70)

    print("\nMEDICAMENTOS CREADOS (20 en total, 10 por usuario)")
    print("-" * 70)
    hoy = timezone.localdate()
    for usuario, med, dias, fecha_venc in medicamentos:
        estado = med.estado
        etiqueta = {
            EstadoInventario.VIGENTE: "VIGENTE",
            EstadoInventario.PROXIMO: "PROXIMO A VENCER",
            EstadoInventario.VENCIDO: "VENCIDO",
        }.get(estado, estado)
        dias_txt = f"{dias} dias" if dias >= 0 else f"hace {abs(dias)} dias"
        print(f"  [{usuario.username}] {med.nombre_completo} ({med.presentacion}) - "
              f"{etiqueta} - vence {fecha_venc.strftime('%d/%m/%Y')} ({dias_txt}) - "
              f"foto: {med.foto.name}")

    resumen = {}
    for _, med, _, _ in medicamentos:
        resumen[med.estado] = resumen.get(med.estado, 0) + 1
    print("-" * 70)
    print("Resumen por estado:")
    for estado in (EstadoInventario.VIGENTE, EstadoInventario.PROXIMO, EstadoInventario.VENCIDO):
        print(f"  {EstadoInventario(estado).label}: {resumen.get(estado, 0)}")
    print(f"  Total: {len(medicamentos)}")

    print("\nCREDENCIALES FINALES (usuarios nuevos):")
    print("=" * 70)
    for usuario, password in creada:
        print(f"  Correo: {usuario.email:<30} | Contrasena: {password}")
    print("=" * 70)
    print("\nListo. Puedes iniciar sesion con cualquiera de los dos usuarios.")


if __name__ == "__main__":
    main()
