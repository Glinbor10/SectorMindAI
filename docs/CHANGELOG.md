# Historial de Cambios (Changelog)

Todas las modificaciones notables en el proyecto Sector Mind AI se documentarán en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/), y este proyecto se adhiere al versionado semántico.


## [v0.5.0] - Desde el 20/12/2025 hasta la actualidad (Refactorización Rasa y Flujo Propietario)


### ✨ Añadido (Added)

**Refactorización Backend y DevOps:**
- Ahora existen dos bases de datos independientes: una principal (`sectormind_db`) y otra exclusiva para tests (`sectormind_test_db`). Esto permite ejecutar tests sin afectar los datos reales.
- La base de datos de producción en Docker ahora persiste los datos correctamente entre reinicios de contenedores, gracias al volumen `sector_mind_postgres_data`.
- Eliminado el borrado y repoblamiento automático de la base de datos al arrancar el backend: ahora los datos solo se restauran manualmente si se ejecuta el script correspondiente.
- Eliminación completa de `db_utils.py` y de la función `adapt_query` en todo el backend. Todas las rutas y lógica ahora usan queries PostgreSQL directas con `%s`.
- Refactorización de `logic.py`, `routes/auth.py`, `routes/citas.py` y `routes/negocios.py` para eliminar dependencias de SQLite y adaptar queries a PostgreSQL.
- Centralización de todos los scripts PowerShell (`start_docker.ps1`, `stop_docker.ps1`, `run_tests.ps1`, `manage_db.ps1`) en la carpeta `scripts/` y actualización de todas las referencias en VS Code (Action Buttons y tasks.json).
- Mejora de los scripts para que funcionen correctamente desde la raíz del proyecto, eliminando rutas relativas innecesarias.
- Eliminación de scripts y archivos obsoletos relacionados con SQLite y migraciones antiguas.
- Añadido botón de Action Button y tarea de VS Code para ejecutar `manage_db.py` vía Docker.
- Mejora del script de tests (`run_tests.ps1`) para mostrar de forma clara los tests pasados y fallidos tanto de backend como de Rasa.

**Flujo Propietario y Refactorización Rasa:**
- Flujo de trabajo completo como propietario: gestión de negocios, servicios y clientes desde la plataforma.
- Corrección de bugs detectados en producción.
- Refactorización inicial de Rasa para eliminar deuda técnica y unificar la lógica de gestión de citas.
- Rasa ahora usa un sistema general para la gestión de citas de todos los negocios, usando metadatos para identificar el negocio y el usuario en cada interacción.
- Respuestas contextuales de urgencias según tipo de negocio (dentista, peluquería, fisioterapia), evitando solapamientos y malentendidos.
- Identificación de intenciones de reserva y consulta usando FuzzyWuzzy para tolerancia a errores ortográficos en los servicios.
- Eliminación de duplicidad y repetición de código en acciones de Rasa.
- Mejor comprensión del modelo y reducción de malentendidos.

### 🔧 Cambiado (Changed)

- Refactorización de las acciones de Rasa para centralizar la gestión de citas y urgencias.
- Uso de metadatos en los mensajes para mantener el contexto de negocio y usuario.
- Mejoras en la experiencia de usuario para propietarios y clientes.

### 🐛 Corregido (Fixed)

- Bugs en la gestión de citas y servicios detectados en el desarrollo.
- Solapamiento de respuestas de urgencias y repetición de código en Rasa.

---

## [v0.4.0] - 2025-12-20 (Profesionalización con Docker y PostgreSQL)

### ✨ Añadido (Added)

**Orquestación Profesional:**
- **Docker Compose:** Sistema de 4 microservicios completamente containerizado
  - `backend`: Flask API en contenedor con volumen de rasa_model
  - `postgres`: PostgreSQL 15-Alpine con persistencia garantizada
  - `rasa`: Motor de diálogo Rasa 3.6.13
  - `rasa-actions`: Servidor de acciones personalizadas
- **Red Docker Interna:** Comunicación segura entre servicios en red privada `sector_mind_net`
- **Volúmenes Persistentes:** 
  - Base de datos PostgreSQL (volumen named)
  - Modelo Rasa (volumen bind mount)

**Infraestructura y DevOps:**
- **Action Buttons en VS Code:** Interfaz gráfica para operaciones comunes
  - 🚀 `INICIAR TODO SECTOR MIND` - Levanta stack completo
  - 🛑 `STOP DOCKER` - Detiene e elimina contenedores
  - 🧪 `TESTS` - Ejecuta suite unificada de tests
