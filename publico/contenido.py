"""Contenido de las páginas públicas e institucionales de Mi Botiquín Digital.

Todo el texto institucional, comercial y educativo que se repite en varias
páginas vive aquí para que pueda actualizarse desde un solo lugar, sin tocar
las plantillas.

Los datos de la institución se pueden sobrescribir con variables de entorno
(ver `.env.example`) para no tener que editar el código en cada entrega:

    CONTACTO_CORREO=regencia.farmacia@uptc.edu.co
    INSTITUCION_NOMBRE=Universidad ...
    INSTITUCION_AUTORA=Nombre Apellido
"""
import os
from email.utils import parseaddr

from django.conf import settings


def _env(nombre, defecto=""):
    """Devuelve la variable de entorno o el valor por defecto."""
    valor = os.environ.get(nombre, "").strip()
    return valor or defecto


def _correo_contacto():
    """Correo de contacto del proyecto.

    Prioridad: `CONTACTO_CORREO` en el entorno y, si no está, la dirección
    remitente configurada en `DEFAULT_FROM_EMAIL` (la que usa la app).
    """
    explicito = _env("CONTACTO_CORREO")
    if explicito:
        return explicito
    remitente = getattr(settings, "DEFAULT_FROM_EMAIL", "")
    return parseaddr(remitente)[1]


#: Datos generals del sitio (nombre, lema, descripción para buscadores).
SITIO = {
    "nombre": "Mi Botiquín Digital",
    "lema": "Organiza, cuida y nunca olvides tus medicamentos",
    "descripcion": (
        "Inventario digital del botiquín del hogar: registra tus medicamentos, "
        "recibe alertas de vencimiento 30, 15 y 5 días antes, comparte el "
        "inventario con tu familia y sigue las pautas de toma."
    ),
    "palabras_clave": [
        "botiquín digital",
        "medicamentos vencidos",
        "alertas de vencimiento",
        "control de medicamentos",
        "pautas de toma",
        "regencia de farmacia",
        "educación sanitaria",
    ],
}


#: Identidad institucional del proyecto (editable por entorno).
INSTITUCION = {
    "nombre": _env(
        "INSTITUCION_NOMBRE",
        "Universidad Pedagógica y Tecnológica de Colombia",
    ),
    "sigla": _env("INSTITUCION_SIGLA", "UPTC"),
    "facultad": _env(
        "INSTITUCION_FACULTAD", "Facultad de Estudios a Distancia"
    ),
    "sede": _env("INSTITUCION_SEDE", "Sogamoso, Boyacá — Colombia"),
    "autora": _env(
        "INSTITUCION_AUTORA", "Neidy Julieth Rodríguez Patiño"
    ),
    "codigo": _env("INSTITUCION_CODIGO", "202410310"),
    "enfoque": _env("PROYECTO_ENFOQUE", "Regencia de Farmacia"),
    "correo": _correo_contacto(),
}


#: Funciones del producto que se presentan en la portada.
FUNCIONES = [
    {
        "icono": "📦",
        "titulo": "Inventario digital del botiquín",
        "texto": (
            "Registra cada caja con nombre, cantidad, fecha de vencimiento, "
            "lote, registro sanitario, categoría, ubicación en casa y una foto "
            "de la etiqueta."
        ),
    },
    {
        "icono": "⏳",
        "titulo": "Alertas escalonadas de vencimiento",
        "texto": (
            "Tres avisos independientes —30, 15 y 5 días— para que decidas con "
            "tiempo si usas, renuevas o retiras el medicamento."
        ),
    },
    {
        "icono": "📉",
        "titulo": "Control de existencias",
        "texto": (
            "Avisos de stock bajo (dos unidades o menos) y de medicamentos "
            "agotados, para reponer antes de quedarte sin medicina."
        ),
    },
    {
        "icono": "👨‍👩‍👧",
        "titulo": "Un inventario por integrante",
        "texto": (
            "Asigna cada medicamento a la persona que lo usa y mira, de un "
            "vistazo, qué necesita atención en casa."
        ),
    },
    {
        "icono": "🏠",
        "titulo": "Hogar compartido con código QR",
        "texto": (
            "Crea tu hogar, comparte un código QR y los integrantes ven el "
            "mismo botiquín sin duplicar registros."
        ),
    },
    {
        "icono": "💊",
        "titulo": "Pautas de toma y recordatorios",
        "texto": (
            "Programa horarios, frecuencia y duración del tratamiento; el "
            "sistema avisa a la hora exacta y confirma cada toma."
        ),
    },
    {
        "icono": "📬",
        "titulo": "Avisos por correo electrónico",
        "texto": (
            "Recibe el resumen de alertas y recordatorios en tu correo, sin "
            "necesidad de tener la aplicación abierta."
        ),
    },
    {
        "icono": "🧾",
        "titulo": "Educación sanitaria preventiva",
        "texto": (
            "Recomendaciones de Regencia de Farmacia sobre almacenamiento, "
            "automedicación, desecho seguro y consulta profesional."
        ),
    },
]


