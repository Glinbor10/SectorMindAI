
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

### C. Acciones Personalizadas - Únicas y Centralizadas
- Todas las acciones personalizadas están ahora en un único archivo (`actions/actions.py`).
- No existen ya archivos separados por tipo de negocio.
- La lógica de urgencias, reservas, información y cancelaciones se adapta dinámicamente según el slot `tipo_negocio` y los metadatos.
- Ejemplo: Si el usuario reporta una urgencia, el bot responde con el protocolo adecuado según el tipo de negocio (dentista, peluquería, fisioterapia) usando una única acción.
- Se eliminan duplicidades y se reduce la deuda técnica.

#### Acciones principales:
- `ActionSetContexto`: Inicializa contexto y slots con metadatos
- `ActionNormalizarServicio`: Fuzzy matching de servicios
- `ActionMostrarDisponibilidad`: Consulta horarios
- `ActionReservarCita`: Reserva cita
- `ActionCancelarCita`: Cancela cita
- `ActionInfoNegocio`: Da información del negocio
- `ActionResponderBotChallenge`: Respuestas contextuales
- `ActionUrgencia`: Protocolo de urgencias adaptado al tipo de negocio

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
├── domain.yml                    # Intents, slots, actions, responses
├── credentials.yml               # Conexión con frontend (socketio/rest)
├── endpoints.yml                 # URL del action server
│
├── data/
│   ├── nlu/                     # Datos de entrenamiento (unificados y enriquecidos)
│   ├── stories/                 # Flujos conversacionales centralizados
│   └── rules.yml                # Reglas globales
│
├── actions/
│   ├── __init__.py
│   └── actions.py               # Todas las acciones personalizadas (único archivo)
│
├── tests/
│   └── test_actions.py          # Tests unitarios (100% passing)
│
└── models/
    └── ...                      # Modelos entrenados
```

### Archivos Clave:

| Archivo | Descripción |
| :--- | :--- |
| `domain.yml` | Intents, slots, acciones, respuestas |
| `data/nlu/` | Datos de entrenamiento unificados |
| `data/stories/` | Flujos conversacionales centralizados |
| `actions/actions.py` | Todas las acciones personalizadas |
| `tests/test_actions.py` | Tests unitarios |
| `config.yml` | Pipeline ML |