# Acciones de Rasa - Estructura Modular

## 📊 Resumen de la refactorización

**Antes:** 2356 líneas en un solo archivo `actions.py`  
**Después:** 1525 líneas distribuidas en 9 módulos especializados  
**Reducción:** 82% en el archivo principal (421 líneas)

---

## 📁 Estructura de archivos

### 🔧 Módulos auxiliares

#### `utils.py` (106 líneas)
Funciones comunes reutilizables:
- `limpiar_flujo()` - Limpia slots del flujo activo
- `obtener_horarios_disponibles(negocio_id, servicio_id)` - Consulta API de disponibilidad
- `formatear_horarios_display(horarios_por_dia)` - Formatea horarios para mostrar al usuario
- `calcular_similitud(texto1, texto2)` - Calcula similitud Levenshtein para fuzzy matching

#### `extractores.py` (150 líneas)
Clase `ExtractorFechaHora` con métodos estáticos para parsing de fecha/hora:
- `extraer_solo_fecha(texto, horarios)` - Extrae fecha del texto del usuario
  - Soporta: "hoy", "mañana", "viernes 15", "15/01", "para el lunes"
  - **Prioriza números explícitos sobre días de la semana** (fix: "viernes 15" → 15/01)
- `extraer_solo_hora(texto, horarios)` - Extrae hora del texto del usuario
  - Soporta: "10", "10:30", "a las diez", "diez y media", "las once y cuarto"
  - Incluye diccionarios para parsing de texto: `horas_texto` y `minutos_texto`

---

### 🎯 Módulos de acciones

#### `contexto.py` (131 líneas)
Inicialización y detección de servicios:
- `ActionSetContexto` - Establece `cliente_id` y `negocio_id` desde metadata
- `ActionNormalizarServicio` - Detecta servicio solicitado, obtiene horarios, inicia flujo de reserva

#### `reservas.py` (132 líneas)
Flujo de reserva (3 pasos):
1. `ActionNormalizarServicio` (en contexto.py) → `flujo_activo=reserva_fecha`
2. `ActionReservarCita` - Extrae fecha, muestra horarios del día → `flujo_activo=reserva_hora`
3. `ActionConfirmarHoraReserva` - Extrae hora, crea cita via API POST

#### `cambios.py` (204 líneas)
Flujo de cambio de cita (4 pasos):
1. `ActionCambiarHorario` - Muestra citas del usuario
2. `ActionSeleccionarCitaCambio` - Usuario selecciona cita a cambiar
3. `ActionConfirmarFechaCambio` - Extrae fecha, muestra horarios → `flujo_activo=cambiar_hora`
4. `ActionConfirmarHoraCambio` - Extrae hora, actualiza cita via API PUT

#### `cancelaciones.py` (143 líneas)
Flujo de cancelación (3 pasos):
1. `ActionCancelarCita` - Muestra citas del usuario
2. `ActionSeleccionarCitaCancelar` - Usuario selecciona cita a cancelar
3. `ActionProcesarConfirmacionCancelar` - Confirma y ejecuta cancelación via API DELETE

#### `consultas.py` (209 líneas)
Acciones de consulta (sin flujos):
- `ActionConsultarCitasUsuario` - Lista citas futuras del usuario
- `ActionListarServicios` - Muestra servicios disponibles con precios
- `ActionMostrarHorarios` - Muestra horarios de apertura del negocio
- `ActionMostrarUbicacion` - Muestra dirección y teléfono
- `ActionInfoNegocio` - Información completa del negocio
- `ActionMostrarDisponibilidad` - Prompt para seleccionar servicio

#### `actions.py` (421 líneas)
**Cerebro central del sistema:**
- `ActionFallbackInteligente` - Redirige según `flujo_activo` o detecta servicios
  - Métodos privados: `_ejecutar_reservar_cita()`, `_ejecutar_confirmar_hora_reserva()`, etc.
  - Contiene lógica de todos los flujos (llamada desde fallback cuando el usuario no usa intents específicos)
- `ActionResponderBotChallenge` - Responde cuando preguntan "¿qué eres?"

---

## 🔄 Flujos implementados

### Flujo de Reserva (2 pasos: fecha → hora)
```
Usuario: "quiero un corte"
→ ActionNormalizarServicio
→ flujo_activo = "reserva_fecha"
→ Bot: "¿Para qué día?"

Usuario: "para el viernes 15"
→ ActionReservarCita (o fallback → _ejecutar_reservar_cita)
→ ExtractorFechaHora.extraer_solo_fecha("viernes 15") → "2026-01-15"
→ flujo_activo = "reserva_hora"
→ Bot: "Horarios disponibles: 09:00, 10:00, 11:00... ¿A qué hora prefieres?"

Usuario: "a las diez y media"
→ ActionConfirmarHoraReserva (o fallback → _ejecutar_confirmar_hora_reserva)
→ ExtractorFechaHora.extraer_solo_hora("diez y media") → "10:30:00"
→ POST /citas
→ Bot: "✅ Reserva confirmada para 15/01/2026 a las 10:30"
```

### Flujo de Cambio (3 pasos: seleccionar → fecha → hora)
```
Usuario: "quiero cambiar mi cita"
→ ActionCambiarHorario
→ Bot: "Tienes una cita el 10/01 a las 14:00. ¿Para qué día quieres cambiarla?"
→ flujo_activo = "cambiar_fecha"

Usuario: "para el martes 6"
→ ActionConfirmarFechaCambio
→ flujo_activo = "cambiar_hora"
→ Bot: "Horarios disponibles: 09:00, 10:00... ¿A qué hora?"

Usuario: "las once"
→ ActionConfirmarHoraCambio
→ PUT /citas/{id}
→ Bot: "✅ Cita cambiada a 06/01 a las 11:00"
```

