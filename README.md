# SectorMindAI

Plataforma para gestión de negocios y reservas con API REST (Flask), asistentes conversacionales (Rasa) y despliegue en Docker.

## Resumen

SectorMindAI es una plataforma full-stack diseñada para modernizar y democratizar la gestión de reservas en pymes del sector servicios. Sus objetivos principales son:

- Democratizar el acceso a la Inteligencia Artificial para negocios pequeños y sus clientes.
- Mejorar la inclusión digital: permitir reservas y consultas por lenguaje natural (texto y voz).
- Facilitar la operación diaria de negocios reduciendo la fricción tecnológica.

La plataforma combina:
- Backend en Python/Flask que expone APIs para negocios, usuarios y citas.
- Modelos y acciones Rasa para asistentes conversacionales (rasa_model y rasa_discovery).
- Base de datos PostgreSQL para persistencia.
- Frontend estático (HTML/JS) servido por el backend.
- Contenedores Docker y scripts PowerShell para facilitar arranque y pruebas.

El repositorio incluye datos de ejemplo y utilidades para levantar un entorno de desarrollo y ejecutar pruebas automatizadas.

## Demostración en Video

Puedes ver una demostración de la aplicación en el siguiente video:

[Ver video de demostración](https://drive.google.com/file/d/1EqFygkhmut2kG2bySK1g0IpKr9qihfvy/view?usp=sharing)

## Contenido / Estructura

- `backend/` : Código del servidor Flask, gestión de base de datos y tests.
- `frontend/` : HTML, JS y recursos estáticos de la interfaz.
- `rasa_model/` y `rasa_discovery/` : proyectos Rasa (modelos, acciones, Dockerfiles).
- `database/` : esquemas SQL (schema_postgres.sql).
- `scripts/` : scripts PowerShell para operaciones comunes (arranque, paro, tests, training).
- `docker-compose.yml` : definición de servicios (db, backend, rasa, actions).
- `requirements.txt` : dependencias Python utilizadas por el proyecto.

## Requisitos

- Docker y Docker Compose
- Git

## Rápido: arranque con Docker (recomendado)

En Windows PowerShell (desde la raíz del repo):

```powershell
.\scripts\start_docker.ps1
```

Esto levanta los contenedores definidos en `docker-compose.yml`: PostgreSQL, backend Flask, Rasa (y sus actions).

Para detener todo:

```powershell
.\scripts\stop_docker.ps1
```

Si prefieres usar Docker Compose directo (bash/mac/linux):

```bash
docker compose up -d
docker compose down
```

## Desarrollo y ejecución local del backend (sin Docker)

1. Crear y activar un entorno virtual.
2. Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

3. Definir variables de entorno en un archivo `.env` (ver `docker-compose.yml` para nombres de variables esperadas).
4. Ejecutar el servidor:

```bash
python -m backend.app
```

El backend sirve la carpeta `frontend/` y expone las rutas API bajo `/`.

## Base de datos

- `backend/manage_db.py` es el script maestro para crear/asegurar la base de datos y poblarla con datos de ejemplo.
- Los contenedores usan una base de datos principal y una base de tests separada (`sectormind_db` y `sectormind_test_db`).

Ejemplo para restaurar la DB de tests (el script `run_tests.ps1` ya lo hace automáticamente antes de ejecutar tests):

```powershell
# desde el host (usa docker-compose para ejecutar el script dentro del container):
docker compose exec -T backend python backend/manage_db.py postgresql://user:pass@db:5432/sectormind_test_db
```

## Pruebas (tests)

Hay un script centralizado para ejecutar las pruebas:

```powershell
.\scripts\run_tests.ps1
```

Opciones útiles:
- `-BackendOnly` : ejecutar solo tests del backend.
- `-RasaOnly` : ejecutar solo tests de Rasa/acciones.
- `-Integration` : ejecutar tests marcados como integración (requieren red/internet).
- `-Coverage` : generar reporte de cobertura (HTML en `htmlcov/index.html`).

El script hace lo siguiente antes de ejecutar tests del backend:
- Verifica que el contenedor `backend` esté corriendo.
- Restaura la base de datos de tests con `backend/manage_db.py`.

## Entrenamiento de Rasa

Para entrenar los modelos Rasa incluidos hay un script:

```powershell
.\scripts\train_rasa.ps1
```

Revisa `rasa_model/` y `rasa_discovery/` para detalles de dominio, historias y acciones.

## Docker

El `docker-compose.yml` levanta los servicios necesarios:
- `db` (Postgres)
- `backend` (Flask)
- `rasa`, `rasa-actions`, `rasa-discovery` y sus `actions`.

Variables clave se pasan vía `.env` (usuario, password, DATABASE_URL, API_URL, etc.).

## Contribuir

- Clona el repositorio.
- Crea una rama por feature/bug: `git checkout -b feat/nombre`.
- Añade tests para cambios en lógica o nuevas features.
- Abre Pull Request con descripción clara hacia `trunk`.

## Recursos y archivos importantes

- Scripts: `scripts/start_docker.ps1`, `scripts/stop_docker.ps1`, `scripts/run_tests.ps1`, `scripts/train_rasa.ps1`.
- Backend: `backend/app.py`, `backend/manage_db.py`, `backend/db.py`, `backend/logic.py`.
- Docker compose: `docker-compose.yml`.

## Licencia

Este proyecto está bajo una licencia de uso no comercial con atribución. Consulta el archivo `LICENSE` para el texto completo.

Resumen: permiso para usar, modificar y distribuir con fines no comerciales, siempre que se reconozca la autoría a Glinbor10 (Guillermo Linares Borrego). El uso comercial está prohibido sin permiso expreso del autor.

---

