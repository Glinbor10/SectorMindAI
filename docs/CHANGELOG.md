# Historial de Cambios (Changelog)

Formato basado en Keep a Changelog y SemVer.

## Releases publicados (GitHub)

Tags/publicaciones confirmadas:
- 1.0.1 - 2026-04-05
- 0.5.0 - 2026-01-02
- 0.3.0 - 2025-12-06
- 0.2.0 - 2025-11-29
- 0.1.0 - 2025-11-28

Versiones internas/documentadas sin tag publico confirmado en GitHub:
- 1.0.0 - 2026-03-21
- 0.7.5 - 2026-01-29
- 0.7.4 - 2026-01-29
- 0.7.3 - 2026-01-29
- 0.7.2 - 2026-01-17
- 0.7.1 - 2026-01-15
- 0.7.0 - 2026-01-08
- 0.6.1 - 2026-01-06
- 0.6.0 - 2026-01-06
- 0.4.0 - 2025-12-20
- 0.0.1 - 2025-11-02

## [1.0.1] - 2026-04-05

Release GitHub: publicado como tag `v1.0.1`.

### Added
- Documentacion exhaustiva: `docs/CONTEXTO_TFG.md` como referencia tecnica para capitulos TFG.
- Accesibilidad mejorada: tarjetas de discovery completamente clicables (teclado + mouse).

### Fixed
- Discovery: tarjetas ahora usan todo el contenedor como area de navegacion.
- Soporte de teclado: Enter/Espacio en tarjetas de negocios.
- Correccion de UC-03 (flujo GPS automatico).
- Rasa NLU: correccion en validacion de fechas relativas cruzando cambio de mes.
- Algoritmo de reservas: caso limite en `verificar_solapamiento()` para servicios que terminan al cierre.
- Geolocalizacion: salida de carga infinita cuando usuario deniega permisos de ubicacion.

### Changed
- Mejor manejo de rate limiting de Nominatim en frontend (debounce y errores amigables).
- Mejoras de robustez en reconocimiento de voz (Firefox y movil).
- UX: mayor proteccion frente a cancelaciones accidentales de cita.
- README actualizado con reinicio de servicios Rasa via Docker.

## [1.0.0] - 2026-03-21

Release GitHub: pendiente de confirmar tag/fecha publica.

### Added
- Consolidacion de arquitectura dual Rasa:
  - Rasa Discovery (5006)
  - Rasa Model (5005)
- Documentacion unificada y coherente con estado del repositorio.
- Flujo de testing Docker unificado con `scripts/run_tests.ps1`.

### Changed
- Documentacion de proyecto actualizada a estado estable v1.0.0.
- Eliminado lenguaje de roadmap de nuevas features; foco en mantenimiento correctivo.

### Fixed
- Ajustes de coherencia documental y limpieza de inconsistencias historicas.

## [0.7.5] - 2026-01-29

Release GitHub: sin tag publico confirmado.

### Added
- Variacion realista de numero de servicios por negocio (1-4) para datos de muestra.
- Servicios unicos por tipo de negocio para mejorar testing y realismo.

### Fixed
- Mejor diferenciacion visual y funcional entre negocios similares.

## [0.7.4] - 2026-01-29

Release GitHub: sin tag publico confirmado.

### Added
- Fallback inteligente en Rasa Model: deteccion directa de nombres de servicio antes de fallback generico.

## [0.7.3] - 2026-01-29

Release GitHub: sin tag publico confirmado.

### Added
- Fotos unicas para cada negocio de ejemplo.
- Mejoras en comprension de intents y entidades en Discovery.

### Fixed
- Correcciones menores en visualizacion de fotos y asignacion de imagenes.

## [0.7.2] - 2026-01-17

Release GitHub: sin tag publico confirmado.

### Added
- Deteccion de disponibilidad para "manana" con filtrado inteligente.
- Seleccion enumerada de negocios y redireccion automatica desde Discovery.

### Changed
- Simplificacion de seleccion de ubicacion (auto-seleccion del mejor resultado).
- Limite de resultados de negocios reducido para mejorar claridad.

### Fixed
- Filtrado de "mis citas" por `negocio_id` en contexto.
- Correcciones de deteccion de saludos y scoring de geocoding.
- Eliminacion de import duplicado que causaba `UnboundLocalError`.

## [0.7.1] - 2026-01-15

Release GitHub: sin tag publico confirmado.

### Added
- Expansion de datos de muestra (mas negocios y servicios).
- `.env.example` e instrucciones ampliadas de configuracion.

### Changed
- Limpieza de ejecucion de migraciones SQL para robustez ante comentarios/statements vacios.

