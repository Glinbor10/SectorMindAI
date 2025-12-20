#!/usr/bin/env pwsh

Write-Host "[STOP] Deteniendo Docker Compose..." -ForegroundColor Yellow

docker compose down

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Docker Compose detenido exitosamente." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Fallo al detener Docker Compose." -ForegroundColor Red
    exit 1
}
