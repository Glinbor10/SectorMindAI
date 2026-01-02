
# 🧠 Arquitectura del Asistente Conversacional (Rasa) - Sector Mind AI (v0.5.x)

Este documento describe el funcionamiento actual (v0.5.x) del módulo de IA conversacional Rasa en Sector Mind AI, tras la refactorización para gestión generalizada de citas y reducción de deuda técnica.

---

## 1. Rol de Rasa en el Proyecto (v0.5.x)

Rasa es el cerebro conversacional y el orquestador de la lógica de negocio. Su función es estructurar el lenguaje natural del usuario para interactuar con la API Backend (Flask), gestionando reservas, urgencias y consultas de forma centralizada y contextual.

### Arquitectura de Conexión (Containerizada)

```
┌─────────────────────────────────────────────────────────────┐
│ Docker Compose Network (sector_mind_net)                    │
├─────────────────────────────────────────────────────────────┤
│  Frontend (navegador) → Backend (Flask) → PostgreSQL        │
│        │             ↘                                      │
│        │              → Rasa Core (5005)                    │
│        │              → Rasa Actions Server (5055)          │
└─────────────────────────────────────────────────────────────┘
```

**Ventajas:**
- Aislamiento y reproducibilidad total
- Versionado exacto (`rasa:3.6.13`)
- Persistencia de modelos y logs
- Escalabilidad y despliegue sencillo

---

## 2. Estado Actual (v0.5.x): Gestión Generalizada y Contextual

### A. Comprensión del Lenguaje (NLU) y Contexto
- El modelo ahora utiliza una arquitectura **generalizada**: los intents y ejemplos están unificados y enriquecidos con metadatos de negocio y usuario.
- Los metadatos (`negocio_id`, `tipo_negocio`, `cliente_id`) se envían desde el frontend y se almacenan en slots.
- El bot identifica la intención (reserva, consulta, urgencia, información) y el tipo de negocio para adaptar la respuesta y lógica.
- Se utiliza FuzzyWuzzy para detectar servicios aunque el usuario escriba con errores ortográficos.

#### Intents principales:
- `reservar_servicio`, `informar_fecha`, `consultar_citas`, `cancelar_cita`, `info_negocio`, `urgencia`, `greet`, `goodbye`, `affirm`, `deny`.

#### Entities:
- `servicio`, `fecha`, `negocio`, `tipo_negocio`, `urgencia_tipo`

### B. Gestión del Diálogo (Stories & Rules)
- Los flujos conversacionales están centralizados y adaptan la lógica según el tipo de negocio y la intención detectada.
- El bot puede gestionar reservas, urgencias, consultas y cancelaciones en cualquier contexto de negocio.
- Las reglas y stories usan slots y metadatos para personalizar la experiencia.

#### Ejemplo de flujo:
1. Usuario saluda → `action_set_contexto` inicializa contexto con metadatos
2. Usuario menciona servicio o urgencia → `action_normalizar_servicio` y lógica de urgencia adaptada
3. Bot consulta disponibilidad → `action_mostrar_disponibilidad`
4. Usuario elige fecha → `action_reservar_cita` o `action_urgencia` según contexto
5. Confirmación y cierre

### C. Acciones Personalizadas - Arquitectura Modular (9 Módulos)

**Refactorización v0.5.0:** `actions.py` de 2356 líneas dividido en 9 módulos especializados:

#### Módulos Auxiliares:
- **`utils.py` (106 líneas):** Funciones comunes
  - `limpiar_flujo()`: Limpia slots del flujo activo
  - `obtener_horarios_disponibles()`: Consulta API de disponibilidad
  - `formatear_horarios_display()`: Formatea horarios (3 días, 3 slots por día)
- **`extractores.py` (150 líneas):** Clase `ExtractorFechaHora`
  - `extraer_solo_fecha()`: Parsea "mañana", "viernes 15", "30/01"
  - `extraer_solo_hora()`: Parsea "10:30", "10 45", "diez y media"
  - Soporte de texto natural y validación estricta

#### Módulos de Flujos:
- **`contexto.py` (131 líneas):** Inicialización
  - `ActionSetContexto`: Establece cliente_id y negocio_id
  - `ActionNormalizarServicio`: Fuzzy matching de servicios
- **`reservas.py` (132 líneas):** Flujo reserva (fecha → hora)
  - `ActionReservarCita`: Extrae fecha, muestra horarios
  - `ActionConfirmarHoraReserva`: Extrae hora, crea cita
