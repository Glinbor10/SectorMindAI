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

function Get-DotEnvValue {
	param(
		[string]$EnvPath,
		[string]$Key
	)

	if (-not (Test-Path $EnvPath)) {
		return $null
	}

	foreach ($line in Get-Content $EnvPath) {
		$trimmed = $line.Trim()
		if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }

		$parts = $trimmed.Split("=", 2)
		if ($parts.Count -ne 2) { continue }

		if ($parts[0].Trim() -eq $Key) {
			return $parts[1].Trim()
		}
	}

	return $null
}

$envPath = Join-Path (Split-Path $PSScriptRoot -Parent) ".env"
$TEST_DB_URL = Get-DotEnvValue -EnvPath $envPath -Key "DATABASE_URL_TEST"
if (-not $TEST_DB_URL) {
	$TEST_DB_URL = "postgresql://sectormind:password@db:5432/sectormind_test_db"
}


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

	# Extraer métricas desde la línea de resumen de pytest
	$passedCount = 0
	$failedCount = 0
	$errorCount = 0

	$summaryLine = ($lines | Where-Object { $_ -match "=+.*(passed|failed|error|errors)" } | Select-Object -Last 1)
	if ($summaryLine) {
		if ($summaryLine -match "(\d+)\s+passed") { $passedCount = [int]$matches[1] }
		if ($summaryLine -match "(\d+)\s+failed") { $failedCount = [int]$matches[1] }
		if ($summaryLine -match "(\d+)\s+errors?") { $errorCount = [int]$matches[1] }
	}

	return @{ passed = $passedCount; failed = $failedCount; errors = $errorCount }
}

$selectedSuites = @()
if ($Integration) {
	$selectedSuites = @("integration")
} elseif ($BackendOnly) {
	$selectedSuites = @("backend")
} elseif ($RasaOnly) {
	$selectedSuites = @("rasa")
} else {
	$selectedSuites = @("backend", "integration", "rasa")
}

function Get-CoverageArgs {
	param(
		[string[]]$Suites,
		[bool]$IsFinalRun
	)

	if (-not $Coverage) {
		return ""
	}

	$targets = @()
	if ($Suites -contains "backend" -or $Suites -contains "integration") {
		$targets += "--cov=backend"
	}
	if ($Suites -contains "rasa") {
		$targets += "--cov=rasa_model/actions"
	}

	if ($targets.Count -eq 0) {
		return ""
	}

	$args = ($targets -join " ") + " --cov-append --cov-config=backend/.coveragerc"
	if ($IsFinalRun) {
		$args += " --cov-report=html --cov-report=term"
	} else {
		$args += " --cov-report=term"
	}

	return $args
}

if ($Coverage) {
	docker compose exec backend sh -c "rm -f .coverage"
}

# ====== EJECUCIÓN ======
$backendUnitRes = $null
$integrationRes = $null
$rasaRes = $null
$totalPassed = 0
$totalFailed = 0
$totalErrors = 0

for ($index = 0; $index -lt $selectedSuites.Count; $index++) {
	$suite = $selectedSuites[$index]
	$isFinalRun = ($index -eq $selectedSuites.Count - 1)
	$coverageArgs = Get-CoverageArgs -Suites $selectedSuites -IsFinalRun $isFinalRun

	switch ($suite) {
		"backend" {
			$pytestCmd = "python -m pytest backend/tests/ -m 'not integration' -v"
			if ($coverageArgs) { $pytestCmd += " $coverageArgs" }
			if ($TestFile) { $pytestCmd += " $TestFile" }
			$backendUnitRes = Execute-FilteredTests -title "BACKEND UNIT" -command $pytestCmd -envVar "DATABASE_URL=$TEST_DB_URL"
			$totalPassed += $backendUnitRes.passed
			$totalFailed += $backendUnitRes.failed
			$totalErrors += $backendUnitRes.errors
		}
		"integration" {
			Write-Host "[INFO] Ejecutando tests de integración (requieren internet)..." -ForegroundColor Yellow
			$pytestCmd = "python -m pytest backend/tests/ -m integration -v"
			if ($coverageArgs) { $pytestCmd += " $coverageArgs" }
			if ($TestFile) { $pytestCmd += " $TestFile" }
			$integrationRes = Execute-FilteredTests -title "BACKEND INTEGRATION" -command $pytestCmd -envVar "DATABASE_URL=$TEST_DB_URL"
			$totalPassed += $integrationRes.passed
			$totalFailed += $integrationRes.failed
			$totalErrors += $integrationRes.errors
		}
		"rasa" {
			$rasaCmd = "python -m pytest rasa_model/tests/test_acciones.py -v --tb=short"
			if ($coverageArgs) { $rasaCmd += " $coverageArgs" }
			$rasaRes = Execute-FilteredTests -title "RASA ACCIONES" -command $rasaCmd
			$totalPassed += $rasaRes.passed
			$totalFailed += $rasaRes.failed
			$totalErrors += $rasaRes.errors
		}
	}
}

