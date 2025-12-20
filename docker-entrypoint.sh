#!/bin/sh
# Entrypoint para backend - Ejecuta migraciones antes de iniciar Flask

set -e

echo "🔄 Ejecutando migraciones de base de datos..."
python -m backend.migrations.migrate

echo "🚀 Iniciando servidor Flask..."
exec python -m backend.app