## [0.7.0] - 2026-01-08

Release GitHub: sin tag publico confirmado.

### Added
- Interfaz adaptativa por rol (cliente vs propietario) sin recarga de pagina.
- Carga dinamica de negocios segun rol.

### Changed
- Refactorizacion de autenticacion y separacion de responsabilidades entre `index.html` y `app.js`.
- Simplificacion estructural de vistas y reduccion de complejidad de layout.

### Fixed
- Carga de negocios de propietario al cambiar de rol.
- Sincronizacion de sesion y limpieza de vista en logout.

## [0.6.1] - 2026-01-06

Release GitHub: sin tag publico confirmado.

### Added
- Estilo visual por tipo de negocio (emoji + backgrounds personalizados).

### Changed
- Reduccion de categorias de negocio al MVP (dentista, peluqueria, fisioterapia).
- Mejor diferenciacion visual para negocios sin foto.

## [0.6.0] - 2026-01-06

Release GitHub: sin tag publico confirmado.

### Added
- Geolocalizacion completa de negocios (schema, API y frontend).
- Integracion con Nominatim (forward y reverse geocoding).
- Visualizacion de distancia en tarjetas y datos de prueba con coordenadas reales.
- Suite de tests de geolocalizacion en backend.

### Changed
- Refactor de `backend/routes/negocios.py` para soporte `lat/lon` y Haversine.
- Mejoras de UX en permisos GPS y fallback seguro.

### Fixed
- Permiso de geolocalizacion, timeout de espera y distancias no mostradas.
- Problemas de arranque Docker por line endings en `docker-entrypoint.sh`.
- Colisiones de emails de tests y validacion de coordenadas fuera de rango.

## [0.5.0] - 2026-01-02

Release GitHub: publicado como tag `v0.5.0`.

### Added
- Endpoint `GET /usuarios/buscar` con filtro por rol cliente y autocomplete.
- Mejoras UX en gestion de citas (modales, parsing, validaciones).
- Refactorizacion profunda de Rasa a arquitectura modular (9 modulos).
- Nuevos tests backend y suite final 104/104 passing (92 backend + 12 Rasa).

### Changed
- Migracion total a PostgreSQL y consolidacion de scripts en `scripts/`.
- `run_tests.ps1` optimizado para flujo de pruebas de backend y acciones Rasa.

### Fixed
- Bug de timezone en horarios.
- Limpieza de modales y parseo seguro de respuestas vacias.
- Solapamientos y deuda tecnica en acciones Rasa.

## [0.4.0] - 2025-12-20

Release GitHub: sin tag publico confirmado.

### Added
- Profesionalizacion con Docker Compose y PostgreSQL.
- Scripts PowerShell de operacion y testing.
- Suite unificada de tests ejecutable en contenedores.

### Changed
- Eliminacion completa de SQLite del backend y adaptacion de rutas/queries.
- Dependencias pinneadas para reproducibilidad.

### Fixed
- Estabilidad de tests de Rasa por fechas dinamicas.
- Problemas de dependencias/build y fixtures hardcodeados.

## [0.3.0] - 2025-12-06

Release GitHub: publicado como tag `v0.3.0`.

### Added
- Sistema integral de testing y calidad (123 tests, 82% cobertura global).
- Mejoras en IA y custom actions de Rasa.

### Changed
- Refuerzo de fixtures, manejo de uploads en tests y ajustes documentales.

### Fixed
- Errores de validacion y consistencia en endpoints y tests.

## [0.2.0] - 2025-11-29

Release GitHub: publicado como tag `v0.2.0`.

### Added
- IA multimodal (voz), gestion de imagenes de perfil y UX moderna.
- Lock screen para acceso al asistente y auto-login tras registro.

### Changed
- Reescritura de `manage_db.py` y mejoras de persistencia de navegacion.

### Fixed
- Correccion de errores HTTP y validaciones de email en datos de muestra.

## [0.1.0] - 2025-11-28

Release GitHub: publicado como tag `v0.1.0`.

### Added
- Primera version funcional del sistema (backend Flask, frontend, DB, Rasa).
- Script `manage_db.py` y automatizacion inicial de arranque.

## [0.0.1] - 2025-11-02

Release GitHub: sin tag publico confirmado.

### Added
- Inicio del proyecto y estructura base (`backend/`, `frontend/`, `database/`, `rasa_model/`).
- Configuracion inicial de entorno y dependencias.

## Politica despues de 1.0.0

Desde v1.0.0 la rama funcional queda cerrada a nuevas features.
Solo se aceptan:
- correcciones de errores
- mejoras de estabilidad
- mantenimiento tecnico
