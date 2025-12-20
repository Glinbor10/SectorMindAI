# 🧠 Arquitectura del Asistente Conversacional (Rasa) - Sector Mind AI

Este documento detalla el funcionamiento actual del módulo de Inteligencia Artificial (Rasa) dentro del ecosistema **Sector Mind AI**, así como las mejoras planificadas para futuras versiones.

---

## 1. Rol de Rasa en el Proyecto (v0.4.0)

Rasa actúa como el **cerebro conversacional** y el orquestador de la lógica de negocio de cara al usuario. Su función no es solo "chatear", sino estructurar datos no estructurados (lenguaje natural) para interactuar con la API Backend (Flask).

### Arquitectura de Conexión (Containerizada)

```
┌─────────────────────────────────────────────────────────────┐
│ Docker Compose Network (sector_mind_net)                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Frontend (navegador)                                        │
│        │                                                     │
│        │ HTTP (puerto 5000 mapeado)                         │
│        ▼                                                     │
│  ┌─────────────────────┐                                   │
│  │   Backend (Flask)   │                                   │
│  │    :5000            │                                   │
│  │                     │◄──┐                               │
│  │  - API REST         │   │                               │
│  │  - Auth             │   │                               │
│  │  - Logic            │   │ HTTP :5055 (interno)         │
│  │  - DB Queries       │   │                               │
│  └─────────────────────┘   │                               │
│         │                  │                               │
│         │ conexión TCP     │                               │
│         ▼                  │                               │
│  ┌──────────────────────┐  │                               │
│  │  PostgreSQL 15       │  │                               │
│  │  :5432               │  │                               │
│  │  (persistencia)      │  │                               │
│  └──────────────────────┘  │                               │
│                             │                               │
│         ┌───────────────────┘                               │
│         │                                                   │
│         ▼                                                   │
│  ┌────────────────────────────┐                            │
│  │  Rasa Actions Server       │                            │
│  │  :5055 (HTTP)              │                            │
│  │                            │                            │
│  │  Ejecuta acciones custom:  │                            │
│  │  - SET_CONTEXTO            │                            │
│  │  - NORMALIZAR_SERVICIO     │                            │
│  │  - MOSTRAR_DISPONIBILIDAD  │                            │
│  │  - RESERVAR_CITA           │                            │
│  │  - etc.                    │                            │
│  └────────────────────────────┘                            │
│         │                                                   │
│         │ JSON/HTTP (requests)                             │
│         ▼                                                   │
│  ┌────────────────────────────┐                            │
│  │  Rasa Core                 │                            │
│  │  :5005 (HTTP)              │                            │
│  │                            │                            │
│  │  - NLU (procesamiento)     │                            │
│  │  - Policy (decisiones)     │                            │
│  │  - Slot management         │                            │
│  │  - Response generation     │                            │
│  └────────────────────────────┘                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Ventajas de la Ejecución en Docker (v0.4.0)

1. **Aislamiento:** Rasa no interfiere con Backend
2. **Versionado:** Exactamente `rasa:3.6.13` en todos los ambientes
3. **Persistencia del Modelo:** Volumen bind mount de `./rasa_model`
4. **Escalabilidad:** Fácil escalar a múltiples replicas de Rasa
5. **Reproducibilidad:** Ambiente idéntico en dev/staging/prod
6. **Logs Centralizados:** Visibles con `docker logs sector_mind_rasa`

### Cómo Levantar Rasa en Docker

**Opción 1: Automático (Recomendado)**
```bash
# Desde VS Code: Run Task → 🚀 INICIAR TODO SECTOR MIND
# O desde PowerShell:
docker-compose up -d
```

**Opción 2: Manual (Desarrollo)** 
```bash
# Terminal 1: Rasa Core
cd rasa_model
docker run -it -p 5005:5005 \
  -v $(pwd):/app \
  rasa/rasa:3.6.13 run --enable-api

# Terminal 2: Rasa Actions
docker run -it -p 5055:5055 \
  -v $(pwd):/app \
  rasa/rasa:3.6.13 run actions
