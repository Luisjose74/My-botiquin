# Mi Botiquín Digital

Aplicación web para gestionar el inventario de medicamentos de un hogar:
registro con foto de la caja, categorías, fechas de vencimiento, cantidades,
ubicación y alertas de vencimiento.

## Requisitos

- Python 3.12+
- Django 6.1.1 (ver `requirements.txt`)

## Instalación

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
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

## Correo electrónico (recuperación de contraseña)

El envío se hace por SMTP (Gmail). Las credenciales se leen de variables de
entorno o del archivo `.env` (no se sube a GitHub).

1. Copia `.env.example` a `.env`.
2. Crea una cuenta dedicada de Gmail (recomendado) y activa la verificación
   en dos pasos.
3. Genera una **contraseña de aplicación** en
   https://myaccount.google.com/apppasswords
4. Completa `.env`:

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-cuenta@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
DEFAULT_FROM_EMAIL=Mi Botiquín Digital <tu-cuenta@gmail.com>
```

5. Prueba el envío desde la consola de Django:

```powershell
python manage.py shell
```

```python
from django.core.mail import send_mail
send_mail(
    "Prueba Mi Botiquín Digital",
    "Si lees esto, el SMTP funciona correctamente.",
    "tu-cuenta@gmail.com",
    ["tu-correo@ejemplo.com"],
)
```

Si no llega, revisa la carpeta de spam la primera vez.

## Feria / URL pública

Para exponer la app con un túnel (ngrok, cloudflared, etc.) en `.env`:

```
DJANGO_DEBUG=True
DJANGO_TRAS_PROXY_HTTPS=True
ALLOWED_HOSTS=tu-dominio.ngrok-free.app,localhost,127.0.0.1
SITE_URL=https://tu-dominio.ngrok-free.app
```

- `CSRF_TRUSTED_ORIGINS` se deriva solo de `ALLOWED_HOSTS` (`https://tu-dominio...`).
  Defínelo a mano solo si necesitas otros orígenes.
- Mantén `DJANGO_DEBUG=True` para la demostración: con `False` Django no sirve
  los archivos estáticos (CSS) y la página se ve sin estilo.
- Los enlaces de los correos usan `SITE_URL`, así que llegan con la URL pública.

## Seguridad y producción

- `DJANGO_SECRET_KEY` debe definirse en `.env` (genera una nueva con
  `python -c "import secrets; print(secrets.token_urlsafe(50))"`).
- Con `DJANGO_DEBUG=False` la aplicación no arranca sin `DJANGO_SECRET_KEY`.
- Nunca subas `.env` al repositorio.

## Alertas por correo

Cada alerta aparece en el panel. Si el usuario eligió el canal **Correo
electrónico** en su perfil, además recibe un único correo con las alertas nuevas
(no se repiten las ya enviadas).

Tipos de alerta (en orden de prioridad): agotado, vencido, próximo a vencer
(30 días o menos) y stock bajo (2 unidades o menos).

Para recalcular alertas y enviar correos sin abrir la app:

```powershell
python manage.py sincronizar_alertas
```

Para enviar las alertas matutinas de tomas del día (según las pautas activas):

```powershell
python manage.py enviar_alertas_tomas
```

Para enviar recordatorios de toma para las pautas programadas en la hora actual:

```powershell
python manage.py enviar_recordatorios_hora
```

IMPORTANTE: el comando compara la hora y el minuto exactos de la pauta. Para que las alertas lleguen a la hora configurada (ej. 9:10 p.m.) debes programarlo para ejecutarse **cada minuto**:

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
