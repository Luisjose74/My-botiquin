# Ejecuta la sincronización de alertas de Mi Botiquín Digital.
#
# Uso manual (desde la carpeta del proyecto):
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\sincronizar_alertas.ps1
#
# Pensado para el Programador de tareas de Windows. Ver docs\automatizacion-windows.md.
# La salida se guarda en logs\sincronizar_alertas.log.

$ErrorActionPreference = "Continue"
$env:PYTHONUTF8 = "1"

$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz "venv\Scripts\python.exe"
$logDir = Join-Path $raiz "logs"
$log = Join-Path $logDir "sincronizar_alertas.log"

if (-not (Test-Path $python)) {
    Write-Error "No se encontró el entorno virtual en: $python"
    exit 1
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Set-Location $raiz

$marca = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$salida = & $python manage.py sincronizar_alertas 2>&1
$codigo = $LASTEXITCODE

$lineas = @("[$marca] exit=$codigo") + ($salida | ForEach-Object { "    $_" })
Add-Content -Path $log -Value $lineas -Encoding UTF8

exit $codigo