# ====== RESUMEN FINAL ======
Write-Host "`n========================================" -ForegroundColor Yellow
if ($Integration) {
	Write-Host "   REPORTE - TESTS DE INTEGRACION" -ForegroundColor Yellow
} else {
	Write-Host "         REPORTE DE RESULTADOS" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Yellow

if ($null -ne $backendUnitRes) {
	$bStatus = if ($backendUnitRes.failed -eq 0 -and $backendUnitRes.errors -eq 0) { "OK" } else { "FAIL" }
	Write-Host "BACKEND UNIT [$bStatus]:" -ForegroundColor Cyan
	Write-Host "  - Pasados: $($backendUnitRes.passed)" -ForegroundColor Green
	Write-Host "  - Fallados: $($backendUnitRes.failed)" -ForegroundColor Red
	if ($backendUnitRes.errors -gt 0) { Write-Host "  - Errores: $($backendUnitRes.errors)" -ForegroundColor Magenta }
}

if ($null -ne $integrationRes) {
	$iStatus = if ($integrationRes.failed -eq 0 -and $integrationRes.errors -eq 0) { "OK" } else { "FAIL" }
	Write-Host "`nBACKEND INTEGRATION [$iStatus]:" -ForegroundColor Cyan
	Write-Host "  - Pasados: $($integrationRes.passed)" -ForegroundColor Green
	Write-Host "  - Fallados: $($integrationRes.failed)" -ForegroundColor Red
	if ($integrationRes.errors -gt 0) { Write-Host "  - Errores: $($integrationRes.errors)" -ForegroundColor Magenta }
}

if ($null -ne $rasaRes) {
	$rStatus = if ($rasaRes.failed -eq 0 -and $rasaRes.errors -eq 0) { "OK" } else { "FAIL" }
	Write-Host "`nRASA ACCIONES [$rStatus]:" -ForegroundColor Cyan
	Write-Host "  - Pasados: $($rasaRes.passed)" -ForegroundColor Green
	Write-Host "  - Fallados: $($rasaRes.failed)" -ForegroundColor Red
	if ($rasaRes.errors -gt 0) { Write-Host "  - Errores: $($rasaRes.errors)" -ForegroundColor Magenta }
}

if ($selectedSuites.Count -gt 1) {
	$overallStatus = if ($totalFailed -eq 0 -and $totalErrors -eq 0) { "OK" } else { "FAIL" }
	Write-Host "`nTOTAL [$overallStatus]:" -ForegroundColor Cyan
	Write-Host "  - Pasados: $totalPassed" -ForegroundColor Green
	Write-Host "  - Fallados: $totalFailed" -ForegroundColor Red
	if ($totalErrors -gt 0) { Write-Host "  - Errores: $totalErrors" -ForegroundColor Magenta }
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

if ($Coverage) {
	Write-Host "`n[COVERAGE] REPORTE DE COBERTURA:" -ForegroundColor Yellow
	$coverageLabel = if ($BackendOnly) { "Cobertura backend" } else { "Cobertura global" }
	$coverageHtmlPath = Join-Path (Split-Path $PSScriptRoot -Parent) "htmlcov/index.html"
	if (Test-Path $coverageHtmlPath) {
		$htmlContent = Get-Content $coverageHtmlPath -Raw
		$coverageMatch = [regex]::Match($htmlContent, '<span class="pc_cov">\s*([^<]+)\s*</span>')
		if ($coverageMatch.Success) {
			$coveragePct = $coverageMatch.Groups[1].Value.Trim()
			Write-Host ("   {0}: {1}" -f $coverageLabel, $coveragePct) -ForegroundColor Green
		}
	}
	Write-Host "   HTML Report generado en: htmlcov/index.html" -ForegroundColor Cyan
	Write-Host "   Abre el archivo en tu navegador para ver detalles." -ForegroundColor Gray
}

