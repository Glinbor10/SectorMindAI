# Historial de Cambios (Changelog)

Formato basado en Keep a Changelog y SemVer.

## [1.0.0] - 2026-03-21

### Added
- Consolidacion de arquitectura dual Rasa:
  - Rasa Discovery (5006)
  - Rasa Model (5005)
- Documentacion unificada y coherente con estado actual del repo.
- Flujo de testing Docker unificado con `scripts/run_tests.ps1`.

### Changed
- Documentacion de proyecto actualizada a estado estable v1.0.0.
- Se elimina lenguaje de roadmap de features y se adopta mantenimiento correctivo.

### Fixed
- Ajustes de coherencia documental y limpieza de inconsistencias historicas.

## [1.0.1] - 2026-04-05

### Added
- Documentacion exhaustiva: `docs/CONTEXTO_TFG.md` - Referencia tecnica completa para capitulos TFG (Design, Implementacion, Manual, Conclusiones)
- Accesibilidad mejorada: Tarjetas de descubrimiento completamente clicables (teclado + mouse)

### Fixed
- Interfaz Discovery: Business cards ahora usan todo el contenedor como area de navegacion (no solo enlace de texto)
- Soporte para navegacion por teclado: Enter/Espacio en tarjetas de negocios
- Validacion de caso de uso UC-03: Descripcion corregida (flujo GPS automatico, no manual)
- Tests: Todos validados y ejecutados exitosamente (104 tests, 92% cobertura)

### Changed
- Documentacion de caso de uso actualizada para reflejar implementacion real (GPS automatico vs manual)

## Politica despues de 1.0.0

Desde v1.0.0 la rama funcional queda cerrada a nuevas features.
Solo se aceptan:
- correcciones de errores
- mejoras de estabilidad
- mantenimiento tecnico
