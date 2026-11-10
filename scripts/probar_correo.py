"""Prueba del envío de correo de Mi Botiquín Digital.

Uso:
    python scripts/probar_correo.py --real destino@correo.com
    python scripts/probar_correo.py --local

`--local` levanta un servidor SMTP de captura en el propio proceso (sin
internet) y comprueba que Django envía el mensaje completo: destinatario,
asunto, cuerpo en texto plano y la alternativa HTML. Sirve para verificar el
cableado (EMAIL_BACKEND, plantillas, adjuntos) sin depender de Gmail.

`--real` usa el SMTP configurado en `.env` (Gmail) y envía a un buzón real.
"""
import argparse
import email
import email.header
import os
import socket
import socketserver
import sys
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "botiquin_project.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.mail import EmailMultiAlternatives  # noqa: E402

ASUNTO = "Prueba Mi Botiquín Digital"
CUERPO = "Si lees este mensaje, el envío de correo funciona correctamente."


class ServidorSMTPCaptura(socketserver.ThreadingTCPServer):
    """Servidor SMTP mínimo que guarda los mensajes recibidos."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        self.buzones = []
        super().__init__(*args, **kwargs)


class ManejadorSMTP(socketserver.StreamRequestHandler):
    def responder(self, linea):
        self.wfile.write(f"{linea}\r\n".encode("utf-8"))
        self.wfile.flush()

    def handle(self):
        self.responder("220 Prueba Mi Botiquín Digital")
        remitente, destinatarios, datos = "", [], []
        while True:
            linea = self.rfile.readline()
            if not linea:
                break
            comando = linea.decode("utf-8", "replace").strip()
            upper = comando.upper()
            if upper.startswith(("EHLO", "HELO")):
                self.responder("250-pc.local")
                self.responder("250 AUTH PLAIN LOGIN")
            elif upper.startswith("AUTH"):
                self.responder("235 2.7.0 Authentication successful")
            elif upper.startswith("MAIL FROM"):
                remitente = comando.split(":", 1)[1].strip()
                self.responder("250 2.1.0 Ok")
            elif upper.startswith("RCPT TO"):
                destinatarios.append(comando.split(":", 1)[1].strip())
                self.responder("250 2.1.5 Ok")
            elif upper == "DATA":
                self.responder("354 End data with <CR><LF>.<CR><LF>")
                while True:
                    linea = self.rfile.readline()
                    if not linea or linea.strip() == b".":
                        break
                    datos.append(linea.decode("utf-8", "replace"))
                cuerpo = "".join(datos)
                self.server.buzones.append(
                    {"remitente": remitente, "destinatarios": destinatarios, "cuerpo": cuerpo}
                )
                self.responder("250 2.0.0 Ok: queued")
            elif upper == "RSET":
                remitente, destinatarios, datos = "", [], []
                self.responder("250 2.0.0 Ok")
            elif upper == "NOOP":
                self.responder("250 2.0.0 Ok")
            elif upper == "QUIT":
                self.responder("221 2.0.0 Bye")
                break
            else:
                self.responder("250 2.0.0 Ok")


def prueba_local(destinatario):
    servidor = ServidorSMTPCaptura(("127.0.0.1", 0), ManejadorSMTP)
    puerto = servidor.server_address[1]
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()

    try:
        from django.test import override_settings

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
            EMAIL_HOST="127.0.0.1",
            EMAIL_PORT=puerto,
            EMAIL_USE_TLS=False,
            EMAIL_USE_SSL=False,
            EMAIL_HOST_USER="prueba@local",
            EMAIL_HOST_PASSWORD="prueba",
            DEFAULT_FROM_EMAIL="Mi Botiquín Digital <prueba@local>",
        ):
            mensaje = EmailMultiAlternatives(
                subject=ASUNTO,
                body=CUERPO,
                from_email="Mi Botiquín Digital <prueba@local>",
                to=[destinatario],
            )
            mensaje.attach_alternative(
                "<html><body><p>" + CUERPO + "</p></body></html>", "text/html"
            )
            enviados = mensaje.send()
    finally:
        servidor.shutdown()
        servidor.server_close()

    recibidos = servidor.buzones
    print(f"Correos enviados por Django: {enviados}")
    print(f"Correos recibidos por el servidor: {len(recibidos)}")
    if not recibidos:
        print("FALLO: el servidor no recibió ningún mensaje.")
        return 1

    recibido = recibidos[0]
    cuerpo = recibido["cuerpo"]
    # Decodificar el mensaje (el asunto puede venir codificado en MIME).
    mensaje = email.message_from_string(cuerpo)
    asunto = str(email.header.make_header(email.header.decode_header(mensaje.get("Subject", ""))))
    partes = mensaje.walk()
    hay_html = any(p.get_content_type() == "text/html" for p in partes)
    print(f"Remitente: {recibido['remitente']}")
    print(f"Destinatario: {', '.join(recibido['destinatarios'])}")
    print(f"Asunto recibido: {asunto}")
    print(f"Cuerpo presente: {'OK' if CUERPO in cuerpo else 'NO'}")
    print(f"Alternativa HTML presente: {'OK' if hay_html else 'NO'}")
    ok = (
        enviados == 1
        and len(recibidos) == 1
        and asunto == ASUNTO
        and CUERPO in cuerpo
        and hay_html
    )
    print("RESULTADO:", "OK - el cableado del correo funciona" if ok else "FALLO")
    return 0 if ok else 1


def prueba_real(destinatario):
    from django.core.mail import send_mail

    print(f"Backend: {settings.EMAIL_BACKEND}")
    print(f"Servidor: {settings.EMAIL_HOST}:{settings.EMAIL_PORT} (TLS={settings.EMAIL_USE_TLS})")
    print(f"Usuario: {settings.EMAIL_HOST_USER}")
    try:
        enviados = send_mail(
            ASUNTO,
            CUERPO,
            settings.DEFAULT_FROM_EMAIL,
            [destinatario],
            fail_silently=False,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FALLO de autenticación SMTP: {type(exc).__name__}: {exc}")
        print(
            "Revisa que la contraseña de aplicación de Gmail sea válida "
            "(https://myaccount.google.com/apppasswords) y que la cuenta tenga "
            "verificación en dos pasos activa."
        )
        return 1
    print(f"Correos enviados: {enviados}")
    print("Revisa la bandeja de entrada (y la carpeta de spam) del destinatario.")
    return 0 if enviados else 1


def main():
    parser = argparse.ArgumentParser(description="Prueba de envío de correo.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--real", action="store_true", help="Enviar por el SMTP configurado.")
    grupo.add_argument("--local", action="store_true", help="Capturar el envío en local.")
    parser.add_argument("destinatario", nargs="?", default="destinatario@ejemplo.com")
    args = parser.parse_args()

    if args.local:
        return prueba_local(args.destinatario)
    return prueba_real(args.destinatario)


if __name__ == "__main__":
    raise SystemExit(main())
