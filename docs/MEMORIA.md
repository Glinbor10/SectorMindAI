# Memoria Tecnica - SectorMindAI v1.0.0

## Resumen ejecutivo
SectorMindAI es una plataforma de reservas con arquitectura de microservicios y asistentes conversacionales duales.

Estado de producto:
- Version: 1.0.0
- Estado: estable
- Politica: mantenimiento correctivo (sin nuevas features funcionales)

## Arquitectura

Componentes:
- Frontend web (`frontend/`)
- Backend Flask (`backend/`)
- PostgreSQL (`db` en Docker Compose)
- Rasa Model + Rasa Actions
- Rasa Discovery + Rasa Discovery Actions

Comunicacion:
- Todo corre en Docker Compose sobre red `sector_mind_net`.
- Los action servers consumen API backend para operaciones de negocio.

## Capacidades principales

- Busqueda de negocios por proximidad (Discovery)
- Reserva, cambio, cancelacion y consulta de citas (Model)
- Geolocalizacion con Nominatim y orden por distancia (Haversine)
- Interfaz por rol (cliente / propietario)
- Testing automatizado en Docker

## Operacion

Scripts oficiales:
- `scripts/start_docker.ps1`
- `scripts/stop_docker.ps1`
- `scripts/train_rasa.ps1`
- `scripts/run_tests.ps1`

## Calidad y pruebas

La validacion se ejecuta dentro de contenedores para asegurar paridad de entorno.

Suite principal:
- backend/tests
- rasa_model/tests/test_acciones.py
- rasa_model/tests/test_llm_fallback_actions.py (si aplica en la rama actual)

## Cierre de ciclo funcional

Con v1.0.0 se considera completada la linea funcional principal.
Cambios permitidos desde este punto:
- correcciones de errores
- seguridad
- estabilidad
- mantenimiento tecnico

No se planifican nuevas funcionalidades de producto en esta linea.

## Fecha de actualizacion

2026-03-21
