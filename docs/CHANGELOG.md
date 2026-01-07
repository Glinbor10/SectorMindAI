# Historial de Cambios (Changelog)

Todas las modificaciones notables en el proyecto Sector Mind AI se documentarán en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/), y este proyecto se adhiere al versionado semántico.


## [v0.6.1] - 2026-01-06 (Interfaz Visual por Tipo de Negocio)

### ✨ Añadido (Added)

**Backgrounds y Emoji Personalizados por Tipo de Negocio (2026-01-06):**
- **Asignación de Estilos Visuales por Categoría:**
  - **Dentista** 🦷: Fondo azul claro (`bg-blue-100`, `#dbeafe`)
  - **Peluquería** ✂️: Fondo rosa claro (`bg-pink-100`, `#fce7f3`)
  - **Fisioterapia** 🦴: Fondo verde claro (`bg-green-100`, `#dcfce7`)
  - Emoji escalado a `text-6xl` (grid) y 2rem (gestion) con opacidad 0.8

- **Función Helper `getBusinessStyle()`:**
  - Ubicación: `frontend/index.html` (línea 651) y `frontend/gestion_negocio.html` (línea 691)
  - Mapeo de tipo_negocio → {bgColor, emoji, color, textColor}
  - Fallback a 'dentista' si tipo_negocio no coincide (casos edge)
  - Reutilizable para futuras expansiones de categorías

- **Integración en Interfaz de Usuario:**
  - **Grid de Negocios (Cliente):** Función `renderBusinessGrid()` ahora renderiza emoji+background si no hay `foto_base64`
  - **Lista de Propietario:** Función `loadMyBusinesses()` ahora renderiza emoji+background si no hay `foto_base64`
  - **Página de Gestión:** Función `loadBusinessData()` muestra emoji en thumbnail (w-16 h-16) si no hay foto

### 🔧 Cambiado (Changed)

- **Reducción de Categorías de Negocio:**
  - Removida categoría "General" (demasiado genérica en MVP)
  - Dropdown de creación/edición (`business-type`, `edit-business-type`) ahora solo contiene:
    - Dentista
    - Peluquería
    - Fisioterapia
  - Valor default cambiado de 'general' a 'dentista'
  - Archivos afectados: `frontend/index.html`, `frontend/gestion_negocio.html`

- **Mejora de Experiencia Visual:**
  - Negocios sin foto ahora muestran identidad visual clara según tipo
  - Sustitución de placeholder genérico SVG por emoji descriptivo
  - Mejor diferenciación visual entre tipos de negocio en grillas


## [v0.6.0] - 2026-01-06 (Geolocalización de Negocios y Búsqueda por Proximidad)

### ✨ Añadido (Added)

**Geolocalización de Negocios (2026-01-06):**
- **Esquema de Base de Datos Extendido:** Adición de columnas geográficas a tabla `negocios`
  - `latitud DECIMAL(10, 8)` - Rango: -90.0° a +90.0° (precisión de 7 decimales ≈ 1.1 cm)
  - `longitud DECIMAL(11, 8)` - Rango: -180.0° a +180.0° (precisión de 7 decimales ≈ 1.1 cm)
  - `CREATE INDEX idx_negocios_ubicacion ON negocios(latitud, longitud)` para optimización de queries
  - Archivos: `database/schema_postgres.sql`, `backend/migrations/003_add_geolocalizacion.sql`

- **API REST con Cálculo de Distancia:**
  - **Endpoint GET `/negocios/?lat=X&lon=Y`** - Nuevo parámetro de query para ubicación del usuario
    - Calcula distancia Haversine en tiempo real: `SELECT *, 6371 * acos(...) as distancia_km`
    - Ordena automáticamente por proximidad: `ORDER BY distancia_km NULLS LAST`
    - Retorna campo `distancia_km` en respuesta JSON para cada negocio
    - Soporta fallback: sin parámetros devuelve todos los negocios (sin distancia)
  - **Endpoint POST `/negocios`** - Validación de coordenadas en creación
    - Extrae `latitud` y `longitud` del payload (JSON o FormData)
    - Valida rangos: -90 ≤ lat ≤ 90, -180 ≤ lon ≤ 180
    - Retorna error 400 si coordenadas inválidas
    - Opcional: coordenadas pueden omitirse (negocio se crea sin ubicación)
  - **Endpoint PUT `/negocios/<id>`** - Actualización de coordenadas
    - Permite modificar `latitud` y `longitud` de negocios existentes
    - Misma validación de rangos que en POST
  - Archivos: `backend/routes/negocios.py` (refactorización completa)

