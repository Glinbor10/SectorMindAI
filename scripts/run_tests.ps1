param(
	[string]$TestFile = "",
	[switch]$Verbose,
	[switch]$Coverage,
	[switch]$BackendOnly,
	[switch]$RasaOnly,
	[switch]$Integration
)

Write-Host "[TEST] Iniciando tests..." -ForegroundColor Cyan

if ($Integration) {
	Write-Host "[TEST] Modo: Tests de Integración con APIs Externas" -ForegroundColor Magenta
	Write-Host "[WARN] Estos tests requieren conexión a internet y pueden tardar ~30-40 segundos" -ForegroundColor Yellow
} else {
	Write-Host "[TEST] Modo: Tests Unitarios (sin integración)" -ForegroundColor Magenta
}

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
	if ($Integration) {
		# Ejecutar SOLO tests de integración con APIs externas
		Write-Host "[INFO] Ejecutando tests de integración (requieren internet)..." -ForegroundColor Yellow
		$pytestCmd = "python -m pytest backend/tests/ -m integration -v"
	} else {
		# Ejecutar tests normales (EXCLUYENDO integración)
		$pytestCmd = "python -m pytest backend/tests/ -m 'not integration' -v"
	}
	if ($TestFile) { $pytestCmd += " $TestFile" }
	$backendRes = Execute-FilteredTests -title "BACKEND" -command $pytestCmd -envVar "DATABASE_URL=$TEST_DB_URL"
}

if ($runRasa) {
	# Tests unitarios de acciones
	$rasaCmd = "python -m pytest rasa_model/tests/test_acciones.py -v --tb=short"
	$rasaRes = Execute-FilteredTests -title "RASA ACCIONES" -command $rasaCmd
	
	# Tests de stories deshabilitados (no son útiles para validar funcionalidad real)
	# # Tests de stories (conversaciones)
	# Write-Host "`n[RASA STORIES] Ejecutando tests de conversación..." -ForegroundColor Cyan
	# $storiesOutput = docker compose exec rasa rasa test --stories tests/test_stories.yml --out results/ 2>&1 | Out-String
	# ...
	# $rasaStoriesRes = @{ passed = $storiesPassed; failed = $storiesFailed; errors = 0 }
}

# ====== RESUMEN FINAL ======
Write-Host "`n========================================" -ForegroundColor Yellow
if ($Integration) {
	Write-Host "   REPORTE - TESTS DE INTEGRACION" -ForegroundColor Yellow
} else {
	Write-Host "         REPORTE DE RESULTADOS" -ForegroundColor Yellow
}
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
	Write-Host "`nRASA ACCIONES [$rStatus]:" -ForegroundColor Cyan
	Write-Host "  - Pasados: $($rasaRes.passed)" -ForegroundColor Green
	Write-Host "  - Fallados: $($rasaRes.failed)" -ForegroundColor Red
	if ($rasaRes.errors -gt 0) { Write-Host "  - Errores: $($rasaRes.errors)" -ForegroundColor Magenta }
}

# Tests de stories deshabilitados
# if ($null -ne $rasaStoriesRes) {
# 	$sStatus = if ($rasaStoriesRes.failed -eq 0 -and $rasaStoriesRes.errors -eq 0) { "OK" } else { "FAIL" }
# 	Write-Host "`nRASA STORIES [$sStatus]:" -ForegroundColor Cyan
# 	Write-Host "  - Pasados: $($rasaStoriesRes.passed)" -ForegroundColor Green
# 	Write-Host "  - Fallados: $($rasaStoriesRes.failed)" -ForegroundColor Red
# 	if ($rasaStoriesRes.errors -gt 0) { Write-Host "  - Errores: $($rasaStoriesRes.errors)" -ForegroundColor Magenta }
# }

Write-Host "`n----------------------------------------" -ForegroundColor Yellow
