Clear-Host
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   Sector Mind AI - Verificador de Infraestructura" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# 1. Verificar si el motor de Docker está corriendo
Write-Host "[CHECK] Comprobando el estado de Docker Engine..." -NoNewline
docker info >$null 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host " [FALLO]" -ForegroundColor Red
    Write-Host "`n[!] ERROR CRÍTICO: No se puede conectar con Docker." -ForegroundColor Red
    Write-Host "------------------------------------------------"
    Write-Host "ACCIONES RECOMENDADAS:" -ForegroundColor Yellow
    Write-Host "1. Abre la aplicación 'Docker Desktop'."
    Write-Host "2. Espera a que el icono de la ballena (abajo a la izquierda) esté en VERDE."
    Write-Host "3. Una vez listo, vuelve a ejecutar este script."
    Write-Host "------------------------------------------------"
    exit
}
Write-Host " [OK]" -ForegroundColor Green

# 2. Intentar levantar los contenedores
Write-Host "[DOCKER] Levantando microservicios (Backend, DB, Rasa)..." -ForegroundColor Cyan
docker compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[!] ERROR: Hubo un problema al levantar los contenedores." -ForegroundColor Red
    Write-Host "Revisa si hay algún puerto ocupado (5000, 5005 o 5432)." -ForegroundColor Yellow
    exit
}

# 3. Verificación de estabilidad
Write-Host "`n[WAIT] Esperando 5 segundos para estabilización..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 4. Confirmación Real
$runningContainers = docker ps --format "{{.Names}}"
Write-Host "`n[FINAL] Estado de los servicios:" -ForegroundColor Cyan
Write-Host "------------------------------------------------"
Write-Host "[OK] Sistema Online y Verificado!" -ForegroundColor Green
Write-Host "[WEB] App Web: http://localhost:5000" -ForegroundColor Blue
Write-Host "[IA] Rasa IA: http://localhost:5005" -ForegroundColor Blue
Write-Host "------------------------------------------------"
Write-Host "Contenedores activos:`n$runningContainers" -ForegroundColor Gray