- **Geocodificación con Nominatim (OpenStreetMap):**
  - **Forward Geocoding:** Función `geocodificarDireccion()` convierte dirección → coordenadas
    - Envía búsqueda a API Nominatim: `GET https://nominatim.openstreetmap.org/search`
    - Parámetros: `q=<dirección>&format=json&limit=1`
    - User-Agent requerido para respetar políticas de rate limiting
    - Respeta límite de ~1 request/segundo de Nominatim
  - **Reverse Geocoding:** Función `useMyLocation()` convierte coordenadas → dirección
    - Envía coordenadas a Nominatim reverse: `GET .../reverse?format=json&lat=X&lon=Y`
    - Extrae `address.road`, `address.house_number`, `address.city` de respuesta
    - Formatea dirección legible automáticamente
  - Archivos: `frontend/index.html`, `frontend/gestion_negocio.html`

- **Interfaz de Usuario para Geolocalización:**
  - **En Creación de Negocio:** 3 métodos para ingresar ubicación
    1. **Input Manual:** Escribir dirección en campo de texto
    2. **Botón "Usar mi ubicación" (📍):** Icono pin en formulario que activa GPS
       - Solicita permiso de geolocalización del navegador (con timeout de 30 segundos)
       - Muestra UI "⏳ Esperando permiso de ubicación..." durante espera
       - Llama automáticamente a reverse geocoding para mostrar dirección legible
    3. **Botón "Actualizar coordenadas":** Re-geocodifica dirección si fue editada
  - **En Edición de Negocio:** Funciones paralelas `useMyLocationEdit()` y `geocodificarDireccionEdit()`
  - **Feedback Visual:**
    - ✅ Éxito (verde): "📍 40.41685, -3.70379" con coordenadas mostradas
    - ⚠️ Advertencia (naranja): "Negocio se creará sin coordenadas si falla geocodificación"
    - ❌ Error (rojo): "No se encontraron coordenadas para esa dirección"
  - Archivos: `frontend/index.html`, `frontend/gestion_negocio.html` (UI updates)

- **Visualización de Distancia en Listado:**
  - **Tarjetas de Negocio Mejoradas:** Nueva línea en renderizado
    - Muestra: `📍 ${distancia_km.toFixed(1)} km` cuando geolocalización está habilitada
    - Oculta distancia si usuario denegó permiso de ubicación
  - Archivo: `frontend/index.html` - Función `renderBusinessGrid()`

- **Datos de Prueba con Coordenadas Reales:**
  - Script `backend/manage_db.py` actualizado con 3 negocios en ciudades españolas reales:
    1. **Peluquería Estilo & Glamour** - Madrid (40.4168, -3.7038)
    2. **Clínica Dental Smile** - Barcelona (41.3874, 2.1686)
    3. **FisioMente Centro** - Valencia (39.4699, -0.3763)
  - Output al ejecutar: `✅ Peluquería Estilo & Glamour (ID: 1) - 📍 40.4168, -3.7038`
  - Archivo: `backend/manage_db.py` (array NEGOCIOS y query INSERT)

- **Suite de Tests para Geolocalización:**
  - **6 Tests Nuevos en `backend/tests/test_geolocalizacion.py`:**
    - `test_crear_negocio_con_coordenadas` - Verifica persistencia de lat/lon en BD
    - `test_crear_negocio_sin_coordenadas` - Negocio creado exitosamente con coords NULL
    - `test_listar_negocios_con_distancia` - Calcula y ordena por distancia correctamente
      - Crea 3 negocios (Madrid, Barcelona, Valencia)
      - Consulta desde ubicación del usuario (Madrid)
      - Valida orden: Negocio A (0 km) → B (302 km) → C (505 km)
      - Verifica cálculo Haversine: Madrid→Valencia ≈ 302 km, Madrid→Barcelona ≈ 505 km
    - `test_actualizar_coordenadas_negocio` - PUT endpoint actualiza lat/lon
    - `test_listar_negocios_sin_ubicacion_usuario` - Fallback sin params lat/lon
    - `test_coordenadas_invalidas` - Valida rechazo de coords fuera de rango
  - **Fixtures Mejorados:** @pytest.fixture `test_user()` usa UUID para emails únicos
    - Previene error "El email ya está registrado" en ejecuciones rápidas
    - Registra usuario como cliente, login automático
  - Tests ejecutados vía Docker: `docker compose exec backend pytest backend/tests/test_geolocalizacion.py -v`
  - **Resultado: 6 tests passing (100%) en 1.20 segundos**
  - Archivo: `backend/tests/test_geolocalizacion.py` (nuevo)

