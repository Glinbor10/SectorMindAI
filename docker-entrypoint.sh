#!/bin/sh
# Entrypoint para backend - Ejecuta preparación de BD antes de iniciar Flask

set -e

echo "🔄 Ejecutando preparación de base de datos..."
python -m backend.manage_db

echo "🚀 Iniciando servidor Flask..."
exec python -m backend.app
