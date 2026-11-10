# run_lan.ps1 — Levanta Mi Botiquín Digital disponible en la red local (LAN).
# Uso:  .\run_lan.ps1
# Luego abre en el navegador del celular/otro PC:  http://<IP-de-esta-PC>:8000

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Detectar la IP local principal (IPv4, no loopback)
$ip = (Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -eq "Dhcp" } |
        Select-Object -First 1 -ExpandProperty IPAddress)
if (-not $ip) {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object { $_.IPAddress -notlike "127.*" } |
            Select-Object -First 1 -ExpandProperty IPAddress)
}
if (-not $ip) { $ip = "127.0.0.1" }

Write-Host ""
Write-Host "=== Mi Botiquín Digital — modo LAN (demostración) ===" -ForegroundColor Cyan
Write-Host "IP local detectada: $ip"
Write-Host "URL de acceso:     http://$ip`:8000"
Write-Host "URL local:         http://localhost:8000"
Write-Host ""
Write-Host "Modo demostración: se activa DJANGO_DEBUG=True para permitir el acceso" -ForegroundColor Yellow
Write-Host "desde la red local (la IP cambia y no puede fijarse en ALLOWED_HOSTS)." -ForegroundColor Yellow
Write-Host "Para una instalación real usa DJANGO_DEBUG=False con tu dominio y HTTPS." -ForegroundColor Yellow
Write-Host ""
Write-Host "Asegúrate de que el firewall permita el puerto 8000 (ver instrucciones abajo)."
Write-Host "Para detener el servidor: Ctrl+C"
Write-Host ""

# Verificar que el puerto 8000 esté libre
$enUso = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($enUso) {
    Write-Host "AVISO: el puerto 8000 ya está en uso. Cierra el proceso anterior o usa otro puerto." -ForegroundColor Yellow
}

# Abrir el firewall (requiere admin; si falla, se avisa)
try {
    New-NetFirewallRule -DisplayName "Mi Botiquin Digital 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -ErrorAction Stop | Out-Null
    Write-Host "Regla de firewall creada/verificada para el puerto 8000." -ForegroundColor Green
} catch {
    Write-Host "No se pudo crear la regla de firewall automáticamente (ejecuta como administrador si es necesario)." -ForegroundColor Yellow
}

# Modo demostración: permite el acceso desde cualquier IP de la red local
# (la IP puede cambiar y no puede fijarse en ALLOWED_HOSTS).
$env:DJANGO_DEBUG = "True"

python manage.py runserver 0.0.0.0:8000