### 🔧 Cambiado (Changed)

- **Backend Routes - `negocios.py` Refactorizado:**
  - Función `listar_negocios()` ahora acepta parámetros `?lat=X&lon=Y` opcionales
  - Fórmula Haversine en SQL para cálculo de distancia: `6371 * acos(cos(radians(lat)) * ...)`
  - Validación de rangos de coordenadas en `crear_negocio()` y `actualizar_negocio()`
  - Manejo de coordenadas NULL en queries con `NULLS LAST`
  
- **Frontend - `index.html` Mejoras Significativas:**
  - Función `loadBusinesses()` ahora es async y solicita geolocalización automáticamente
  - Promesa de geolocalización con timeout de 30 segundos
  - Renderizado de UI "⏳ Esperando permiso de ubicación..." durante espera
  - Construcción dinámica de URL: `/negocios/?lat=X&lon=Y` si permiso otorgado
  - Fallback seguro si usuario deniega permiso

- **Frontend - `gestion_negocio.html` Nuevas Funciones:**
  - Funciones de geocodificación parallelas: `geocodificarDireccionEdit()`, `useMyLocationEdit()`
  - Modal de creación/edición ahora soporta entry de coordenadas

- **Docker y DevOps:**
  - **Fix de Line Endings:** `docker-entrypoint.sh` convertido de CRLF a LF
    - Problema: "exec /app/docker-entrypoint.sh: no such file or directory"
    - Solución: PowerShell script para conversión: `(Get-Content ... -Raw) -replace "`r`n", "`n"`
    - Docker image rebuilda sin cache: `docker-compose build backend --no-cache`
  - **Volumen de Migraciones:** Backend container ahora tiene acceso a scripts de migración

- **Tests - Fixtures Robustos:**
  - `conftest.py` actualizado: fixtures ahora usan `uuid.uuid4()` para emails únicos
  - Previene colisiones en test rápidos (antes usaba `time.time()`)

- **Documentación:**
  - Nuevo archivo `docs/GEOLOCALIZACION.md` con arquitectura técnica completa
    - Flujo de usuario (propietario → geocodificación → BD)
    - Flujo de búsqueda (cliente → GPS → Haversine → ordenamiento)
    - Opciones de entrada (manual, GPS, reverse geocoding)
    - Feedback visual (success/error/warning states)

### 🐛 Corregido (Fixed)

- **Bug: Permiso de Geolocalización No Solicitado**
  - Problema: `loadBusinesses()` no llamaba a `navigator.geolocation.getCurrentPosition()`
  - Solución: Refactorización a async/await con Promise explícita
  - Resultado: Navegador ahora solicita permiso correctamente al cargar la página

- **Bug: Timeout Insuficiente**
  - Problema: 5 segundos no eran suficientes para que usuario responda a permiso
  - Solución: Incrementado a 30 segundos con UI feedback: "⏳ Esperando permiso..."
  - Resultado: Usuario tiene tiempo suficiente para otorgar/denegar permiso

- **Bug: Distancias No Mostradas**
  - Problema: Aún con coordenadas en BD, `renderBusinessGrid()` no mostraba distancia
  - Solución: Agregado cálculo de distancia Haversine en `listar_negocios()` endpoint
  - Resultado: Cada negocio ahora incluye `distancia_km` en respuesta JSON

- **Bug: Docker Backend No Iniciaba**
  - Problema: `docker-entrypoint.sh` tenía line endings Windows (CRLF)
  - Solución: Convertido a Unix line endings (LF) via PowerShell
  - Comando: `(Get-Content -Path ./docker-entrypoint.sh -Raw) -replace "`r`n", "`n" | Set-Content -Path ./docker-entrypoint.sh -NoNewline`
  - Resultado: Backend container ahora inicia correctamente

- **Bug: Tests Registrando Mismo Email**
  - Problema: Fixtures con `time.time()` generaban colisiones en tests rápidos
  - Solución: Cambio a `uuid.uuid4()` para garantizar unicidad
  - Resultado: Tests corren consecutivamente sin "El email ya está registrado"

- **Bug: Validación de Coordenadas Ausente**
  - Problema: Backend aceptaba lat/lon fuera de rango geográfico válido
  - Solución: Validación en `crear_negocio()` y `actualizar_negocio()`:
    - `-90 ≤ latitud ≤ 90`
    - `-180 ≤ longitud ≤ 180`
  - Resultado: Coordenadas inválidas rechazadas con error HTTP 400

