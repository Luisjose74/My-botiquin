# Mi Botiquín Digital

Aplicación web para gestionar el inventario de medicamentos de un hogar:
registro con foto de la caja, categorías, fechas de vencimiento, cantidades,
ubicación, alertas escalonadas de vencimiento (30, 15 y 5 días) y recomendaciones
de atención farmacéutica preventiva (Regencia de Farmacia).

Incluye además un **sitio público** (portada, guía de educación sanitaria,
página institucional y textos legales) y un **panel privado** para las
familias que usan la herramienta.

## Estructura del sitio

| Dirección | Página | Acceso |
| --- | --- | --- |
| `/` | Portada pública (qué es el proyecto, funciones, FAQ) | Público |
| `/educacion/` | Guía de educación sanitaria (Regencia de Farmacia) | Público |
| `/acerca-de/` | Página institucional (origen, metodología, créditos) | Público |
| `/contacto/` | Formulario de contacto con el equipo del proyecto | Público |
| `/privacidad/` | Política de privacidad (Ley 1581 de 2012) | Público |
| `/terminos/` | Términos y condiciones de uso | Público |
| `/sitemap.xml` | Mapa del sitio para los buscadores | Público |
| `/robots.txt` | Instrucciones para los buscadores | Público |
| `/app/` | Panel de la aplicación (resumen del botiquín) | Con sesión |
| `/botiquin/…` | Inventario, alertas, pautas y tomas | Con sesión |
| `/cuentas/…` | Registro, perfil, hogar compartido | Mixto |

## Requisitos

- Python 3.12+
- Django 6.1.1 (ver `requirements.txt`)

## Instalación

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

En producción (o en una copia de entrega) hay que recopilar los archivos
estáticos, que WhiteNoise sirve cuando `DJANGO_DEBUG=False`:

```powershell
python manage.py collectstatic --noinput
```

> Con `DJANGO_DEBUG=False`, `runserver` sigue sirviendo los estáticos gracias a
> WhiteNoise, siempre que se haya ejecutado `collectstatic` al menos una vez.

## Configuración (`.env`)

Todas las variables están documentadas en `.env.example`. Las essentials:

| Variable | Para qué sirve |
| --- | --- |
| `DJANGO_DEBUG` | `False` en producción. Sin `DJANGO_SECRET_KEY` la app no arranca. |
| `DJANGO_SECRET_KEY` | Clave secreta: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `ALLOWED_HOSTS` | Dominios permitidos, separados por coma. Nunca `*` en producción. |
| `CSRF_TRUSTED_ORIGINS` | Se deriva de `ALLOWED_HOSTS` si lo dejas vacío. |
| `SITE_URL` | URL pública; se usa en los enlaces de los correos. |
| `DJANGO_TRAS_PROXY_HTTPS` | `True` si la app está detrás de un túnel HTTPS (ngrok). |
| `DJANGO_SECURE_SSL_REDIRECT` | Redirige todo el tráfico a HTTPS. |
| `DJANGO_SESSION_COOKIE_SECURE` / `DJANGO_CSRF_COOKIE_SECURE` | Cookies solo por HTTPS. |
| `DJANGO_SECURE_HSTS_SECONDS` | HSTS (`31536000` con dominio estable, `0` en túneles). |
| `EMAIL_*` | Configuración SMTP estándar de Django. |

Los flags de HTTPS se activan por defecto cuando `DJANGO_DEBUG=False`, y se
pueden apagar por `.env` para probar en la red local sin certificado.

Comprobación rápida de la configuración de seguridad:

```powershell
python manage.py check --deploy
```

## Acceso en red local (LAN) y túneles

Por defecto Django solo escucha en `127.0.0.1` (localhost). Para que otros
dispositivos de la misma red (o un túnel público) puedan probar la app:

```powershell
python manage.py runserver 0.0.0.0:8000
```

O usa los scripts incluidos:

```powershell
# Windows
.\run_lan.ps1
# Linux / macOS
./run_lan.sh
```

El script detecta la IP local, crea (si es posible) una regla de firewall para
el puerto 8000 y arranca el servidor. Al finalizar muestra la URL de acceso, por
ejemplo `http://192.168.1.25:8000`.

Verifica la conectividad con:

```powershell
python verificar_lan.py
```

Notas:

- Con `DJANGO_DEBUG=True` y `ALLOWED_HOSTS` vacío en `.env`, la app acepta
  cualquier host (LAN + túneles) de forma segura para desarrollo.
- En producción (`DJANGO_DEBUG=False`) define `ALLOWED_HOSTS` con los dominios
  reales; nunca uses `*`.
- Si un dispositivo no carga la página, revisa el firewall de Windows
  (Windows Defender → Firewall → "Permitir una aplicación") o el antivirus.
- Para túneles HTTPS (ngrok, cloudflared) sigue la sección "Feria / URL pública".

## Correo electrónico (SMTP)