#: Pasos para empezar a usar la aplicación.
PASOS = [
    {
        "numero": "01",
        "titulo": "Crea tu cuenta y tu hogar",
        "texto": (
            "Regístrate con tu correo y crea el hogar compartido. Invita a "
            "los tuyos con un código QR y todos verán el mismo inventario."
        ),
    },
    {
        "numero": "02",
        "titulo": "Registra tus medicamentos",
        "texto": (
            "Sube la foto de la caja o escribe los datos: cantidad, fecha de "
            "vencimiento, lote, registro sanitario, categoría y dónde lo guardas."
        ),
    },
    {
        "numero": "03",
        "titulo": "Activa los avisos por correo",
        "texto": (
            "En tu perfil elige recibir las alertas por correo. Cada hito de "
            "vencimiento se te avisa una sola vez, sin repetir mensajes."
        ),
    },
    {
        "numero": "04",
        "titulo": "Revisa y actúa antes de que venza",
        "texto": (
            "Tu panel muestra qué está por vencer, qué se agotó y qué está "
            "en buen estado, con educación sanitaria para decidir con criterio."
        ),
    },
]


#: Perfiles de usuario para los que la herramienta es útil.
PERFILES = [
    {
        "icono": "🏠",
        "titulo": "Hogares",
        "texto": (
            "Organiza el botiquín familiar y evita comprar de más lo que "
            "todavía sirve."
        ),
    },
    {
        "icono": "👴",
        "titulo": "Adultos mayores y pacientes crónicos",
        "texto": (
            "Varios medicamentos, horarios distintos: las pautas y los "
            "recordatorios ayudan a no saltarse ninguna dosis."
        ),
    },
    {
        "icono": "🧒",
        "titulo": "Hogares con niños",
        "texto": (
            "Ubica cada medicamento y mantén el envase original fuera de su "
            "alcance, como recomienda la Regencia de Farmacia."
        ),
    },
    {
        "icono": "🏥",
        "titulo": "Consultorios y botiquines institucionales",
        "texto": (
            "Controla el inventario de un consultorio pequeño o de un centro "
            "de atención primaria con la misma metodología."
        ),
    },
]


#: Tabla de hitos de aviso de vencimiento (coincide con botiquin/alertas.py).
HITOS_VENCIMIENTO = [
    {
        "dias": "31 días o más",
        "alerta": "Sin aviso",
        "comportamiento": "El medicamento se registra como óptimo.",
    },
    {
        "dias": "16 a 30 días",
        "alerta": "Aviso a 30 días",
        "comportamiento": "Primer aviso: revisa si todavía lo necesitas.",
    },
    {
        "dias": "6 a 15 días",
        "alerta": "Aviso a 15 días",
        "comportamiento": "El aviso de 30 días queda archivado en el historial.",
    },
    {
        "dias": "1 a 5 días",
        "alerta": "Aviso a 5 días",
        "comportamiento": "Últimos días: úsalo si está indicado y retíralo al vencerse.",
    },
    {
        "dias": "Vencido",
        "alerta": "Aviso permanente",
        "comportamiento": "No lo consumas: entrégalo en un punto de recolección.",
    },
]