---

## 🛠️ Correcciones implementadas

### Bug #1: Fecha con día explícito
**Problema:** "viernes 15" extraía el próximo viernes (02/01) en lugar del día 15  
**Solución:** Reordenada lógica en `extraer_solo_fecha()` para priorizar números explícitos sobre días de la semana

### Bug #2: Hora en texto natural
**Problema:** "diez y media" no se reconocía (solo "10:30" funcionaba)  
**Solución:** Agregados diccionarios en `extraer_solo_hora()`:
```python
horas_texto = {'una': 1, 'dos': 2, ..., 'diez': 10, ..., 'veintitrés': 23}
minutos_texto = {'media': 30, 'cuarto': 15, 'y media': 30, 'y cuarto': 15}
```

### Bug #3: Cambio de cita saltaba paso de hora
**Problema:** Al cambiar cita, el bot no pedía la hora (completaba el cambio con solo la fecha)  
**Solución:** Dividido `ActionCambiarHorario` en dos acciones:
- `ActionConfirmarFechaCambio` - Extrae fecha, pide hora
- `ActionConfirmarHoraCambio` - Extrae hora, ejecuta cambio

---

## 🧪 Testing

Para probar el sistema modularizado:

```bash
# Reiniciar contenedor de acciones
docker compose restart rasa-actions

# Ver logs de acciones
docker compose logs -f rasa-actions

# Verificar registro de acciones
docker compose logs rasa-actions | grep "Re-registered"
```

**Acciones esperadas registradas (19):**
- action_set_contexto
- action_normalizar_servicio
- action_reservar_cita
- action_confirmar_hora_reserva
- action_cambiar_horario
- action_seleccionar_cita_cambio
- action_confirmar_fecha_cambio
- action_confirmar_hora_cambio
- action_cancelar_cita
- action_seleccionar_cita_cancelar
- action_procesar_confirmacion_cancelar
- action_consultar_citas_usuario
- action_listar_servicios
- action_mostrar_horarios
- action_mostrar_ubicacion
- action_info_negocio
- action_mostrar_disponibilidad
- action_responder_bot_challenge
- action_fallback_inteligente

---

## 📝 Mantenimiento

### Añadir nueva acción de consulta
1. Crear clase en `consultas.py`
2. Añadir import y nombre en `__init__.py`
3. Registrar en `domain.yml`

### Añadir nuevo flujo multi-paso
1. Crear archivo nuevo (ej: `notificaciones.py`)
2. Definir valores de `flujo_activo` (ej: `notif_config`, `notif_confirm`)
3. Añadir redirecciones en `ActionFallbackInteligente`
4. Actualizar `__init__.py` y `domain.yml`

### Modificar parsing de fecha/hora
1. Editar `extractores.py` → métodos de `ExtractorFechaHora`
2. Reiniciar contenedor: `docker compose restart rasa-actions`
3. Probar con: `docker compose logs -f rasa-actions`

---

## 📦 Backup

El archivo original está respaldado en:
- `actions_backup.py` (1996 líneas - versión pre-refactorización)

Para restaurar en caso de emergencia:
```bash
cd rasa_model/actions
cp actions_backup.py actions.py
docker compose restart rasa-actions
```

---

## 🎯 Beneficios de la modularización

✅ **Mantenibilidad**: Cada módulo tiene responsabilidad única  
✅ **Legibilidad**: 130-200 líneas por archivo vs 2356 en uno solo  
✅ **Reusabilidad**: Funciones en `utils.py` y `extractores.py` compartidas  
✅ **Testing**: Más fácil probar módulos individuales  
✅ **Colaboración**: Varios devs pueden trabajar en paralelo sin conflictos  
✅ **Debugging**: Logs más claros con nombres de módulos  

---

## ⚠️ Errores corregidos adicionales

### Bug #4: Endpoints incorrectos
**Problema:** Código usaba `/servicios/negocio/{id}` pero el backend expone `/negocios/{id}/servicios` (404 Not Found)  
**Solución:** Corregidos endpoints en `actions.py`, `contexto.py`, `consultas.py`

### Bug #5: Cache de Python con código antiguo
**Problema:** Archivos `.pyc` cacheados ejecutaban código del backup eliminado  
**Solución:** Eliminado `__pycache__` y `actions_backup.py` del contenedor

### Bug #6: GET /citas con path param inexistente
**Problema:** Código usaba `/citas/cliente/{id}` pero el endpoint correcto es `/citas?cliente_id={id}`  
**Solución:** Corregidos en `cambios.py` y `cancelaciones.py` para usar query parameters

### Bug #7: Salto automático de fecha
**Problema:** Si "sábado 17" no tiene horarios, el bot saltaba automáticamente a lunes 19  
**Solución:** Eliminado salto automático en `extractores.py` - ahora avisa "No hay horarios para ese día"

---

## 📌 Siguientes pasos sugeridos

1. ✅ ~~Refactorizar actions.py~~ (COMPLETADO)
2. ✅ ~~Corregir endpoints del backend~~ (COMPLETADO)
3. ✅ ~~Limpiar cache de Python~~ (COMPLETADO)
4. ✅ ~~Implementar hora en texto natural~~ (COMPLETADO)
5. 🔄 Crear tests unitarios para `ExtractorFechaHora`
6. 🔄 Documentar API endpoints del backend
7. 🔄 Añadir logging estructurado (JSON) para mejor observabilidad