El envío usa la **configuración estándar de Django** (`EMAIL_BACKEND`,
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`), leída de `.env`.

1. Copia `.env.example` a `.env`.
2. Crea una cuenta dedicada de Gmail (recomendado) y activa la verificación
   en dos pasos.
3. Genera una **contraseña de aplicación** en
   https://myaccount.google.com/apppasswords (16 caracteres, sin espacios).
4. Completa `.env`:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=tu-cuenta@gmail.com
EMAIL_HOST_PASSWORD=xxxxxxxxxxxxxxxx
DEFAULT_FROM_EMAIL=Mi Botiquín Digital <tu-cuenta@gmail.com>
EMAIL_TIMEOUT=10
```

5. Prueba el envío:

```powershell
# Prueba local: captura el correo en un servidor SMTP interno (sin internet)
python scripts/probar_correo.py --local

# Prueba real: envía con el SMTP configurado en .env
python scripts/probar_correo.py --real tu-correo@ejemplo.com
```

Si no llega, revisa la carpeta de spam la primera vez. Si el error es
`SMTPServerDisconnected` durante la autenticación, la contraseña de aplicación
es incorrecta o fue revocada: genera una nueva.

> **Importante:** si una contraseña de aplicación se ha compartido o quedó
> expuesta, revócala en Google y genera otra. No la guardes en el repositorio.

## Feria / URL pública (túnel HTTPS)

Para exponer la app con un túnel (ngrok, cloudflared, etc.) en `.env`:

```
DJANGO_DEBUG=False
DJANGO_TRAS_PROXY_HTTPS=True
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
ALLOWED_HOSTS=tu-dominio.ngrok-free.app,localhost,127.0.0.1
SITE_URL=https://tu-dominio.ngrok-free.app
```

- `CSRF_TRUSTED_ORIGINS` se deriva solo de `ALLOWED_HOSTS` (`https://tu-dominio...`).
  Defínelo a mano solo si necesitas otros orígenes.
- Con la URL pública de ngrok cambia en cada arranque: actualiza `ALLOWED_HOSTS`
  y `SITE_URL` con la nueva.
- Ejecuta `python manage.py collectstatic --noinput` antes de la demostración
  (con `DEBUG=False` los estilos los sirve WhiteNoise desde `staticfiles/`).
- Los enlaces de los correos usan `SITE_URL`, así que llegan con la URL pública.

## Seguridad y producción

- `DJANGO_SECRET_KEY` debe definirse en `.env` (genera una nueva con
  `python -c "import secrets; print(secrets.token_urlsafe(50))"`).
- Con `DJANGO_DEBUG=False` la aplicación no arranca sin `DJANGO_SECRET_KEY`.
- Nunca subas `.env` al repositorio.
- Con `DEBUG=False` se activan cookies seguras y redirección a HTTPS; se
  pueden desactivar por `.env` para uso local en HTTP.
- `python manage.py check --deploy` lista los avisos de seguridad pendientes.

## Alertas de vencimiento (30, 15 y 5 días)

Cada alerta aparece en el panel. Si el usuario eligió el canal **Correo
electrónico** en su perfil, además recibe un correo con las alertas nuevas (no
se repiten las ya enviadas).

Tipos de alerta (en orden de prioridad): agotado, vencido, próximo a vencer y
stock bajo (2 unidades o menos).

El aviso de vencimiento es **escalonado en tres hitos independientes**:

| Días que faltan | Alerta | Comportamiento |
| --- | --- | --- |
| 31 o más | — | Sin aviso. |
| 16 a 30 | `por_vencer_30` | Primer aviso. |
| 6 a 15 | `por_vencer_15` | El aviso de 30 días queda archivado. |
| 1 a 5 | `por_vencer_5` | El aviso de 15 días queda archivado. |
| Vencido | `vencido` | Aviso permanente hasta que se disponga del medicamento. |

Cada hito se avisa por correo una sola vez (controlado por `Alerta.notificada`).
El aviso de "vencido" permanece activo en el panel mientras el medicamento siga
vencido en el inventario.

Para recalcular alertas y enviar correos sin abrir la app:

```powershell
python manage.py sincronizar_alertas
```

## Atención farmacéutica preventiva (Regencia de Farmacia)

La app incluye recomendaciones educativas en el panel de alertas, en el detalle
del medicamento y en los correos:

- No consumas medicamentos vencidos (y entrégalos en puntos de recolección).
- Evita la automedicación.
- Respeta las condiciones de almacenamiento (fresco, seco, sin luz, en su
  envase original y fuera del alcance de los niños).
- No compartas medicamentos.
- Consulta al personal de salud ante dudas de dosis, interacciones o efectos
  adversos.

El texto está centralizado en `templates/botiquin/_consejos_farmacia.html`
(HTML) y `templates/botiquin/_consejos_farmacia.txt` (correo en texto plano),
de modo que se actualiza desde un solo lugar. La página pública
`/educacion/` reutiliza ese mismo bloque, así que el mensaje educativo es
idéntico en el sitio, en la app y en los correos.

## Páginas públicas e institucionales

La app `publico` sirve el sitio público, sin iniciar sesión:

| Página | Archivo | Contenido |
| --- | --- | --- |
| Portada | `templates/publico/portada.html` | Hero, problema, funciones, tabla de hitos de vencimiento, pasos, perfiles, preguntas frecuentes y llamadas a la acción. |
| Educación sanitaria | `templates/publico/educacion.html` | Guía preventiva (almacenamiento, desecho seguro, señales de alarma, interacciones) y cuándo consultar de inmediato. |
| Institucional | `templates/publico/acerca_de.html` | Origen, propósito/misión/visión, metodología de Regencia de Farmacia, qué hace y qué no hace, créditos y ficha técnica. |
| Privacidad | `templates/publico/privacidad.html` | Tratamiento de datos conforme a la Ley 1581 de 2012: responsable, datos, finalidad, base legal, seguridad, derechos del titular, cookies y menores de edad. |
| Términos | `templates/publico/terminos.html` | Objeto, uso del servicio, alcance clínico, propiedad intelectual, limitación de responsabilidad y legislación aplicable. |

Todo el contenido institucional y educativo se edita desde **un solo
archivo**: `publico/contenido.py` (datos de la institución, funciones, pasos,
hitos, preguntas frecuentes y secciones de la guía). Los datos de la
institución también se pueden sobrescribir por entorno sin tocar el código:

```bash
CONTACTO_CORREO=regencia.farmacia@uptc.edu.co
INSTITUCION_NOMBRE=Universidad ...
INSTITUCION_AUTORA=Nombre Apellido
```

Si no se define `CONTACTO_CORREO`, se usa la dirección remitente de
`DEFAULT_FROM_EMAIL`.

Las páginas públicas incluyen metadatos para buscadores (descripción,
canonical y Open Graph), enlace de salto al contenido, navegación adaptable
con menú en móvil y el aviso de que el contenido es educativo y no reemplaza
la consulta profesional.

## Formulario de contacto

`/contacto/` permite escribir al equipo del proyecto sin sesión. El mensaje
se envía por SMTP a la casilla configurada en `CONTACTO_CORREO` (si no se
define, se usa el remitente de `DEFAULT_FROM_EMAIL`) y la respuesta se
puede dirigir al correo de quien escribe (`Reply-To`).

El formulario trae dos protecciones sencillas contra el envío automatizado:
un campo trampa invisible y una marca de tiempo que obliga a que el formulario
permanezca abierto unos segundos. Un envío automatizado se acepta en pantalla
pero no genera correo.

Para probarlo sin salir del computador:

```powershell
python scripts/probar_correo.py --local
```

## Mapas para los buscadores

- `/sitemap.xml` lista solo las páginas públicas (la página privada `/app/` y
  las áreas de cuenta no se indexan).
- `/robots.txt` permite todo lo público y bloquea `/app/`, `/botiquin/`,
  `/cuentas/` y `/admin/`.

Ambos usan el dominio de `SITE_URL` cuando está configurado; si no, el
dominio de la petición.

## Recordatorios de toma y programación

Para enviar las alertas matutinas de tomas del día (según las pautas activas):

```powershell
python manage.py enviar_alertas_tomas
```

Para enviar recordatorios de toma para las pautas programadas en la hora actual:

```powershell
python manage.py enviar_recordatorios_hora
```

IMPORTANTE: el comando compara la hora y el minuto exactos de la pauta. Para que las alertas lleguen a la hora configurada (ej. 9:10 p.m.) debes programarlo para ejecutarse **cada minuto**:

Además, en desarrollo el servidor arranca automáticamente un programador en segundo plano (cada 60s) que dispara los recordatorios sin necesidad de terminal. En producción usa el Programador de tareas / cron.

- Prueba rápida (dejar corriendo en una ventana aparte):
  ```powershell
  .\run_recordatorios.ps1
  ```
- Producción (Programador de tareas de Windows): crea una tarea que ejecute
  `python manage.py enviar_recordatorios_hora` cada 1 minuto, todos los días,
  con "Ejecutar tanto si el usuario inició sesión como si no".
- Linux/macOS (cron): `* * * * * cd /ruta/app && python manage.py enviar_recordatorios_hora`

Programa `enviar_alertas_tomas` a primera hora del día (una vez) y
`enviar_recordatorios_hora` cada minuto para notificar por correo (y WhatsApp si está configurado).

Para ejecutarlo automáticamente cada hora en Windows, sigue la guía
[docs/automatizacion-windows.md](docs/automatizacion-windows.md).

## Pruebas

```powershell
python manage.py test
```

## Paquete de entrega

Para generar el ZIP con el código fuente (sin base de datos, entornos
virtuales ni archivos subidos):

```powershell
python scripts/empaquetar_entrega.py
```

Se crea `MiBotiquinDigital-entrega.zip` en la raíz del proyecto.