#: Preguntas frecuentes de la portada.
FAQ = [
    {
        "pregunta": "¿El servicio es gratuito?",
        "respuesta": (
            "Sí. Mi Botiquín Digital es un proyecto académico sin costo para "
            "las familias: bastan un correo y un dispositivo con navegador."
        ),
    },
    {
        "pregunta": "¿Necesito ser farmacéutico o médico para usarlo?",
        "respuesta": (
            "No. Cualquier persona puede registrar y organizar medicamentos. "
            "La aplicación no interpreta dosis ni modifica indicaciones: eso "
            "corresponde al profesional de salud que prescribe."
        ),
    },
    {
        "pregunta": "¿Cómo funcionan las alertas de vencimiento?",
        "respuesta": (
            "El aviso es escalonado: aparece a 30, 15 y 5 días de la fecha de "
            "vencimiento. Cada hito se notifica una sola vez y los anteriores "
            "quedan archivados en el historial."
        ),
    },
    {
        "pregunta": "¿Puedo usarlo para toda la familia?",
        "respuesta": (
            "Sí. Creas un hogar, asignas cada medicamento al integrante que "
            "lo usa y compartes el acceso con un código QR, sin registrar dos "
            "veces el mismo medicamento."
        ),
    },
    {
        "pregunta": "¿Qué pasa con los medicamentos vencidos?",
        "respuesta": (
            "La aplicación te avisa y te recomienda retirarlos del botiquín. "
            "No los consumas: entrégalos en una farmacia o en un punto de "
            "recolección autorizado."
        ),
    },
    {
        "pregunta": "¿Mis datos están seguros?",
        "respuesta": (
            "Las contraseñas se guardan cifradas, la navegación usa HTTPS y "
            "el acceso a los datos está restringido a la cuenta y a su hogar. "
            "Los detalles están en la política de privacidad."
        ),
    },
    {
        "pregunta": "¿Puedo usarlo desde el celular?",
        "respuesta": (
            "Sí. La aplicación está pensada para el teléfono y la "
            "computadora; además puedes dejar que el sistema te avise por "
            "correo electrónico."
        ),
    },
]


#: Aviso de alcance clínico que se repite en las páginas de contenido.
AVISO_PROFESIONAL = (
    "El contenido de este sitio es educativo y de carácter preventivo. "
    "Mi Botiquín Digital no diagnostica, no prescribe y no reemplaza la "
    "consulta con tu médico, tu regente de farmacia o el servicio de urgencias."
)


