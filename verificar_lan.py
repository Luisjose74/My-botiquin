"""Verifica que la app pueda exponerse en la red local (LAN).

Ejecutar:  python verificar_lan.py
Muestra la IP local y prueba que el puerto 8000 pueda abrirse.
"""
import socket

def ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def puerto_libre(puerto=8000):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", puerto))
        s.close()
        return True
    except OSError:
        return False

if __name__ == "__main__":
    ip = ip_local()
    print("IP local detectada:", ip)
    print("URL de acceso desde otro dispositivo:", "http://{}:8000".format(ip))
    if puerto_libre(8000):
        print("Puerto 8000: LIBRE (listo para iniciar el servidor).")
    else:
        print("Puerto 8000: EN USO. Cierra el proceso anterior o usa otro puerto.")
    print("")
    print("Pasos:")
    print("  1. Inicia el servidor:  python manage.py runserver 0.0.0.0:8000")
    print("     (o ejecuta run_lan.ps1 / run_lan.sh)")
    print("  2. Desde otro dispositivo en la misma red, abre http://{}:8000".format(ip))
    print("  3. Si no carga, revisa el firewall (Windows Defender / antivirus).")