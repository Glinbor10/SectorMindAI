# Scripts - SectorMindAI v1.0.0

Scripts PowerShell oficiales para operar la plataforma en Docker.

## Scripts disponibles

- `start_docker.ps1`:
  inicia todos los servicios de la plataforma.

- `stop_docker.ps1`:
  detiene la plataforma.

- `train_rasa.ps1`:
  entrena Rasa Model y Rasa Discovery.

- `run_tests.ps1`:
  ejecuta pruebas backend y Rasa en contenedores.

- `manage_db.ps1`:
  utilidades de base de datos.

## Ejemplos

```powershell
.\scripts\start_docker.ps1
.\scripts\run_tests.ps1
.\scripts\run_tests.ps1 -RasaOnly
.\scripts\train_rasa.ps1
.\scripts\stop_docker.ps1
```

## Estado de proyecto

Version: 1.0.0 estable.
Uso previsto de scripts: operacion y mantenimiento.