#: Bloques de la guía de educación sanitaria.
SECCIONES_EDUCACION = [
    {
        "icono": "🧊",
        "titulo": "Cómo almacenar correctamente",
        "texto": (
            "Guarda los medicamentos en su envase original, en lugares frescos, "
            "secos y protegidos de la luz. Si el producto exige refrigeración, "
            "el termómetro del refrigerador debe marcar entre 2 °C y 8 °C. "
            "Separa los medicamentos de uso externo de los de uso oral y "
            "revisa que estén fuera del alcance de los niños."
        ),
    },
    {
        "icono": "🗑️",
        "titulo": "Qué hacer con los medicamentos vencidos",
        "texto": (
            "Retíralos del botiquín y entrégalos en una farmacia o en un punto "
            "de recolección autorizado. No los deseches en la basura ni en el "
            "inodoro: los residuos farmacéuticos contaminan el agua y "
            "pueden volver al consumo humano o animal."
        ),
        "enlace": {
            "texto": "Ver el directorio de Puntos Azules en Sogamoso",
            "url": "publico:puntos_azules",
        },
    },
    {
        "icono": "🚨",
        "titulo": "Señales de alarma",
        "texto": (
            "Ronchas, hinchazón de labios o lengua, dificultad para respirar, "
            "desmayo o convulsiones son señales de una reacción alérgica "
            "grave: pide atención de urgencias de inmediato. También consulta "
            "si presentas vómitos persistentes, confusión, dificultad para "
            "deglutir o un empeoramiento rápido de tus síntomas."
        ),
    },
    {
        "icono": "💬",
        "titulo": "Antes de combinar medicamentos",
        "texto": (
            "Los medicamentos de venta libre, los suplementos y las bebidas "
            "energizantes pueden interactuar con tus tratamientos sin que lo "
            "notes. Registra todo lo que consumes en la aplicación y menciona "
            "esa lista —incluidos los suplementos y las plantas medicinales— "
            "cuando tu profesional de salud te indique un nuevo medicamento."
        ),
    },
    {
        "icono": "👶",
        "titulo": "Niños, embarazo y adultos mayores",
        "texto": (
            "En la población pediátrica y en el embarazo, la dosis depende "
            "del peso, y en los adultos mayores suele ser menor que la del "
            "adulto joven, incluso con el mismo medicamento. No ajustes dosis "
            "por tu cuenta: pida siempre la indicación por peso y la revisión "
            "de la lista completa de medicamentos."
        ),
    },
    {
        "icono": "📝",
        "titulo": "Cómo llevar la lista a la consulta",
        "texto": (
            "Lleva el listado de medicamentos que usas, con dosis y horarios, "
            "a la consulta. Mi Botiquín Digital te ayuda a tener ese listado "
            "al día, pero la decisión clínica siempre es del profesional de "
            "salud."
        ),
    },
]


# ---------------------------------------------------------------------------
# Directorio de Puntos Azules (puntos de recolección de medicamentos)
# ---------------------------------------------------------------------------

#: Texto introductorio de la página de Puntos Azules.
PUNTOS_AZULES_INTRO = {
    "que_son": (
        "Los Puntos Azules son los puntos de recolección de medicamentos "
        "habilitados en droguerías, hospitales y entidades de salud. Allí "
        "entregas los medicamentos que ya no usas: los que vencieron, los que "
        "se deterioraron o los que simplemente te sobran. En vez de terminar "
        "en la basura común, se recogen y se destinan a un manejo adecuado."
    ),
    "proposito": (
        "Un medicamento que llega al río, al embalse o al suelo sigue "
        "actuando: sus componentes activos contaminan el agua que bebemos, "
        "afectan a otros seres vivos y regresan hasta nosotros por la cadena "
        "alimentaria. Los antibióticos desechados al ambiente incluso favorecen "
        "la aparición de bacterias resistentes. Recogerlos y tratarlos bien es, "
        "por eso, una medida de salud pública y de cuidado del ambiente."
    ),
    "prohibicion": (
        "Está prohibido arrojar medicamentos al desagüe, al inodoro o a la "
        "basura común: contaminan el agua, exponen a niños y animales a una "
        "intoxicación accidental y hacen imposible cualquier manejo seguro. "
        "La normativa sanitaria y ambiental del país lo prohíbe expresamente, "
        "y la responsabilidad es de cada persona que tiene medicamentos en su "
        "casa."
    ),
}


#: Puntos de recolección verificados en Sogamoso (Boyacá).
PUNTOS_AZULES = [
    {
        "icono": "🏥",
        "tipo": "Hospital",
        "nombre": "Hospital Regional de Sogamoso",
        "direccion": "",
    },
    {
        "icono": "🏥",
        "tipo": "Entidad de salud",
        "nombre": "Salud Sogamoso, sede Centro",
        "direccion": "",
    },
    {
        "icono": "💊",
        "tipo": "Droguería",
        "nombre": "Droguería Cruz Verde",
        "direccion": "Calle 14 # 11-74",
    },
    {
        "icono": "💊",
        "tipo": "Droguería",
        "nombre": "Droguería Colsubsidio",
        "direccion": "Calle 13 # 11-61",
    },
    {
        "icono": "💊",
        "tipo": "Droguería",
        "nombre": "Droguería Colsubsidio",
        "direccion": "Carrera 10 # 90",
    },
]


