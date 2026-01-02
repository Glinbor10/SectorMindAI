#!/bin/sh
# Entrypoint para backend

set -e

echo "🚀 Iniciando servidor Flask..."
exec python -m backend.app
