Write-Host "[RASA] Entrenando modelo principal (rasa_model)..."

docker compose exec -T rasa rasa train
if ($LASTEXITCODE -ne 0) {
    Write-Host "[RASA] Error entrenando rasa_model."
    exit $LASTEXITCODE
}

Write-Host "[RASA] Evaluando rasa_model mediante validación cruzada (k=5)..."

docker compose exec -T rasa rasa test nlu --cross-validation --folds 5
if ($LASTEXITCODE -ne 0) {
    Write-Host "[RASA] Warning: Error en evaluación de rasa_model (continuando)."
}

Write-Host "[RASA] Entrenando modelo discovery (rasa_discovery)..."

docker compose exec -T rasa-discovery rasa train
if ($LASTEXITCODE -ne 0) {
    Write-Host "[RASA] Error entrenando rasa_discovery."
    exit $LASTEXITCODE
}

Write-Host "[RASA] Evaluando rasa_discovery mediante validación cruzada (k=5)..."

docker compose exec -T rasa-discovery rasa test nlu --cross-validation --folds 5
if ($LASTEXITCODE -ne 0) {
    Write-Host "[RASA] Warning: Error en evaluación de rasa_discovery (continuando)."
}

Write-Host "[RASA] Entrenamiento y evaluación completados en ambos modelos."
Write-Host "[RASA] Revisa results/intent_report.json en ambas carpetas para métricas de validación cruzada."
