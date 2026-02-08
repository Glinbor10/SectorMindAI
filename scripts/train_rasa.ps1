Write-Host "[RASA] Entrenando modelo principal (rasa_model)..."

docker compose exec -T rasa rasa train
if ($LASTEXITCODE -ne 0) {
    Write-Host "[RASA] Error entrenando rasa_model."
    exit $LASTEXITCODE
}

Write-Host "[RASA] Entrenando modelo discovery (rasa_discovery)..."

docker compose exec -T rasa-discovery rasa train
if ($LASTEXITCODE -ne 0) {
    Write-Host "[RASA] Error entrenando rasa_discovery."
    exit $LASTEXITCODE
}

Write-Host "[RASA] Entrenamiento completado en ambos modelos."
