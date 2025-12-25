param(
	[string]$TestFile = "",
	[switch]$Verbose,
	[switch]$Coverage,
	[switch]$BackendOnly,
	[switch]$RasaOnly
)

Write-Host "[TEST] Iniciando tests..." -ForegroundColor Cyan

$TEST_DB_URL = "postgresql://sectormind:password@db:5432/sectormind_test_db"


# Validar si el contenedor está corriendo
$containerStatus = docker compose ps --format json | ConvertFrom-Json | Where-Object { $_.Service -eq "backend" }
if ($null -eq $containerStatus -or $containerStatus.State -ne "running") {
	Write-Host "[ERROR] El contenedor 'backend' no está activo." -ForegroundColor Red
	exit
}

# Restaurar la base de datos de tests antes de correr los tests del backend
Write-Host "[DB] Restaurando la base de datos de tests..." -ForegroundColor Yellow
docker compose exec backend python backend/manage_db.py $TEST_DB_URL
Write-Host "[DB] Base de datos de tests restaurada." -ForegroundColor Green

# Función para procesar y mostrar solo PASSED/FAILED y extraer totales
function Execute-FilteredTests {
	param($title, $command, $envVar = "")
    
	Write-Host "`n[$title] Ejecutando tests..." -ForegroundColor Cyan
    
	# Ejecutamos con -v para listar cada test individualmente
	$fullCmd = if ($envVar) { "export $envVar && $command" } else { $command }
	$output = docker compose exec backend sh -c "$fullCmd" 2>&1 | Out-String
    
	# Filtrar y mostrar solo líneas con PASSED o FAILED
	$lines = $output -split "`n"
	foreach ($line in $lines) {
		if ($line -match "PASSED") { Write-Host $line -ForegroundColor Green }
		if ($line -match "FAILED") { Write-Host $line -ForegroundColor Red }
	}

	# Extraer métricas para el resumen
	$passedCount = 0
	$failedCount = 0
	$errorCount = 0

	if ($output -match "(\d+) passed") { $passedCount = [int]$matches[1] }
	if ($output -match "(\d+) failed") { $failedCount = [int]$matches[1] }
	if ($output -match "(\d+) error")  { $errorCount  = [int]$matches[1] }

	return @{ passed = $passedCount; failed = $failedCount; errors = $errorCount }
}

$runBackend = $true
$runRasa = $true
if ($BackendOnly) { $runRasa = $false }
if ($RasaOnly) { $runBackend = $false }

# ====== EJECUCIÓN ======
$backendRes = $null
$rasaRes = $null

if ($runBackend) {
	$pytestCmd = "python -m pytest backend/tests/ -v"
	if ($TestFile) { $pytestCmd += " $TestFile" }
	$backendRes = Execute-FilteredTests -title "BACKEND" -command $pytestCmd -envVar "DATABASE_URL=$TEST_DB_URL"
}

if ($runRasa) {
	$rasaCmd = "python -m pytest rasa_model/tests/test_actions.py -v --tb=short"
	$rasaRes = Execute-FilteredTests -title "RASA" -command $rasaCmd
}

# ====== RESUMEN FINAL ======
Write-Host "`n========================================" -ForegroundColor Yellow
Write-Host "         REPORTE DE RESULTADOS" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

if ($null -ne $backendRes) {
	$bStatus = if ($backendRes.failed -eq 0 -and $backendRes.errors -eq 0) { "OK" } else { "FAIL" }
	Write-Host "BACKEND [$bStatus]:" -ForegroundColor Cyan
	Write-Host "  - Pasados: $($backendRes.passed)" -ForegroundColor Green
	Write-Host "  - Fallados: $($backendRes.failed)" -ForegroundColor Red
	if ($backendRes.errors -gt 0) { Write-Host "  - Errores: $($backendRes.errors)" -ForegroundColor Magenta }
}

if ($null -ne $rasaRes) {
	$rStatus = if ($rasaRes.failed -eq 0 -and $rasaRes.errors -eq 0) { "OK" } else { "FAIL" }
	Write-Host "`nRASA [$rStatus]:" -ForegroundColor Cyan
	Write-Host "  - Pasados: $($rasaRes.passed)" -ForegroundColor Green
	Write-Host "  - Fallados: $($rasaRes.failed)" -ForegroundColor Red
	if ($rasaRes.errors -gt 0) { Write-Host "  - Errores: $($rasaRes.errors)" -ForegroundColor Magenta }
}

Write-Host "`n----------------------------------------" -ForegroundColor Yellow
