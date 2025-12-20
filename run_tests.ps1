param(
    [string]$TestFile = "",
    [switch]$Verbose,
    [switch]$Coverage,
    [switch]$BackendOnly,
    [switch]$RasaOnly
)

Write-Host "[TEST] Iniciando tests (Configuración automática)..." -ForegroundColor Cyan

# Definimos la URL de la base de datos de tests aquí 
# Esto evita que tengas que cambiar el .env manualmente.
$TEST_DB_URL = "postgresql://sectormind:password@db:5432/sectormind_db"

# Comprobar si el contenedor está corriendo
$containerStatus = docker compose ps --format json | ConvertFrom-Json | Where-Object { $_.Service -eq "backend" }
if ($null -eq $containerStatus -or $containerStatus.State -ne "running") {
    Write-Host "[ERROR] El contenedor 'backend' no está activo. Pulsa START." -ForegroundColor Red
    exit
}

# Determinar qué tests ejecutar
$runBackend = $true
$runRasa = $true

if ($BackendOnly) { $runRasa = $false }
if ($RasaOnly) { $runBackend = $false }

# ====== TESTS DEL BACKEND ======
if ($runBackend) {
    Write-Host "`n[BACKEND] Ejecutando tests del backend..." -ForegroundColor Cyan
    
    $pytestCmd = "python -m pytest backend/tests/"
    if ($TestFile) { $pytestCmd += $TestFile }
    if ($Verbose)  { $pytestCmd += " -v" }
    if ($Coverage) { $pytestCmd += " --cov=backend --cov-report=html --cov-report=term" }
    
    $backendOutput = docker compose exec -e DATABASE_URL=$TEST_DB_URL backend sh -c "$pytestCmd" 2>&1 | Out-String
    $backendExitCode = $LASTEXITCODE
    $backendOutput | Write-Host
    
    # Extraer número de tests pasados
    if ($backendOutput -match "(\d+) passed") {
        $backendCount = [int]$matches[1]
    } else {
        $backendCount = 0
    }
}

# ====== TESTS DE RASA ======
if ($runRasa) {
    Write-Host "`n[RASA] Ejecutando tests de Rasa (60+ tests)..." -ForegroundColor Cyan
    
    # Los tests de Rasa están en rasa_model/tests/test_actions.py
    # Se ejecutan desde el backend container que tiene acceso al volumen completo
    $rasaCmd = "python -m pytest rasa_model/tests/test_actions.py -v --tb=short"
    if ($Coverage) { $rasaCmd += " --cov=rasa_model --cov-report=html" }
    
    $rasaOutput = docker compose exec backend sh -c "$rasaCmd" 2>&1 | Out-String
    $rasaExitCode = $LASTEXITCODE
    $rasaOutput | Write-Host
    
    # Extraer número de tests pasados
    if ($rasaOutput -match "(\d+) passed") {
        $rasaCount = [int]$matches[1]
    } else {
        $rasaCount = 0
    }
}

# Resumen final
Write-Host "`n[SUMMARY] Resumen de tests:" -ForegroundColor Yellow
if ($runBackend) {
    $backendStatus = if ($backendExitCode -eq 0) { "[OK]" } else { "[FAIL]" }
    Write-Host "$backendStatus Backend: $backendCount tests passed" -ForegroundColor $(if ($backendExitCode -eq 0) { "Green" } else { "Red" })
}
if ($runRasa) {
    $rasaStatus = if ($rasaExitCode -eq 0) { "[OK]" } else { "[FAIL]" }
    Write-Host "$rasaStatus Rasa: $rasaCount tests passed" -ForegroundColor $(if ($rasaExitCode -eq 0) { "Green" } else { "Red" })
}

if ($runBackend -and $runRasa) {
    $totalTests = $backendCount + $rasaCount
    $allPassed = ($backendExitCode -eq 0) -and ($rasaExitCode -eq 0)
    $totalStatus = if ($allPassed) { "[OK]" } else { "[FAIL]" }
    Write-Host "$totalStatus Total: $totalTests tests passed" -ForegroundColor $(if ($allPassed) { "Green" } else { "Red" })
}

Write-Host "[OK] Proceso finalizado." -ForegroundColor Green