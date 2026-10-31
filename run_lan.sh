#!/usr/bin/env bash
# run_lan.sh — Levanta Mi Botiquín Digital disponible en la red local (LAN).
# Uso:  ./run_lan.sh
set -e
cd "$(dirname "$0")"

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$IP" ] && IP=$(ipconfig getifaddr en0 2>/dev/null)
[ -z "$IP" ] && IP="127.0.0.1"

echo ""
echo "=== Mi Botiquín Digital — modo LAN ==="
echo "IP local detectada: $IP"
echo "URL de acceso:     http://$IP:8000"
echo "URL local:         http://localhost:8000"
echo ""
echo "Para detener el servidor: Ctrl+C"
echo ""

python manage.py runserver 0.0.0.0:8000