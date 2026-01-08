
# 🧠 Arquitectura del Asistente Conversacional (Rasa) - Sector Mind AI (v0.7.0)

Este documento resume la arquitectura Rasa en v0.7.0. Para la descripción completa de la nueva separación de modelos (Rasa Discovery + Rasa Model) consulta [RASA_v0.7.md](RASA_v0.7.md).

## Resumen v0.7.0 (Modelos Actuales)
- **Rasa Discovery (nuevo, puerto 5006):** Descubrimiento de negocios por ubicación y tipo de servicio. Integra geocodificación, búsqueda por proximidad y tarjetas clicables que redirigen a `detalle.html?id={id}`.
- **Rasa Model (existente, puerto 5005):** Gestión completa de citas (reservar, cambiar, cancelar, consultar) para un negocio concreto.
- **Frontend:**
  - `index.html` usa Rasa Discovery (chat lateral sticky).
  - `detalle.html` usa Rasa Model (chat principal).
- **Backend:** Ambos modelos consultan API Flask + PostgreSQL; Rasa Discovery llama a `/negocios?lat&lon`; Rasa Model usa endpoints de citas y servicios.

---

## 1. Rasa Discovery (v0.7.0)

**Propósito:** Ayudar a clientes a encontrar negocios cercanos según ubicación y tipo de servicio.

**Directorio / Puerto:** `rasa_discovery/` — 5006

**NLU (data/nlu.yml):**
- Intents clave: `inform_location`, `inform_service_type`, `ask_recommendation`, `affirm_business`, `request_details`, `greet`, `goodbye`.
- Entities: `location`, `service_type`, `distance_preference`.

**Slots (domain.yml):**
```yaml
ubicacion_usuario: text
ubicacion_lat: float
ubicacion_lon: float
tipo_servicio: text
negocios_encontrados: list
negocio_seleccionado: text
cliente_id: int
```

**Acciones Custom (actions/discovery.py):**
- `ActionGeocodeLocation`: Geocodifica dirección vía Nominatim → lat/lon.
- `ActionSearchNearbyBusinesses`: Llama a `/negocios?lat=X&lon=Y` y devuelve lista con `distancia_km`.
- `ActionSelectBusiness`: Selecciona negocio y redirige a `detalle.html?id={id}`.

**Flujo típico (stories.yml):**
1) Usuario da ubicación → geocodificación.  
2) Se buscan negocios cercanos → se listan con distancia.  
3) Usuario confirma uno → se redirige a detalle.

**Entrenamiento (Docker):**
```bash
docker compose run --rm rasa-discovery rasa train
```

**Ejecución (Docker Compose):** expuesto en 5006. Health check: `http://localhost:5006/version`.

---

## 2. Rasa Model (v0.7.0, baseline v0.5.x)

**Propósito:** Gestionar reservas, cambios y cancelaciones de citas para un negocio concreto.

**Directorio / Puerto:** `rasa_model/` — 5005

**NLU (data/nlu.yml):**
- Intents clave: `reservar_servicio`, `informar_fecha`, `informar_hora`, `consultar_citas`, `cancelar_cita`, `cambiar_horario`, `info_negocio`, `urgencia`, `greet`, `goodbye`, `affirm`, `deny`, `thanks`.
- Entities: `servicio`, `fecha`, `hora`, `negocio`, `tipo_negocio`, `urgencia_tipo`.

**Slots (domain.yml):**
```yaml
negocio_id: int
negocio_nombre: text
cliente_id: int
tipo_negocio: text
servicio_solicitado: text
fecha_reserva: text
hora_reserva: text
flujo_activo: categorical  # [reservar, cambiar, cancelar, consulta]
```

**Acciones Custom (actions/):**
- `ActionSetContexto`: Inicializa contexto con negocio_id/cliente_id.
- `ActionReservarCita`: Extrae fecha, muestra horarios disponibles.
- `ActionConfirmarHoraReserva`: Confirma hora y crea cita vía API.
- `ActionCambiarHorario`, `ActionCancelarCita`, `ActionConsultarCitasUsuario`, `ActionMostrarHorarios`, `ActionNormalizarServicio`.
- Arquitectura modular (9 archivos): `actions.py` (core), `utils.py`, `extractores.py`, `contexto.py`, `reservas.py`, `cambios.py`, `cancelaciones.py`, `consultas.py`.

**Flujo típico (stories/rules):**
1) Usuario: "Quiero una cita mañana" → detecta intent + fecha.  
2) `ActionSetContexto` carga negocio/cliente.  
3) `ActionReservarCita` ofrece horarios.  
4) Usuario elige hora → `ActionConfirmarHoraReserva` crea la cita.  
5) Bot confirma con fecha/hora.

**Entrenamiento (Docker):**
```bash
docker compose run --rm rasa rasa train
```

**Ejecución (Docker Compose):** expuesto en 5005. Health check: `http://localhost:5005/version`.

---

## 3. Integración Frontend ↔ Rasa

- **Discovery (index.html):**
  - Endpoint: `http://localhost:5006/webhooks/rest/webhook`
  - Envía `{sender, message, metadata: {cliente_id, ubicacion_texto}}`
  - Renderiza tarjetas `[BUSINESS_CARD]` clicables → `detalle.html?id={id}`.

- **Model (detalle.html):**
  - Endpoint: `http://localhost:5005/webhooks/rest/webhook`
  - Envía `{sender, message, metadata: {negocio, negocio_id}}`
  - Gestiona flujos de cita (reserva, cambio, cancelación).

---

## 4. Diferencias clave Discovery vs Model

| Aspecto | Rasa Discovery | Rasa Model |
| :--- | :--- | :--- |
| Puerto | 5006 | 5005 |
| Directorio | `rasa_discovery/` | `rasa_model/` |
| Objetivo | Encontrar negocios cercanos | Gestionar citas de un negocio |
| Intents | Ubicación, recomendación | Citas, cambios, cancelaciones |
| Slots clave | ubicacion_lat/lon, negocios_encontrados | negocio_id, fecha_reserva, hora_reserva |
| Acciones | Geocoding, búsqueda proximidad | Extracción fecha/hora, lógica de cita |
| Frontend | index.html (chat lateral) | detalle.html (chat principal) |

---

## 5. Cómo entrenar y probar (Docker)

```bash
# Entrenar Discovery (usa servicio docker compose "rasa-discovery")
docker compose run --rm rasa-discovery rasa train

# Entrenar Model (usa servicio docker compose "rasa")
docker compose run --rm rasa rasa train

# Probar salud en los contenedores ya levantados
curl http://localhost:5006/version   # Discovery
curl http://localhost:5005/version   # Model
```

---

## 6. Roadmap breve
- Discovery: enriquecer NLU con sinónimos regionales y ranking por preferencia.
- Model: añadir Forms para validación estricta de datos y multi-idioma.

---