- **Scripts PowerShell Profesionales:**
  - `start_docker.ps1` - Manejo robusto de errores, esperas inteligentes
  - `stop_docker.ps1` - Limpieza completa de contenedores
  - `run_tests.ps1` - Ejecución flexible con flags (-BackendOnly, -RasaOnly, -Coverage)
- **CI/CD Ready:** Dockerfile optimizado con multi-stage build, setuptools/wheel preinstalados

**Base de Datos:**
- **Migración PostgreSQL 100%:** Sustitución completa de SQLite
  - Transacciones ACID garantizadas
  - RealDictCursor para resultados dict-like
  - Preparación para escalabilidad horizontal
- **Schema Mejorado:** 7 tablas relacionales normalizadas con constraints integrity
- **manage_db.py Refactorizado:** Adaptado exclusivamente a PostgreSQL

**Testing e Integración:**
- **Suite Unificada:** 104 tests (75 backend + 29 Rasa) con ejecución centralizada
  - Backend: 100% cobertura en rutas críticas
  - Rasa: Tests parametrizados con mocking de APIs
  - Fechas dinámicas en tests para evitar fallos temporales
- **Ejecución desde Docker:** Tests se ejecutan dentro del contenedor backend
- **Resumen de Tests Mejorado:** Salida con conteo de tests pasados vs. exit codes

**Frontend:**
- **Fotos de Negocios Reales:** URLs actualizadas a Unsplash/Pexels con verificación manual
- **Credenciales Simplificadas:** Contraseñas cortas (p, c) para pruebas rápidas

### 🔧 Cambiado (Changed)

**Backend:**
- **Eliminación Total de SQLite:** Cero imports de sqlite3 en codebase
  - `db.py` - Usa psycopg2 exclusivamente
  - `db_utils.py` - Adaptación de queries de '?' a '%s'
  - Todas las rutas - Usan PostgreSQL con RETURNING id

**Tests:**
- **Fixtures Dinámicos:** `logic_test_data` ahora genera cliente_id en runtime
- **Gestión de Errores HTTP:** Status codes corregidos (409 para conflictos de horario)
- **Fecha Dinámica Rasa:** `test_cancelar_cita_lista_citas` usa datetime.now() + timedelta

**Dependencias:**
- **requirements.txt Pinned:** Versiones exactas para reproducibilidad
  - Flask==3.0.0
  - psycopg2-binary==2.9.9
  - rasa==3.6.13
  - pytest==7.4.3

**Documentación:**
- **README Restructurado:** Secciones de Arquitectura, Uso Rápido, Instalación
- **Arquitectura de Microservicios:** Diagrama ASCII y tabla de servicios
- **Guía de Action Buttons:** Instrucciones paso a paso

### 🐛 Corregido (Fixed)

- **Bug: Photo URLs Corruptas** - Actualización a URLs válidas de Unsplash/Pexels
- **Bug: Tests de Rasa Fallando por Fechas** - Implementación de cálculo dinámico
- **Bug: Rasa Tests No Ejecutables** - Montaje de volumen rasa_model en backend container
- **Bug: Dependencias de Compilación** - Adición de build-essential en Dockerfile
- **Bug: setuptools/wheel Incompatibles** - Upgrade automático en Dockerfile
- **Bug: Fixtures Hardcodeados** - Cliente_id ahora dinámico en conftest.py

---

### ✨ Añadido (Added)

**Flujo Propietario y Refactorización Rasa:**
- Flujo de trabajo completo como propietario: gestión de negocios, servicios y clientes desde la plataforma.
- Corrección de bugs detectados en producción.
- Refactorización inicial de Rasa para eliminar deuda técnica y unificar la lógica de gestión de citas.
- Rasa ahora usa un sistema general para la gestión de citas de todos los negocios, usando metadatos para identificar el negocio y el usuario en cada interacción.
- Respuestas contextuales de urgencias según tipo de negocio (dentista, peluquería, fisioterapia), evitando solapamientos y malentendidos.
- Identificación de intenciones de reserva y consulta usando FuzzyWuzzy para tolerancia a errores ortográficos en los servicios.
- Eliminación de duplicidad y repetición de código en acciones de Rasa.
- Mejor comprensión del modelo y reducción de malentendidos.

### 🔧 Cambiado (Changed)

- Refactorización de las acciones de Rasa para centralizar la gestión de citas y urgencias.
- Uso de metadatos en los mensajes para mantener el contexto de negocio y usuario.
- Mejoras en la experiencia de usuario para propietarios y clientes.

### 🐛 Corregido (Fixed)