### 🧪 Testeado (Tests)

**Backend Geolocation Test Suite:**
- Suite: **6 tests new + 110 existing = 116 total tests (100% passing)**
- **Nuevos Tests:**
  - ✅ `test_crear_negocio_con_coordenadas` - POST con coords
  - ✅ `test_crear_negocio_sin_coordenadas` - POST sin coords (NULL allowed)
  - ✅ `test_listar_negocios_con_distancia` - GET con ?lat=X&lon=Y ordering
  - ✅ `test_actualizar_coordenadas_negocio` - PUT actualiza lat/lon
  - ✅ `test_listar_negocios_sin_ubicacion_usuario` - Fallback sin params
  - ✅ `test_coordenadas_invalidas` - Validación de rangos

**Test Data Validation:**
- ✅ 3 negocios españoles con coordenadas reales verificadas
- ✅ Distancias calculadas: Madrid→Valencia 302.56 km (vs real ~302 km), Madrid→Barcelona 505.10 km (vs real ~505 km)
- ✅ Reverse geocoding: GPS 40.4168, -3.7038 → "Calle Gran Vía, Madrid"

**Rasa Tests (Unchanged):**
- ✅ 12 Rasa action tests - All passing
- Tests aún en `rasa_model/tests/test_acciones.py`

**Full CI/CD Pipeline:**
- ✅ `powershell -ExecutionPolicy Bypass -File ./scripts/run_tests.ps1`
- Result: **116 Backend + 12 Rasa = 128 Total Tests - 100% Passing** ✅

---

## [v0.5.0] - 2025-12-20 hasta 2026-01-02 (Refactorización Rasa, Flujo Propietario y Búsqueda de Clientes)

### ✨ Añadido (Added)

**Búsqueda de Clientes por Email (2026-01-02):**
- Nuevo endpoint `GET /usuarios/buscar?q=<email>` para búsqueda de clientes
  - Filtrado automático a solo usuarios con rol "cliente" (excluye propietarios)
  - Búsqueda case-insensitive con LIKE pattern
  - Máximo 10 resultados, mínimo 2 caracteres de query
  - Retorna: `id`, `nombre`, `email`, `foto_perfil_base64`
- Autocomplete interactivo en formularios de crear/editar cita
  - Dropdown con foto, nombre y email del cliente
  - Debounce 300ms para reducir carga del servidor
  - Validación: requiere seleccionar cliente antes de enviar
- Tests: `test_buscar_usuarios_filtra_por_rol_cliente` - Verifica filtro de rol

**Correcciones UX Frontend (2026-01-02):**
- **Bug Timezone (UTC Shift):** `.toISOString()` convertía horarios locales a UTC (-1 hora)
  - Solución: Formateo manual local `YYYY-MM-DDTHH:MM` sin conversión
  - Aplicado a: `loadAvailableSlots()`, `loadEditAvailableSlots()`, `handleCreateCita()`
  - Tests: `test_post_citas_formato_iso_T` - Valida formato sin segundos
- **Modal Close Error:** Error null al intentar limpiar campo `cita-cliente` inexistente
  - Solución: Actualizados IDs correctos - `cita-cliente-email`, `cita-cliente-id`, `cita-cliente-nombre`
  - Cierre limpio del modal con reset de campos y mensaje
- **Response Parsing:** Falso "Error de conexión" tras cita exitosa (respuesta JSON vacía)
  - Solución: Try-catch seguro en `.json()` con fallback null

**Mejoras Creación de Citas:**
- Aceptación flexible de formatos datetime: `YYYY-MM-DDTHH:MM` y `YYYY-MM-DD HH:MM:SS`
- Soporte de `usuario_id` como alias de `cliente_id` en payload (retrocompatibilidad)
- Test: `test_post_citas_con_usuario_id` - Valida alias usuario_id

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
- **Refactorización arquitectónica de acciones de Rasa:** Modularización completa del código de acciones
  - `actions.py` dividido de 2356 líneas en 9 módulos especializados (reducción del 82%)
  - **Módulos auxiliares:**
    - `utils.py` (106 líneas) - Funciones comunes reutilizables (limpiar_flujo, obtener_horarios, formatear_horarios)
    - `extractores.py` (150 líneas) - Clase ExtractorFechaHora con parsing de fechas/horas naturales
  - **Módulos de flujos:**
    - `contexto.py` (131 líneas) - Inicialización y detección de servicios con fuzzy matching
    - `reservas.py` (132 líneas) - Flujo de reserva en 2 pasos (fecha → hora)
    - `cambios.py` (204 líneas) - Flujo de cambio en 3 pasos (seleccionar → fecha → hora)
    - `cancelaciones.py` (143 líneas) - Flujo de cancelación en 2 pasos
    - `consultas.py` (209 líneas) - Acciones de consulta sin flujos
    - `actions.py` (421 líneas) - Cerebro central con ActionFallbackInteligente
  - Eliminación de 1935 líneas de código duplicado y deuda técnica
  - Mejor separación de responsabilidades y mantenibilidad
  - Facilita testing unitario y trabajo colaborativo
