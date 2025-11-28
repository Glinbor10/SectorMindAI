
# Historial de Cambios (Changelog)

Todas las modificaciones notables en el proyecto Sector Mind AI se documentarán en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/), y este proyecto se adhiere al versionado semántico.

## [v0.1.0] - 2025-11-28 (Versión Funcional / Prototipo)

### 🚀 Novedades (Added)

**Infraestructura Base:**

- Automatización de base de datos: Script `manage_db.py` para resetear y poblar tablas en un solo paso.
- Automatización de arranque: Script `start_services.bat` y tareas de VS Code (`tasks.json`) para ejecución simultánea de servicios.

**Backend (Flask API):**

- Servidor Flask configurado con soporte CORS para permitir peticiones locales.
- Modularización de rutas mediante Blueprints (auth, negocios, citas).

**Base de Datos SQLite Completa:**

- Tabla usuarios con roles (cliente/propietario) y contraseñas hasheadas.
- Tabla negocios vinculada a propietarios, con campos para foto_url, direccion y descripcion.
- Tablas relacionales para servicios, horarios_negocio y citas.
- Algoritmo de lógica de negocio (`logic.py`) para calcular disponibilidad en intervalos de 15 minutos.

**Frontend (Web Client):**

- Interfaz SPA simulada con HTML5 + Vanilla JS + Tailwind CSS.

**Home (index.html):**
- Buscador en tiempo real y filtrado por categoría.
- Sistema de Login/Registro modal con persistencia de sesión.
- Tarjetas de negocio interactivas (clicables).

**Detalle de Negocio (negocio.html):**
- Carga dinámica de información del negocio y propietario.
- Widget Chatbot: Asistente IA personalizado ("NombreNegocio AI"), protegido por login.
- Interfaz de Voz: Reconocimiento (STT) y síntesis (TTS) nativa del navegador.

**Inteligencia Artificial (Rasa):**
- Definición del dominio (`domain.yml`) con slots para negocio, servicio y fecha.
- Historias de reserva (`stories.yml`) y reglas de interacción básica.
- Custom Actions: Conexión con el backend para validación de entidades y consulta de disponibilidad real.

### 🔧 Cambios (Changed)

- Refactorización de Scripts: Se eliminaron `setup_db.py` y `poblar_db.py`, centralizando la gestión en `manage_db.py`.
- Mejora de UX: Eliminación de botones redundantes en el listado; navegación directa al hacer clic en la tarjeta del negocio.
- Seguridad: Los endpoints de la API ahora validan la integridad de los datos de entrada antes de escribir en la base de datos.

### 🐛 Correcciones (Fixed)

- Solucionado error crítico `YamlValidationException` en Rasa (falta de mappings en slots para Rasa 3.x).
- Solucionado error de importación de módulos (`ModuleNotFoundError`) al ejecutar el backend.
- Corregido bloqueo de seguridad (CORS) entre frontend y API.
- Solucionado error de contexto vacío al cargar el asistente en la página de detalle.

---

## [v0.0.1] - 2025-11-02 (Inicio del Proyecto)

### 🎉 Commit Inicial

- Definición del Proyecto: Planteamiento de la arquitectura para "Sector Mind AI".

- Estructura de Directorios: Creación del esqueleto desacoplado:
	- `backend/`: API y Lógica.
	- `frontend/`: Interfaz de usuario.
	- `database/`: Persistencia de datos.
	- `rasa_model/`: Motor conversacional.

- Configuración del Entorno:
	- Creación de entorno virtual Python (`.venv`).
	- Definición inicial de dependencias en `requirements.txt`.
	- Creación del `README.md` original.
