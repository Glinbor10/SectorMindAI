# 🧠 Arquitectura del Asistente Conversacional (Rasa) - Sector Mind AI

Este documento detalla el funcionamiento actual del módulo de Inteligencia Artificial (Rasa) dentro del ecosistema **Sector Mind AI**, así como las mejoras planificadas para futuras versiones.

---

## 1. Rol de Rasa en el Proyecto
Rasa actúa como el **cerebro conversacional** y el orquestador de la lógica de negocio de cara al usuario. Su función no es solo "chatear", sino estructurar datos no estructurados (lenguaje natural) para interactuar con la API Backend (Flask).

### Arquitectura de Conexión
1. **Frontend:** Captura texto o voz y lo envía a Rasa.
2. **Rasa NLU:** Entiende la intención (*Intent*) y extrae datos clave (*Entities*).
3. **Rasa Core:** Decide la siguiente acción (responder texto o ejecutar código).
4. **Action Server:** Ejecuta lógica Python para conectar con el Backend Flask (Puerto 5000).

---

## 2. Lo que se hace actualmente (Estado Actual - v0.3.0)

### A. Comprensión del Lenguaje (NLU)
El modelo está entrenado para gestionar el flujo completo de una reserva **con ejecución real**.
* **Intents (Intenciones):** Detecta qué quiere el usuario.
    * `reservar_servicio`: Inicio del flujo principal cuando el usuario menciona un servicio.
    * `informar_fecha`: Captura expresiones temporales ("mañana", "el lunes", "hoy").
    * `greet`, `goodbye`, `affirm`, `deny`: Protocolo social y confirmaciones.
* **Entities (Datos):** Extrae información crítica:
    * `negocio`: Nombre del establecimiento (ej. "Peluquería Estilo & Glamour").
    * `servicio`: Tipo de servicio (ej. "corte de pelo", "tinte").
    * `fecha`: Momento deseado (ej. "mañana", "lunes").

### B. Gestión del Diálogo (Stories & Rules)
* **Captura de Contexto Automática:** Al iniciar conversación (`/greet`), ejecuta `action_set_contexto` que obtiene `cliente_id` y `negocio_id` desde los metadatos del frontend.
* **Flujo de Reserva Completo:**
  1. Usuario saluda → Bot captura contexto y da bienvenida personalizada.
  2. Usuario menciona servicio → Bot normaliza y valida contra BD.
  3. Bot consulta disponibilidad → Muestra horarios libres de próximos 7 días.
  4. Usuario elige fecha → Bot interpreta lenguaje natural y crea la cita.
* **Slots Dinámicos:** Uso de slots custom (`negocio_id`, `cliente_id`, `servicio_id`, `horarios_disponibles`) para mantener estado conversacional.

### C. Acciones Personalizadas (`actions.py`) - **✅ IMPLEMENTADAS**
El sistema cuenta con 4 custom actions que ejecutan lógica real:

1.  **`ActionSetContexto` (Inicialización de Sesión):**
    * Captura metadatos enviados por el frontend (`cliente_id`, `negocio_id`, `negocio_nombre`).
    * Los guarda en slots de Rasa para uso en acciones posteriores.
    * Se ejecuta automáticamente en el primer mensaje del usuario.

2.  **`ActionNormalizarServicio` (Detección Inteligente de Servicios):**
    * Consulta endpoint `/negocios/{negocio_id}/servicios` para obtener servicios reales.
    * Usa matching de palabras clave para detectar el servicio mencionado por el usuario.
    * *Ejemplo:* Si el usuario dice "quiero un corte" o "necesito tinte", lo asocia automáticamente con "Corte de pelo" o "Tinte completo" según la BD.
    * Guarda `servicio_id` en slot para acciones posteriores.

3.  **`ActionMostrarDisponibilidad` (Consulta de Horarios Disponibles):**
    * Consulta endpoint `/disponibilidad` con `negocio_id` y `servicio_id`.
    * Itera sobre los próximos 7 días buscando slots libres (intervalos de 15 minutos).
    * Muestra al usuario los 3 días con mayor disponibilidad en formato legible ("Hoy", "Mañana", "Lunes 8/12").
    * Guarda diccionario de horarios disponibles en slot para selección posterior.

4.  **`ActionReservarCita` (Creación de Cita en BD):**
    * Interpreta la fecha dicha por el usuario usando lógica de NLP simple:
      - "hoy" / "mañana" / "pasado mañana" → Calcula fecha exacta.
      - "el lunes" / "el martes" → Encuentra próximo día de la semana.
    * Selecciona automáticamente el **primer horario disponible** del día elegido.
    * Envía POST a `/citas` con `cliente_id`, `negocio_id`, `servicio_id`, `fecha_hora_cita`.
    * Confirma la reserva al usuario con formato legible ("08/12/2025 a las 10:00").
    * Limpia los slots de servicio y fecha para permitir nuevas reservas.

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

## 4. Estructura de Archivos Clave

| Archivo | Descripción |
| :--- | :--- |
| `domain.yml` | El "universo" del bot: define todos los intents, entidades, slots y respuestas de texto. |
| `nlu.yml` | Datos de entrenamiento: frases de ejemplo para enseñar al bot a entender. |
| `stories.yml` | Guiones de conversación: enseña al bot cómo transcurre un diálogo. |
| `rules.yml` | Reglas fijas: "Si pasa X, haz Y siempre" (ej. Saludo contextual). |
| `actions.py` | Código Python: Conecta Rasa con la Base de Datos y la API Flask. |
| `config.yml` | Configuración del pipeline de Machine Learning (DIETClassifier, etc.). |