- Bugs en la gestión de citas y servicios detectados en el desarrollo.
- Solapamiento de respuestas de urgencias y repetición de código en Rasa.

---

### ✨ Añadido (Added)

**Orquestación Profesional:**
- **Docker Compose:** Sistema de 4 microservicios completamente containerizado
  - `backend`: Flask API en contenedor con volumen de rasa_model
  - `postgres`: PostgreSQL 15-Alpine con persistencia garantizada
  - `rasa`: Motor de diálogo Rasa 3.6.13
  - `rasa-actions`: Servidor de acciones personalizadas
- **Red Docker Interna:** Comunicación segura entre servicios en red privada `sector_mind_net`
- **Volúmenes Persistentes:** 
  - Base de datos PostgreSQL (volumen named)
  - Modelo Rasa (volumen bind mount)

**Infraestructura y DevOps:**
- **Action Buttons en VS Code:** Interfaz gráfica para operaciones comunes
  - 🚀 `INICIAR TODO SECTOR MIND` - Levanta stack completo
  - 🛑 `STOP DOCKER` - Detiene e elimina contenedores
  - 🧪 `TESTS` - Ejecuta suite unificada de tests
- **Scripts PowerShell Profesionales:**
  - `start_docker.ps1` - Manejo robusto de errores, esperas inteligentes
  - `stop_docker.ps1` - Limpieza completa de contenedores
  - `run_tests.ps1` - Ejecución flexible con flags (-BackendOnly, -RasaOnly, -Coverage)
- **CI/CD Ready:** Dockerfile optimizado con multi-stage build, setuptools/wheel preinstalados

**Base de Datos:**
- **Migración PostgreSQL 100%:** Sustitución completa de SQLite
  - Transacciones ACID garantizadas
  - RealDictCursor para resultados dict-like
  - Preparación para escalabilidad horizontal
- **Schema Mejorado:** 7 tablas relacionales normalizadas con constraints integrity
- **manage_db.py Refactorizado:** Adaptado exclusivamente a PostgreSQL

**Testing e Integración:**
- **Suite Unificada:** 104 tests (75 backend + 29 Rasa) con ejecución centralizada
  - Backend: 100% cobertura en rutas críticas
  - Rasa: Tests parametrizados con mocking de APIs
  - Fechas dinámicas en tests para evitar fallos temporales
- **Ejecución desde Docker:** Tests se ejecutan dentro del contenedor backend
- **Resumen de Tests Mejorado:** Salida con conteo de tests pasados vs. exit codes

**Frontend:**
- **Fotos de Negocios Reales:** URLs actualizadas a Unsplash/Pexels con verificación manual
- **Credenciales Simplificadas:** Contraseñas cortas (p, c) para pruebas rápidas

### 🔧 Cambiado (Changed)

**Backend:**
- **Eliminación Total de SQLite:** Cero imports de sqlite3 en codebase
  - `db.py` - Usa psycopg2 exclusivamente
  - `db_utils.py` - Adaptación de queries de '?' a '%s (archivo ya eliminado)'
  - Todas las rutas - Usan PostgreSQL con RETURNING id

**Tests:**
- **Fixtures Dinámicos:** `logic_test_data` ahora genera cliente_id en runtime
- **Gestión de Errores HTTP:** Status codes corregidos (409 para conflictos de horario)
- **Fecha Dinámica Rasa:** `test_cancelar_cita_lista_citas` usa datetime.now() + timedelta

**Dependencias:**
- **requirements.txt Pinned:** Versiones exactas para reproducibilidad
  - Flask==3.0.0
  - psycopg2-binary==2.9.9
  - rasa==3.6.13
  - pytest==7.4.3

**Documentación:**
- **README Restructurado:** Secciones de Arquitectura, Uso Rápido, Instalación
- **Arquitectura de Microservicios:** Diagrama ASCII y tabla de servicios
- **Guía de Action Buttons:** Instrucciones paso a paso

### 🐛 Corregido (Fixed)

- **Bug: Photo URLs Corruptas** - Actualización a URLs válidas de Unsplash/Pexels
- **Bug: Tests de Rasa Fallando por Fechas** - Implementación de cálculo dinámico
- **Bug: Rasa Tests No Ejecutables** - Montaje de volumen rasa_model en backend container
- **Bug: Dependencias de Compilación** - Adición de build-essential en Dockerfile
- **Bug: setuptools/wheel Incompatibles** - Upgrade automático en Dockerfile
- **Bug: Fixtures Hardcodeados** - Cliente_id ahora dinámico en conftest.py

---

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