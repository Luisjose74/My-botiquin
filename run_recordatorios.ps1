# run_recordatorios.ps1 — Dispara los recordatorios de toma cada minuto.
# Uso: .\run_recordatorios.ps1   (dejar corriendo en una ventana aparte)
# En producción usa el Programador de tareas de Windows (ver README).
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
Write-Host "Disparando recordatorios cada 60s. Ctrl+C para detener." -ForegroundColor Cyan
while ($true) {
    $ahora = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ahora] Ejecutando enviar_recordatorios_hora..."
    python manage.py enviar_recordatorios_hora
    Start-Sleep -Seconds 60
}