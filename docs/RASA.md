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

## 2. Lo que se hace actualmente (Estado Actual)

### A. Comprensión del Lenguaje (NLU)
El modelo está entrenado para gestionar el flujo completo de una reserva.
* **Intents (Intenciones):** Detecta qué quiere el usuario.
    * `reservar_cita`: Inicio del flujo principal.
    * `elegir_negocio`, `elegir_servicio`, `elegir_fecha`: Aportación de datos.
    * `greet`, `goodbye`: Protocolo social.
* **Entities (Datos):** Extrae información crítica:
    * `negocio`: Nombre del establecimiento (ej. "Peluquería Estilo").
    * `servicio`: Tipo de servicio (ej. "corte de pelo").
    * `fecha`: Momento deseado (ej. "mañana", "lunes").

### B. Gestión del Diálogo (Stories & Rules)
* **Saludo Contextual:** Gracias a una regla específica (`rules.yml`), si el frontend envía un payload con el nombre del negocio (al hacer clic en una tarjeta), el bot saluda reconociendo ese contexto inmediatamente.
* **Flujos de Historia:** Soporta tanto el "Happy Path" (el usuario da toda la info de golpe) como flujos interactivos donde el bot pregunta dato por dato.

### C. Acciones Personalizadas (`actions.py`)
Es el componente más complejo, encargado de la validación y conexión con la API:
1.  **`ActionValidarEntidades` (Corrección Inteligente):**
    * Utiliza la librería `fuzzywuzzy` para corregir errores tipográficos del usuario.
    * *Ejemplo:* Si el usuario escribe "peloqueria", el sistema lo asocia automáticamente con "Peluquería Estilo" basándose en la base de datos real.
2.  **`ActionMostrarDisponibilidad`:**
    * Consulta el endpoint `/disponibilidad` del backend Flask.
    * Verifica si la fecha solicitada tiene huecos libres.
3.  **`ActionReservarCita`:**
    * Envía la petición final POST al backend para guardar la reserva en la base de datos SQL.

---

## 3. Lo que se quiere hacer (Hoja de Ruta / Mejoras)

Para robustecer el sistema y pasar de una "Beta Funcional" a un producto de producción, se plantean los siguientes objetivos:

### A. Integración de Duckling (Manejo de Fechas)
* **Problema actual:** El sistema detecta "mañana" como una entidad de texto simple. La conversión a fecha real (`YYYY-MM-DD`) se hace de forma manual o frágil.
* **Solución:** Configurar `DucklingEntityExtractor` en el `config.yml`.
* **Resultado:** Rasa convertirá automáticamente expresiones como "el próximo viernes a las 5" en un objeto JSON con fecha y hora exactas estandarizadas.

### B. Gestión de Formularios (Rasa Forms)
* **Objetivo:** Implementar `Forms` para la recolección de datos (`negocio` + `servicio` + `fecha`).
* **Ventaja:** Simplifica las `stories.yml`. El formulario "atrapa" al usuario en un bucle hasta que proporcione toda la información necesaria, manejando validaciones y rechazos de forma más limpia que las historias manuales.

### C. Fallback y Recuperación (Manejo de Errores)
* **Objetivo:** Mejorar la respuesta cuando el bot no entiende ("Low Confidence") o cuando el Backend Flask está caído.
* **Acción:** Crear una política de "Two-Stage Fallback". Primero pedir al usuario que reformule, y si falla de nuevo, ofrecer opciones botones o derivar a humano (simulado).

### D. Optimización para Voz (Multimodal)
* **Contexto:** Dado que el frontend permite entrada por micrófono.
* **Mejora:** Entrenar el modelo con frases más cortas y coloquiales, típicas del lenguaje hablado, que difieren del lenguaje escrito.

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