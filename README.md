# Sector Mind AI

Introducción
------------
Sector Mind AI es una plataforma para gestionar reservas y citas(para clientes y propietarios) mediante asistentes conversacionales basados en Rasa y una API en Python.

Estructura
----------
- `backend/` — API en Python (Flask).
- `frontend/` — cliente (HTML/CSS/JS).
- `database/` — `schema.sql` y base de datos SQLite.
- `rasa_models/` — modelos Rasa.

Si clonas este repositorio
--------------------------
1. Asegúrate de tener Python 3.10+ instalado (se recomienda 3.10 para compatibilidad).

2. Crear y activar un entorno virtual en PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Actualizar pip e instalar dependencias:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

4. (Opcional) Crear la base de datos SQLite desde el schema (PowerShell):

```powershell
Get-Content database\schema.sql | .\sqlite3 database\tfg_data.db
```

Eso es todo: con el entorno activado y las dependencias instaladas, puedes ejecutar el backend desde `backend/` según su punto de entrada.

Nota rápida
----------
Si ya tienes un entorno distinto (por ejemplo `tfg_venv/`), puedes activarlo en lugar de crear `.venv`.

Licencia y contribuciones
-------------------------
Si deseas que añada una sección de contribución o una licencia (por ejemplo MIT), dímelo y la incluyo.