#: Nota al pie del directorio (los puntos pueden cambiar).
PUNTOS_AZULES_NOTA = (
    "Los puntos de recolección pueden cambiar de horario o de cobertura. "
    "Confirma antes de ir y, si un punto no puede recibir tu medicamento, "
    "pide orientación a la autoridad de salud o ambiental municipal."
)


#: Pasos para entregar los medicamentos de forma segura.
INSTRUCCIONES_ENTREGA = [
    {
        "icono": "🧺",
        "titulo": "Separa lo que vas a entregar",
        "texto": (
            "Haz dos grupos: los medicamentos no perecederos (tabletas, "
            "cápsulas, jarabes e inyectables) y los perecederos o que "
            "requieren refrigeración (vacunas, sueros y productos con la "
            "fecha próxima a vencer). Estos últimos no siempre son aceptados "
            "en el punto: consérvalos y pregunta por su manejo especial."
        ),
    },
    {
        "icono": "📦",
        "titulo": "No los mezcles con la basura doméstica",
        "texto": (
            "Empaqueta todo en una bolsa resistente o en un recipiente con "
            "tapa, y sepáralo del resto de los residuos de la casa. Si el "
            "envase está roto o el medicamento es líquido, haz doble "
            "empacado (una bolsa dentro de otra)."
        ),
    },
    {
        "icono": "🏷️",
        "titulo": "Conserva el envase original",
        "texto": (
            "Entrega el medicamento en su envase o, al menos, con el nombre y "
            "el principio activo a la vista. El punto necesita identificarlo "
            "para clasificarlo y darle un manejo seguro."
        ),
    },
    {
        "icono": "🚫",
        "titulo": "No entregues elementos de riesgo",
        "texto": (
            "Las jeringas, las agujas, los elementos corto punzantes y los "
            "aerosoles presurizados necesitan un manejo distinto y no se "
            "reciben en los puntos de recolección."
        ),
    },
    {
        "icono": "🕗",
        "titulo": "Entrega dentro del horario del punto",
        "texto": (
            "Cada punto tiene su propia franja de atención. Si no lo reciben, "
            "no dejes el medicamento en la puerta ni lo devuelvas a la "
            "basura: escoge otro punto del directorio o pide orientación."
        ),
    },
]


#: Productos que no deben entregarse en un punto azul.
NO_ENTREGAR = [
    "Jeringas, agujas y elementos corto punzantes.",
    "Aerosoles presurizados y productos inflamables.",
    "Residuos clínicos (sangre, saliva, tejidos y otros productos de atención).",
    "Alimentos, productos de aseo y otros residuos domésticos.",
]


#: Datos del tratamiento de datos (resumen para la política de privacidad).
DATOS_RECOLECTADOS = [
    {
        "icono": "👤",
        "titulo": "Datos de la cuenta",
        "texto": (
            "Nombre de usuario, correo electrónico, nombre y apellido, "
            "contraseña cifrada y, si la subes, una foto de perfil. "
            "También el canal elegido para recibir alertas."
        ),
    },
    {
        "icono": "💊",
        "titulo": "Datos del botiquín",
        "texto": (
            "Nombre del medicamento, cantidad, fecha de vencimiento, lote, "
            "registro sanitario, categoría, ubicación, notas y la foto de la "
            "caja que registres."
        ),
    },
    {
        "icono": "🏠",
        "titulo": "Datos del hogar",
        "texto": (
            "Nombre del hogar, integrantes, relación con el titular, "
            "asignación de medicamentos por persona y las pautas de toma "
            "programadas."
        ),
    },
    {
        "icono": "📄",
        "titulo": "Datos técnicos",
        "texto": (
            "Registros del servidor (dirección IP, navegador y fecha de "
            "acceso) usados para la seguridad y la solución de errores "
            "técnicos."
        ),
    },
]


#: Versión y fecha de las páginas legales.
VERSION_LEGAL = "1.0"
FECHA_ACTUALIZACION = "10 de noviembre de 2026"
