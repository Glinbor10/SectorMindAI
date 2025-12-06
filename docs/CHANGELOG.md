# Historial de Cambios (Changelog)

Todas las modificaciones notables en el proyecto Sector Mind AI se documentarán en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/), y este proyecto se adhiere al versionado semántico.

## [v0.3.0] - 2025-12-06 (Calidad y Testing Comprehensivo)

### 🧪 Testing & Calidad (Added)
- **Suite de Testing Completa:** 123 tests automatizados organizados en 6 módulos
  - `test_logic.py`: 20 tests para algoritmos de disponibilidad (92% coverage)
  - `test_citas.py`: 21 tests para sistema de reservas (92% coverage)
  - `test_auth.py`: 21 tests para autenticación y seguridad (98% coverage)
  - `test_negocios.py`: 23 tests para gestión de negocios (92% coverage)
  - `test_usuarios.py`: 19 tests para perfiles y uploads (93% coverage)
  - `test_actions.py`: 17 tests para Rasa actions con mocking (50% coverage)
- **Coverage Global: 82%** (Backend: 92%, Rasa: 50%)
- **Aislamiento de Tests:** Sistema de BD temporales con `tempfile.mkstemp()` para cada test
- **Carpeta Temporal de Uploads:** Tests de file uploads ahora usan carpeta temporal con cleanup automático
- **Mocking de APIs:** `unittest.mock` para simular llamadas HTTP en tests de Rasa sin dependencias externas
- **Reportes HTML:** Generación automática de reportes de coverage en `htmlcov/`
- **Configuración pytest:** `pytest.ini` con testpaths y configuración de coverage

### 🚀 Funcionalidades IA (Added - Completado en versión anterior)
- **Reservas Automáticas End-to-End:** El agente de IA completa reservas reales en la base de datos sin intervención manual
- **Detección Inteligente de Servicios:** Matching fuzzy para entender variaciones del usuario
- **Consulta de Disponibilidad en Tiempo Real:** Action que muestra horarios libres de los próximos 7-14 días
- **Interpretación de Fechas en Lenguaje Natural:** Procesamiento de "mañana", "hoy", "el lunes", "pasado mañana"
- **7 Custom Actions de Rasa:**
  - `action_set_contexto`, `action_normalizar_servicio`, `action_mostrar_disponibilidad`
  - `action_reservar_cita`, `action_info_negocio`, `action_cancelar_cita`
  - `action_responder_bot_challenge`
- **Renderizado de Markdown en Chat:** Soporte para texto en **negrita**, *cursiva* y saltos de línea

### 🔧 Cambios (Changed)
- **Backend Routes:** Refactorización para soportar `current_app.config['UPLOAD_FOLDER']` en tests
  - `auth.py` y `usuarios.py` ahora detectan modo testing automáticamente
- **Test Fixtures:** Todos los fixtures ahora incluyen cleanup automático con `shutil.rmtree()`
- **Documentación:** README y MEMORIA actualizados con secciones de testing y comandos
- **Endpoint `/citas` POST:** Agregado `tipo_negocio` con valor por defecto 'general' para cumplir schema

### 🐛 Correcciones (Fixed)
- **Bug 404 en PUT `/usuarios/<id>`:** Ahora valida `rowcount` y devuelve 404 si usuario no existe
- **Bug INSERT negocios:** Agregado campo `tipo_negocio` obligatorio que faltaba en el INSERT
- **Conflicto de Archivos:** Tests de file upload ya no contaminan `frontend/uploads/` de producción
- **Imports Faltantes:** Agregado `timedelta` en `test_actions.py`
- **Slot 'fecha' en Tests:** Corregido uso de slots en lugar de entity_values en tests de Rasa

---

## [v0.2.0] - 2025-11-29 (Mejoras UX, Voz y Multimedia)

### 🚀 Novedades (Added)
- **Agente IA Multimodal:** Implementación de reconocimiento de voz (Speech-to-Text) y síntesis de voz (Text-to-Speech) mediante Web Speech API en la vista de negocio.
- **Sistema de Archivos:** Soporte para subida física de imágenes de perfil (`multipart/form-data`) con almacenamiento en carpeta local `frontend/uploads`.
- **UX Avanzada:** Integración de **SweetAlert2** para notificaciones visuales modernas en lugar de alertas nativas.
- **Control de Acceso:** Pantalla de bloqueo ("Lock Screen") sobre el agente de IA que obliga a iniciar sesión para interactuar.
- **Navbar Unificado:** Diseño consistente de la barra de navegación en todas las vistas, mostrando avatar y menú de usuario.
- **Auto-Login:** Al registrarse, el usuario inicia sesión automáticamente.

### 🔧 Cambios (Changed)
- **Script `manage_db.py`:** Reescrito totalmente. Ahora limpia la carpeta `uploads`, reinicia la DB y crea usuarios con emails válidos y fotos de demostración.
- **Persistencia de Navegación:** Corregido el flujo de selección de negocio. Ahora se guarda correctamente el negocio seleccionado en `localStorage` al hacer clic.
- **Gestión de Errores API:** Mejorado el manejo de errores HTTP 404 y 500 en los endpoints de usuarios.

### 🐛 Correcciones (Fixed)
- Solucionado error `500 Internal Server Error` cuando se intentaba actualizar un usuario inexistente (ahora devuelve 404).
- Corregida la validación de emails en el script de población de datos (se usan emails con formato válido `user@domain.com`).

---

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