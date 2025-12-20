Write-Host "[START] Iniciando infraestructura Docker de SectorMindAI..." -ForegroundColor Cyan

# Levantar contenedores
docker compose up -d --build

Write-Host "`n[WAIT] Esperando 5 segundos a que los servicios se estabilicen..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "`n[OK] Sistema Online!" -ForegroundColor Green
Write-Host "------------------------------------------------"
Write-Host "[WEB] App Web: http://localhost:5000" -ForegroundColor Blue
Write-Host "[IA] Rasa IA: http://localhost:5005" -ForegroundColor Blue
Write-Host "------------------------------------------------"
Write-Host "[TIP] Sugerencia: Usa 'docker compose logs -f' para ver errores."