- **`cambios.py` (204 líneas):** Flujo cambio (seleccionar → fecha → hora)
  - `ActionCambiarHorario`, `ActionSeleccionarCitaCambio`
  - `ActionConfirmarFechaCambio`, `ActionConfirmarHoraCambio`
- **`cancelaciones.py` (143 líneas):** Flujo cancelación
  - `ActionCancelarCita`, `ActionSeleccionarCitaCancelar`
  - `ActionProcesarConfirmacionCancelar`
- **`consultas.py` (209 líneas):** Acciones sin flujos
  - `ActionConsultarCitasUsuario`, `ActionListarServicios`
  - `ActionMostrarHorarios`, `ActionMostrarUbicacion`

#### Cerebro Central:
- **`actions.py` (421 líneas):** Reducido 82%
  - `ActionFallbackInteligente`: Router según flujo_activo
  - `ActionResponderBotChallenge`: Respuestas contextuales
  - Métodos privados para cada flujo (`_ejecutar_reservar_cita`, etc.)

**Ventajas:**
- ✅ 82% reducción en archivo principal (2356 → 421 líneas)
- ✅ Responsabilidades únicas por módulo (130-200 líneas c/u)
- ✅ Testing unitario más sencillo
- ✅ Trabajo colaborativo sin conflictos
- ✅ Debugging más claro con nombres de módulos

---

## 3. Mejoras y Roadmap Próximo (v0.5.x+)

- Integración avanzada de Duckling para fechas complejas
- Uso de Rasa Forms para validación estricta de datos
- Fallback inteligente y recuperación de errores
- Optimización para entrada por voz y sinónimos regionales
- Gestión de múltiples citas y cancelaciones

---

## 4. Estructura de Archivos Detallada (v0.5.x)

```
rasa_model/
├── config.yml                    # Pipeline ML (DIETClassifier, TEDPolicy, etc.)
├── domain.yml                    # Intents (+ thanks), slots, actions, responses
├── credentials.yml               # Conexión con frontend (socketio/rest)
├── endpoints.yml                 # URL del action server
│
├── data/
│   ├── nlu.yml                  # Intents unificados (incluye thanks)
│   ├── stories.yml              # Flujos conversacionales centralizados
│   └── rules.yml                # Reglas globales (incluye agradecimiento)
│
├── actions/
│   ├── __init__.py              # Exports de todos los módulos
│   ├── actions.py               # Cerebro central (421 líneas)
│   ├── utils.py                 # Funciones comunes (106 líneas)
│   ├── extractores.py           # Parsing fechas/horas (150 líneas)
│   ├── contexto.py              # Inicialización (131 líneas)
│   ├── reservas.py              # Flujo reserva (132 líneas)
│   ├── cambios.py               # Flujo cambio (204 líneas)
│   ├── cancelaciones.py         # Flujo cancelación (143 líneas)
│   └── consultas.py             # Consultas sin flujos (209 líneas)
│
├── tests/
│   ├── test_acciones.py         # 12 tests unitarios (100% passing)
│   └── test_stories.yml         # Tests de stories (deshabilitados)
│
└── models/
    └── sectormind-model.tar.gz  # Modelo entrenado
```

### Archivos Clave:

| Archivo | Descripción | Líneas |
| :--- | :--- | :--- |
| `domain.yml` | Intents (thanks), slots, acciones, respuestas | - |
| `data/nlu.yml` | 19 intents con ejemplos (incluye thanks) | - |
| `data/rules.yml` | Reglas para cada intent (incluye agradecimiento) | - |
| `actions/actions.py` | Cerebro central + ActionFallbackInteligente | 421 |
| `actions/utils.py` | Funciones comunes reutilizables | 106 |
| `actions/extractores.py` | Clase ExtractorFechaHora | 150 |
| `actions/contexto.py` | Inicialización y fuzzy matching | 131 |
| `actions/reservas.py` | Flujo reserva (fecha → hora) | 132 |
| `actions/cambios.py` | Flujo cambio (3 pasos) | 204 |
| `actions/cancelaciones.py` | Flujo cancelación | 143 |
| `actions/consultas.py` | Consultas sin flujos | 209 |
| `tests/test_acciones.py` | 12 tests unitarios | - |
| `config.yml` | Pipeline ML | - |