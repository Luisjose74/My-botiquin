#!/usr/bin/env bash
# run_lan.sh — Levanta Mi Botiquín Digital disponible en la red local (LAN).
# Uso:  ./run_lan.sh
set -e
cd "$(dirname "$0")"

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$IP" ] && IP=$(ipconfig getifaddr en0 2>/dev/null)
[ -z "$IP" ] && IP="127.0.0.1"

echo ""
echo "=== Mi Botiquín Digital — modo LAN (demostración) ==="
echo "IP local detectada: $IP"
echo "URL de acceso:     http://$IP:8000"
echo "URL local:         http://localhost:8000"
echo "Sitio público:     http://$IP:8000/  (portada y guía educativa)"
echo "Panel de la app:   http://$IP:8000/app/  (requiere iniciar sesión)"
echo ""
echo "Modo demostración: se activa DJANGO_DEBUG=True para permitir el acceso"
echo "desde la red local (la IP cambia y no puede fijarse en ALLOWED_HOSTS)."
echo "Para una instalación real usa DJANGO_DEBUG=False con tu dominio y HTTPS."
echo ""
echo "Para detener el servidor: Ctrl+C"
echo ""

# Modo demostración: permite el acceso desde cualquier IP de la red local.
export DJANGO_DEBUG=True

python manage.py runserver 0.0.0.0:8000