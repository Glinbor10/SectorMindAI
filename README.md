# Sector Mind AI (v1.0.0)

Plataforma de reservas inteligente con arquitectura de microservicios en Docker Compose, backend Flask + PostgreSQL y asistentes Rasa duales (Discovery + Model).

## Estado actual

Version actual: v1.0.0 (estable)

Politica de cambios:
- No hay nuevas features planificadas en esta linea.
- Solo se aplicaran correcciones de errores, estabilidad y mantenimiento.

## Arquitectura en produccion

Servicios activos en docker-compose:
- backend (5000)
- db postgres (5432)
- rasa model (5005)
- rasa actions (5055)
- rasa discovery (5006)
- rasa discovery actions (5056)

Red interna:
- sector_mind_net

Persistencia:
- volumen postgres_data para base de datos

## Flujo funcional

- Home (`frontend/index.html`): chat discovery para encontrar negocios cercanos.
- Detalle (`frontend/detalle.html`): chat model para reservar, cambiar, cancelar y consultar citas del negocio seleccionado.
- Backend: API REST + logica de negocio + auth.
- PostgreSQL: persistencia principal.

## Comandos de trabajo

Inicio:
```powershell
.\scripts\start_docker.ps1
```

Parada:
```powershell
.\scripts\stop_docker.ps1
```

Entrenamiento Rasa:
```powershell
.\scripts\train_rasa.ps1
```

Tests:
```powershell
.\scripts\run_tests.ps1
.\scripts\run_tests.ps1 -BackendOnly
.\scripts\run_tests.ps1 -RasaOnly
.\scripts\run_tests.ps1 -Integration
.\scripts\run_tests.ps1 -Coverage
```

## Testing

`run_tests.ps1` ejecuta:
- Backend tests (`backend/tests`)
- Rasa actions core (`rasa_model/tests/test_acciones.py`)
- Rasa LLM fallback tests (`rasa_model/tests/test_llm_fallback_actions.py`), si existen en la base actual

Nota:
- El script corre dentro de contenedores Docker.
- No requiere entorno virtual local.

## Estructura principal

```text
backend/
frontend/
rasa_model/
rasa_discovery/
docs/
scripts/
docker-compose.yml
README.md
```

## Credenciales de prueba

Propietario:
- email: propietario@sectormind.com
- password: p

Cliente:
- email: cliente@sectormind.com
- password: u

## Versionado y documentacion

- Changelog: docs/CHANGELOG.md
- Arquitectura Rasa: docs/RASA.md
- Memoria tecnica: docs/MEMORIA.md
- Geolocalizacion: docs/GEOLOCALIZACION.md

Ultima actualizacion documental: 2026-03-21
