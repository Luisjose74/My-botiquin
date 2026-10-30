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

Para exponer la app con un túnel (ngrok, cloudflared, etc.), define:

```
ALLOWED_HOSTS=tu-dominio.ngrok-free.app,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://tu-dominio.ngrok-free.app
```

El enlace de recuperación se genera a partir del host de la petición, así que
con la URL pública llegará correctamente al celular del usuario.

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

Para ejecutarlo automáticamente cada hora en Windows, sigue la guía
[docs/automatizacion-windows.md](docs/automatizacion-windows.md).