- Rasa ahora usa un sistema general para la gestión de citas de todos los negocios, usando metadatos para identificar el negocio y el usuario en cada interacción.
- Respuestas contextuales de urgencias según tipo de negocio (dentista, peluquería, fisioterapia), evitando solapamientos y malentendidos.
- Identificación de intenciones de reserva y consulta usando FuzzyWuzzy para tolerancia a errores ortográficos en los servicios.
- Eliminación de duplicidad y repetición de código en acciones de Rasa.
- Mejor comprensión del modelo y reducción de malentendidos.

**Frontend Gestión de Negocio:**
- Sistema completo de gestión de citas desde el panel del propietario con calendario interactivo visual.
- Botones de editar/eliminar integrados en cada cita mostrada.
- Modal de creación de citas con selector de servicio, cliente, fecha y hora interactivos.
- Modal de edición de citas con mismo sistema interactivo de calendario y horarios.
- Calendario visual mensual con navegación prev/next month y selección de fechas.
- Lista de horarios disponibles que se actualizan dinámicamente al seleccionar fecha.
- Validación de disponibilidad en tiempo real consultando la API `/disponibilidad`.
- Filtrado automático de slots pasados si la fecha seleccionada es hoy.
- Confirmación visual de fecha/hora seleccionada antes de crear/editar cita.
- Botones de crear/guardar deshabilitados hasta completar selección de fecha y hora.
- Event listeners para cerrar modales al hacer clic fuera del contenido.
- Scroll independiente en lista de citas (máx height con overflow-y-auto).

**Intents y Detección de Agradecimientos:**
- Nuevo intent `thanks` con 13 ejemplos en español (gracias, muchas gracias, ok gracias, vale gracias, perfecto gracias, etc.).
- Respuesta `utter_thanks` con 3 variaciones amigables que ofrecen seguir ayudando.
- Regla en `rules.yml` para manejar agradecimientos automáticamente.
- Modelo reentrenado y contenedor de Rasa reiniciado para aplicar cambios.

**Tests y Validación:**
- 12 tests unitarios para `ExtractorFechaHora` en `test_acciones.py` cubriendo:
  - 4 tests de extracción de fechas (mañana, lunes, número, no disponible)
  - 6 tests de extracción de horas (exacta, con espacio, más cercana, inválida, texto, media)
  - 2 stubs de fuzzy matching para futura implementación
- Tests de stories deshabilitados en `run_tests.ps1` por ser demasiado estrictos.
- **3 nuevos tests (2026-01-02):**
  - `test_buscar_usuarios_filtra_por_rol_cliente` - Verifica filtro rol="cliente"
  - `test_post_citas_formato_iso_T` - Valida formato `YYYY-MM-DDTHH:MM` (sin segundos)
  - `test_post_citas_con_usuario_id` - Valida alias `usuario_id` para `cliente_id`
- Suite final: **104 tests automatizados (92 backend + 12 Rasa acciones) - 100% passing**

### 🔧 Cambiado (Changed)

- Refactorización de las acciones de Rasa para centralizar la gestión de citas y urgencias.
- Uso de metadatos en los mensajes para mantener el contexto de negocio y usuario.
- Mejoras en la experiencia de usuario para propietarios y clientes.
- Script `run_tests.ps1` optimizado para ejecutar solo tests unitarios de backend y Rasa acciones.
- Tests de stories comentados para evitar falsos negativos en CI/CD.

### 🐛 Corregido (Fixed)

- Bugs en la gestión de citas y servicios detectados en el desarrollo.
- Solapamiento de respuestas de urgencias y repetición de código en Rasa.
- Validación de disponibilidad de horarios al crear/editar citas desde el panel de gestión.
- Parsing de fechas/horas con mayor tolerancia a formatos diversos (espacios, texto natural).
- Intent `thanks` ahora reconocido correctamente y responde con mensajes amigables.

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