```

---

## 2. Lo que se hace actualmente (Estado Actual - v0.4.0)

### A. Comprensión del Lenguaje (NLU) - **Arquitectura Modular por Contexto**
El modelo está entrenado con **arquitectura modular** que separa intents por tipo de negocio para mejor precisión.

#### Estructura de Archivos NLU:
* **`data/nlu/dentista.yml`** - 4 intents de urgencias dentales (34 ejemplos)
* **`data/nlu/peluqueria.yml`** - 2 intents de urgencias peluquería (16 ejemplos)
* **`data/nlu/fisioterapia.yml`** - 3 intents de urgencias fisioterapia (22 ejemplos)

#### Intents Globales (Todos los negocios):
* `reservar_servicio`: Inicio del flujo principal cuando el usuario menciona un servicio.
* `informar_fecha`: Captura expresiones temporales ("mañana", "el lunes", "hoy").
* `greet`, `goodbye`, `affirm`, `deny`: Protocolo social y confirmaciones.

#### Intents Específicos por Contexto (Solo Urgencias):
**Dentista:**
* `urgencia_dental_dolor` - Dolor intenso de diente/muela (10 ejemplos)
* `urgencia_dental_bracket` - Bracket caído/despegado (9 ejemplos)
* `urgencia_dental_diente` - Diente roto/caído (9 ejemplos)
* `perdida_empaste` - Empaste perdido (6 ejemplos)

**Peluquería:**
* `corte_urgente_evento` - Evento importante mañana (8 ejemplos)
* `desastre_tinte` - Tinte mal hecho (8 ejemplos)

**Fisioterapia:**
* `dolor_agudo_espalda` - Dolor lumbar/cervical intenso (7 ejemplos)
* `lesion_deportiva` - Lesión jugando deporte (8 ejemplos)
* `contractura_muscular` - Contractura/tensión muscular (7 ejemplos)

* **Entities (Datos):** Extrae información crítica:
    * `negocio`: Nombre del establecimiento
    * `servicio`: Tipo de servicio 
    * `fecha`: Momento deseado (ej. "mañana", "lunes")

### B. Gestión del Diálogo (Stories & Rules) - **Modular por Tipo de Negocio**

#### Estructura de Archivos de Stories:
* **`data/stories/dentista_stories.yml`** - 4 historias de urgencias dentales
* **`data/stories/peluqueria_stories.yml`** - 2 historias de urgencias peluquería
* **`data/stories/fisioterapia_stories.yml`** - 3 historias de urgencias fisioterapia
* **`data/rules.yml`** - Reglas globales (saludo contextual, cancelación)

#### Flujos de Conversación:

**Flujo Normal (Todos los servicios):**
1. Usuario saluda → `action_set_contexto` captura cliente/negocio → Bienvenida personalizada
2. Usuario menciona servicio → `action_normalizar_servicio` busca en BD con fuzzy matching
3. Bot consulta disponibilidad → `action_mostrar_disponibilidad` muestra próximos 7 días
4. Usuario elige fecha → `action_reservar_cita` interpreta lenguaje natural y crea cita

**Flujo Urgencia (Solo casos críticos):**
1. Usuario menciona urgencia → `action_urgencia_[tipo]` valida contexto + muestra primeros auxilios
2. Bot busca huecos → `action_buscar_urgencia_proxima` busca HOY/MAÑANA/próximos 7 días
3. Usuario elige → `action_reservar_cita` crea la cita urgente

* **Validación de Contexto:** Las acciones de urgencia rechazan requests incorrectos (ej: urgencia dental en peluquería) y detienen el flujo con `ActionExecutionRejected`.
* **Slots Dinámicos:** `negocio_id`, `cliente_id`, `tipo_negocio`, `servicio_id`, `es_urgencia`, `horarios_disponibles`

### C. Acciones Personalizadas - **✅ IMPLEMENTADAS (Arquitectura Modular)**

#### Estructura de Archivos de Acciones:
* **`actions/actions.py`** - Acciones globales (reserva estándar)
* **`actions/dentista_actions.py`** - Urgencias dentales + búsqueda urgente
* **`actions/peluqueria_actions.py`** - Urgencias peluquería
* **`actions/fisioterapia_actions.py`** - Urgencias fisioterapia

#### Acciones Globales (Flujo Normal):

1.  **`ActionSetContexto` (Inicialización + Detección Automática de Tipo):**
    * Captura metadatos del frontend (`cliente_id`, `negocio_id`)
    * **Consulta GET `/negocios/{negocio_id}`** para obtener `tipo_negocio` (dentista/peluqueria/fisioterapia)
    * Guarda `tipo_negocio` en slot para validación de contexto posterior
    * Se ejecuta automáticamente en el primer mensaje

2.  **`ActionNormalizarServicio` (Matching Inteligente con Fuzzy Search):**
    * Consulta `/negocios/{negocio_id}/servicios` para obtener servicios reales del negocio
    * Usa fuzzy matching (difusión de palabras clave) para detectar servicio mencionado
    * *Ejemplo:* "quiero corte" → "Corte de Pelo" | "necesito masaje" → "Masaje Descontracturante"
    * Guarda `servicio_id` y `servicio` en slots

3.  **`ActionMostrarDisponibilidad` (Consulta Horarios con Formato Legible):**
    * Consulta `/disponibilidad?negocio_id=X&servicio_id=Y` 
    * Busca en próximos 7 días, muestra 3 días con mayor disponibilidad
    * Formato: "🟢 **Hoy (07/12):** • 09:00 • 10:30 • 15:00"
    * Guarda diccionario `horarios_disponibles` en slot

4.  **`ActionReservarCita` (Interpretación NLP de Fechas):**
    * Interpreta "hoy", "mañana", "pasado mañana", "el lunes", etc.
    * Selecciona primer horario disponible del día elegido
    * POST `/citas` con datos completos → Confirma con formato legible
    * Limpia slots para nueva reserva

#### Acciones Específicas de Urgencias (Con Validación de Contexto):

5.  **`ActionUrgenciaDental` (Primeros Auxilios Dentales):**
    * **Valida:** `tipo_negocio == "dentista"` (rechaza si no coincide)
    * Respuestas específicas por tipo de urgencia:
      - Dolor intenso → Analgésico + frío + evitar temperaturas extremas
      - Bracket caído → Guardar bracket + traerlo a cita
      - Diente roto → Guardar pieza en leche/saliva + urgencia INMEDIATA
      - Empaste perdido → Evitar masticar + no dulces
    * Marca `es_urgencia=True` en slot

6.  **`ActionUrgenciaPeluqueria` (Protocolos Emergencia Capilar):**
    * **Valida:** `tipo_negocio == "peluqueria"`
    * Evento importante → Busca hueco HOY/MAÑANA
    * Desastre tinte → NO lavar más + NO aplicar productos + traer foto color original

7.  **`ActionUrgenciaFisioterapia` (Protocolo RICE + Primeros Auxilios):**
    * **Valida:** `tipo_negocio == "fisioterapia"`
    * Dolor agudo espalda → Frío 15min/2h + movimiento suave + no peso
    * Lesión deportiva → Protocolo RICE (Reposo/Ice/Compresión/Elevación)
    * Contractura → Calor local + estiramientos suaves

8.  **`ActionBuscarUrgenciaProxima` (Búsqueda Inteligente de Huecos Urgentes):**
    * Busca automáticamente: HOY → MAÑANA → Próximos 7 días
    * Muestra formato: "🔴 HOY / 🟡 MAÑANA / 🟢 Miércoles 11/12"
    * Si no hay huecos en 7 días → Ofrece notificación futura
    * Usada solo después de acciones de urgencia validadas

---

## 3. Próximas Mejoras (Hoja de Ruta v0.4.0)

Aunque el sistema ya ejecuta reservas completas end-to-end, existen oportunidades de mejora:

### A. Integración de Duckling (Manejo Avanzado de Fechas)
* **Situación actual:** La interpretación de fechas funciona para casos comunes ("mañana", días de la semana), pero usa lógica manual.
* **Mejora propuesta:** Configurar `DucklingEntityExtractor` en el `config.yml`.
* **Beneficio:** Soporte para expresiones complejas como "el próximo viernes a las 17:00", "dentro de 3 días", "la semana que viene".

### B. Gestión de Formularios (Rasa Forms)
* **Situación actual:** El flujo funciona mediante stories secuenciales, pero no valida rigurosamente la completitud de datos.
* **Mejora propuesta:** Implementar `Forms` para slot filling obligatorio.
* **Beneficio:** 
  - Validación estricta: Si falta servicio o fecha, el bot insiste hasta obtenerlo.
  - Código más limpio y mantenible.
  - Soporte para correcciones mid-conversation ("Espera, mejor quiero otro servicio").

### C. Fallback Inteligente y Recuperación de Errores
* **Situación actual:** Si el backend está caído o hay error de conexión, el bot devuelve mensaje genérico.
* **Mejora propuesta:** 
  - Implementar `FallbackPolicy` con reintentos automáticos.
  - Mostrar botones con servicios disponibles si no entiende el texto del usuario.
  - Derivar a "contactar con el negocio" si persisten errores.

### D. Optimización para Entrada por Voz
* **Situación actual:** El modelo funciona bien con voz, pero el entrenamiento usa texto escrito.
* **Mejora propuesta:** 
  - Agregar ejemplos de NLU más coloquiales ("dame cita pa mañana", "córtame el pelo").
  - Implementar corrección automática de errores de STT (Speech-to-Text).
  - Usar sinónimos y variaciones regionales ("corte", "cortarse", "cortarme").

### E. Gestión de Múltiples Citas y Cancelaciones
* **Objetivo:** Permitir al usuario:
  - Consultar sus citas existentes ("¿Cuándo tengo cita?")
  - Cancelar o reprogramar citas ("Cancela mi cita del lunes")
  - Reservar múltiples servicios en una sola sesión.

---

## 4. Estructura de Archivos Detallada

```
rasa_model/
├── config.yml                    # Pipeline ML (DIETClassifier, TEDPolicy, etc.)
├── domain.yml                    # Intents, slots, actions, responses
├── credentials.yml               # Conexión con frontend (socketio/rest)
├── endpoints.yml                 # URL del action server
│
├── data/
│   ├── nlu/                     # Datos de entrenamiento (modular)
│   │   ├── dentista.yml         # 4 intents urgencias dentales (34 ejemplos)
│   │   ├── peluqueria.yml       # 2 intents urgencias peluquería (16 ejemplos)
│   │   └── fisioterapia.yml     # 3 intents urgencias fisioterapia (22 ejemplos)
│   │
│   ├── stories/                 # Flujos conversacionales (modular)
│   │   ├── dentista_stories.yml     # 4 historias urgencias dentales
│   │   ├── peluqueria_stories.yml   # 2 historias urgencias peluquería
│   │   └── fisioterapia_stories.yml # 3 historias urgencias fisioterapia
│   │
│   └── rules.yml                # Reglas globales (saludo contextual)
│
├── actions/
│   ├── __init__.py
│   ├── actions.py               # Acciones globales (flujo normal)
│   │   ├── ActionSetContexto
│   │   ├── ActionNormalizarServicio
│   │   ├── ActionMostrarDisponibilidad
│   │   └── ActionReservarCita
│   │
│   ├── dentista_actions.py      # Urgencias dentales
│   │   ├── ActionUrgenciaDental
│   │   └── ActionBuscarUrgenciaProxima
│   │
│   ├── peluqueria_actions.py    # Urgencias peluquería
│   │   └── ActionUrgenciaPeluqueria
│   │
│   └── fisioterapia_actions.py  # Urgencias fisioterapia
│       └── ActionUrgenciaFisioterapia
│
├── tests/
│   └── test_actions.py          # 29 tests unitarios (100% passing)
│
└── models/
    └── 20251206-211531-nervous-sparrow.tar.gz  # Modelo entrenado actual
```

### Archivos Clave:

| Archivo | Descripción | Líneas |
| :--- | :--- | ---: |
| `domain.yml` | Universo del bot: 9 intents urgencias + 10 intents globales, 8 acciones custom, 10 slots | ~120 |
| `data/nlu/[contexto].yml` | Datos entrenamiento modulares (72 ejemplos totales urgencias) | ~120 |
| `data/stories/[contexto].yml` | Historias modulares (9 stories urgencias + flujo normal) | ~150 |
| `actions/actions.py` | Acciones globales (flujo reserva estándar) | ~800 |
| `actions/dentista_actions.py` | Urgencias dentales + búsqueda urgente | ~200 |
| `actions/peluqueria_actions.py` | Urgencias peluquería | ~65 |
| `actions/fisioterapia_actions.py` | Urgencias fisioterapia | ~85 |
| `tests/test_actions.py` | Tests unitarios (29 tests) | ~870 |
| `config.yml` | Pipeline: DIETClassifier, TEDPolicy, UnexpecTEDIntentPolicy | ~50 |