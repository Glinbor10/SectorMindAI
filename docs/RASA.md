# Arquitectura Rasa - SectorMindAI v1.0.0

## Resumen
SectorMindAI opera con dos asistentes Rasa separados, cada uno con su action server dedicado.

- Rasa Discovery: puerto 5006
- Rasa Discovery Actions: puerto 5056
- Rasa Model: puerto 5005
- Rasa Actions: puerto 5055

Objetivo de separacion:
- Discovery: encontrar negocio por ubicacion/tipo
- Model: gestionar reserva en negocio concreto

## Discovery

Directorio: `rasa_discovery/`

Responsabilidad:
- interpretar consulta de busqueda
- usar geolocalizacion del usuario
- listar opciones cercanas
- redirigir a detalle de negocio

Punto de entrada frontend:
- `frontend/index.html`

## Model

Directorio: `rasa_model/`

Responsabilidad:
- reservar cita
- cambiar horario
- cancelar cita
- consultar citas y datos del negocio

Punto de entrada frontend:
- `frontend/detalle.html`

## Integracion con backend

Ambos action servers llaman al backend Flask para:
- negocios
- servicios
- citas
- usuarios

Backend: `http://backend:5000`

## Entrenamiento y ejecucion

Entrenar modelos:
```bash
docker compose run --rm rasa rasa train
docker compose run --rm rasa-discovery rasa train
```

Iniciar plataforma completa:
```powershell
.\scripts\start_docker.ps1
```

## Testing relacionado

- `rasa_model/tests/test_acciones.py`
- `rasa_model/tests/test_llm_fallback_actions.py` (si esta presente en la rama actual)

Ejecucion:
```powershell
.\scripts\run_tests.ps1 -RasaOnly
```

## Estado de producto

Version: 1.0.0 estable.
Desde este punto, los cambios en Rasa son solo correctivos o de estabilidad.
