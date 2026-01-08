# Memoria Técnica - Sector Mind AI

## 📋 Introducción

**Sector Mind AI** es una plataforma de gestión de reservas inteligente con IA conversacional para pequeños negocios (peluquerías, clínicas dentales, fisioterapia). Elimina la fricción de formularios web permitiendo reservas por voz y texto natural.

---

## 🏷️ Evolución por Versiones

### **v0.0.1 - Estructura y uso de nuevas tecnologías**
**Fecha:** Octubre, 2025

**Logros:**
- ✅ Estructura: Backend, Frontend y Rasa.
- ✅ Primera toma de mano con las tecnologías a utilizar: Flask, Rasa, Python, JavaScript, libreías múltiples, etc.

**Retos:**
- ⚠️ Desarrollar la IA del proyecto para evitar pagos por APIs externas
- ⚠️ Varias horas y días entendiendo las tecnologías a alto nivel

---

### **v0.1.0 - Arquitectura Base (MVP)**
**Fecha:** Noviembre 28, 2025

**Logros:**
- ✅ Backend Flask modular (Blueprints)
- ✅ Base de datos SQLite relacional (7 tablas)
- ✅ Autenticación con roles (cliente/propietario)
- ✅ API REST completa
- ✅ Frontend SPA (HTML5 + JS)
- ✅ Script manage_db.py para seeding

**Retos:**
- ⚠️ Entorno inconsistente (instalación manual)
- ⚠️ SQLite con limitación de 1 writer (sin concurrencia)
- ⚠️ 3+ procesos en terminales separadas
- ⚠️ Sin testing automatizado

---

### **v0.2.0 - Inteligencia Conversacional**
**Fecha:** Noviembre 29, 2025

**Logros:**
- ✅ Rasa NLU integrado (24 intents iniciales)
- ✅ 7 Rasa Actions custom conectadas a backend
- ✅ Detección inteligente de tipo de negocio
- ✅ Web Speech API (STT/TTS)
- ✅ Validación contextual de servicios

**Retos:**
- ⚠️ Comunicación HTTP entre procesos Python
- ⚠️ Dependencias conflictivas (TensorFlow, Rasa vs Flask)
- ⚠️ Reentrenamiento manual del modelo
- ⚠️ Testing de acciones complejo

---

### **v0.3.0 - Testing Comprehensivo**
**Fecha:** Diciembre 6, 2025

**Logros:**
- ✅ 123 tests automatizados (106 backend + 17 Rasa)
- ✅ Coverage 92% en backend
- ✅ Sistema de contexto por tipo de negocio (24 intents)
- ✅ Fixtures dinámicos
- ✅ Reportes HTML de coverage

**Métricas:**
- Coverage global: 82%
- 123 tests: 100% passing
- 24 intents contextuales

---

### **v0.4.0 - Profesionalización con Docker y PostgreSQL**
**Fecha:** Diciembre 20, 2025

**Logros:**
- ✅ Docker Compose: 4 microservicios orquestados
  - Backend Flask
  - PostgreSQL 15-Alpine
  - Rasa Core
  - Rasa Actions Server
- ✅ Migración 100% SQLite → PostgreSQL
- ✅ 104 tests (75 backend + 29 Rasa) - 100% passing
- ✅ Action Buttons VS Code (🚀 START, 🛑 STOP, 🧪 TESTS)
- ✅ CI/CD automático (GitHub Actions + Trunk-based)
- ✅ Documentación profesional (README, CHANGELOG, RASA)

**Problemas Resueltos:**
1. **SQLite → PostgreSQL:** Adaptación de queries (? → %), fixtures dinámicos, RETURNING id
2. **Docker Build:** gcc + setuptools en Dockerfile
3. **Volume Mounting:** Agregado rasa_model en docker-compose.yml
4. **Fechas Hardcodeadas:** datetime.now() + timedelta para tests perpetuos
5. **CI/CD PostgreSQL:** Health checks + DATABASE_URL env var

**Métricas:**
- 104 tests: 100% passing
- 2 minutos setup (vs 30+ antes)
- Production-ready ✅

---

### **v0.5.0 - Refactorización Rasa, Búsqueda de Clientes y UX de Citas desde web de Propietario**
**Fecha:** Enero 2, 2026 ← **ESTADO ACTUAL**

**Logros:**
- ✅ **Refactorización arquitectónica de Rasa:** Modularización completa de actions.py
  - Dividido de 2356 líneas en 9 módulos especializados (reducción del 82%)
  - Módulos: `utils.py`, `extractores.py`, `contexto.py`, `reservas.py`, `cambios.py`, `cancelaciones.py`, `consultas.py`, `actions.py`
  - Eliminación de 1935 líneas de código duplicado
  - Mejor separación de responsabilidades y testing
- ✅ Flujo de trabajo completo como propietario (gestión de citas, servicios y clientes)
- ✅ Frontend con calendario interactivo para crear/editar citas visualmente
- ✅ Intent `thanks` para detección de agradecimientos (13 ejemplos, 3 respuestas)
- ✅ Corrección de bugs detectados en producción
- ✅ Uso de metadatos para identificar negocio y usuario en cada interacción
- ✅ Respuestas contextuales de urgencias según tipo de negocio
- ✅ FuzzyWuzzy para tolerancia a errores ortográficos en servicios
- ✅ Sistema de tests robusto: 104 tests (92 backend + 12 Rasa acciones) - **100% passing**

**Nuevas Funcionalidades (Enero 2):**
1. **Búsqueda de Clientes por Email:**
   - Endpoint `GET /usuarios/buscar?q=<email>` filtra por email (case-insensitive)
   - **Filtra solo usuarios con rol "cliente"** (excluye propietarios)
   - Autocomplete en formularios de crear/editar cita
   - Dropdown con foto, nombre y email del cliente
   - Mínimo 2 caracteres para activar búsqueda

2. **Corrección de Timezone (UTC Shift):**
   - Bug: `.toISOString()` convertía horarios locales a UTC, causando desplazamiento de -1 hora
   - Solución: Formateo manual local `YYYY-MM-DDTHH:MM` sin conversión UTC
   - Aplicado a: `loadAvailableSlots()`, `loadEditAvailableSlots()`, `handleCreateCita()`

3. **Mejoras en Creación de Citas:**
   - Acepta formato ISO `YYYY-MM-DDTHH:MM` (con y sin segundos)
   - Soporta `usuario_id` como alias de `cliente_id` en payload
   - Validación robusta: verifica servicio, cliente y fecha/hora antes de enviar
   - Manejo de respuestas JSON vacías (evita falso "Error de conexión")

4. **Refactorización Cierre de Modal:**
   - Corregido error null al cerrar modal (limpia inputs reales)
   - Resetea campos: email, id, nombre, resultados y mensaje seleccionado

**Detalles Técnicos:**
1. **Backend (routes/usuarios.py):** Filtro `rol = 'cliente'` en query LIKE
   ```sql
   SELECT id, nombre, email, foto_perfil_base64 FROM usuarios 
   WHERE LOWER(email) LIKE LOWER(%s) AND rol = 'cliente' LIMIT 10
   ```

2. **Frontend (gestion_negocio.html):**
   - Event listener con debounce 300ms en `cita-cliente-email`
   - Dropdown dinámico mostrando solo clientes
   - Almacena ID oculto para validación
   - Confirmación visual "✓ Cliente seleccionado"

3. **Tests Nuevos (92 tests totales):**
   - `test_post_citas_formato_iso_T`: Valida formato YYYY-MM-DDTHH:MM
   - `test_post_citas_con_usuario_id`: Valida alias usuario_id
   - `test_buscar_usuarios_filtra_por_rol_cliente`: Verifica filtro de rol

**Métricas:**
- 104 tests: 100% passing (92 backend + 12 Rasa)
- Reducción 82% en actions.py (2356 → 421 líneas)
- 9 módulos Rasa especializados
- 0 falsos positivos en búsqueda de clientes
- Producción estable ✅

---

### **v0.6.0 - Geolocalización de Negocios y Búsqueda por Proximidad**
**Fecha:** Enero, 2026

**Logros:**
- ✅ Sistema de geolocalización completo: base de datos, backend, frontend
- ✅ Fórmula Haversine para cálculo de distancia en tiempo real
- ✅ Integración con Nominatim (OpenStreetMap) para geocodificación
- ✅ Geolocalización del navegador con solicitud de permisos (30 segundos timeout)
- ✅ Visualización de distancias en tarjetas de negocios
- ✅ 3 métodos de entrada de ubicación (manual, GPS, reverse geocoding)
- ✅ Suite de 6 tests de geolocalización (100% passing)
- ✅ Test data con 3 negocios reales españoles (Madrid, Barcelona, Valencia)
- ✅ Documentación técnica en `docs/GEOLOCALIZACION.md`

**Retos Resueltos:**
1. **Permiso de Geolocalización:** Implementación correcta de `navigator.geolocation` con UI feedback (⏳ esperando)
2. **Precision de Coordenadas:** DECIMAL(10,8) y DECIMAL(11,8) para ~1.1 cm de precisión geográfica
3. **Line Endings en Docker:** Conversión CRLF→LF en `docker-entrypoint.sh`
4. **Fixtures Únicos en Tests:** Cambio de `time.time()` a `uuid.uuid4()` para evitar colisiones
5. **Rate Limiting Nominatim:** User-Agent requerido y respeto de límite ~1 req/segundo

**Métricas:**
- 116 tests totales: 100% passing (110 backend + 6 geo + 12 Rasa)
- Distancia Madrid→Valencia: 302.56 km (Haversine vs ~302 km real)
- Distancia Madrid→Barcelona: 505.10 km (Haversine vs ~505 km real)
- 3 ciudades españolas con coordenadas reales validadas
- 0 bugs en Docker post-fix line endings
- Producción estable ✅

---

### **v0.7.0 - Interfaz Adaptativa por Rol y Chat Discovery**
**Fecha:** Enero 8, 2026

**Logros:**
- ✅ Dos vistas separadas según rol:
   - **Cliente:** Header + búsqueda + grid de negocios + chat Discovery (Rasa Discovery, puerto 5006)
   - **Propietario:** Panel "Tus Negocios" sin chat ni búsqueda
- ✅ Conmutación instantánea sin recargar página al iniciar/cerrar sesión
- ✅ Refactor de autenticación en `index.html` (sin dependencia de `app.js`)
- ✅ Carga dinámica según rol: `loadBusinesses()` (cliente) y `loadMyBusinesses()` (propietario)
- ✅ Nuevo slogan orientado a accesibilidad: "Accesible y fácil, pensado para mayores."
- ✅ Separación de modelos Rasa:
   - **Rasa Discovery (nuevo):** Descubrimiento de negocios por ubicación/tipo (5006)
   - **Rasa Model (existente):** Gestión de citas completas (5005)

**Retos Resueltos:**
1) Conflicto de variable `currentUser` entre `index.html` y `app.js` → scopes separados y sincronización por `localStorage`.
2) Cambio de rol sin recarga → `window.updateRoleViews()` y `saveUserSessionIndex()` actualizan UI al instante.
3) Carga de negocios del propietario → `loadMyBusinesses()` se ejecuta al activar modo propietario.
4) Logout limpia vistas y estado → se vuelven a mostrar elementos de cliente.

**Métricas:**
- 116 tests totales (backend + geolocalización + Rasa Model): 100% passing.
- Cambio de rol < 50 ms percibido.
- 0 conflictos de variables globales tras refactor.


---



## 🚀 Roadmap General

| Versión | Fecha | Foco |
|---------|-------|------|
| **v0.0.1** | Oct, 2025 | Estructura y uso de nuevas tecnologías |
| **v0.1.0** | Nov 28, 2025 | Arquitectura Base (MVP) |
| **v0.2.0** | Nov 29, 2025 | Inteligencia Conversacional |
| **v0.3.0** | Dic 6, 2025 | Testing Comprehensivo |
| **v0.4.0** |  Dic 20, 2025 | Profesionalización Docker |
| **v0.5.0** | Dic/Ene, 2026 | Refactorización Rasa + Flujo Propietario |
| **v0.6.0** | Ene 6, 2026 | Geolocalización de Negocios ✅ |
| **v0.7.0** | Ene 8, 2026 | Interfaz Adaptativa + Rasa Discovery ✅ |
| **v1.0.0** | (previsto) Feb/Mar, 2026 | SaaS Multi-Tenant |

---

## 📋 Criterios de Aceptación

Cada release debe cumplir:
1. ✅ 100% tests pasando
2. ✅ Documentación actualizada
3. ✅ Demo funcional

---

**Actualizado:** 8 Enero 2026
**Versión Actual:** v0.7.0 (Interfaz Adaptativa + Rasa Discovery)  
**Estado:** ✅ 116 tests passing (backend + geo + Rasa Model)
  - 24 intents iniciales (distribuidos entre dentista, peluquería, fisioterapia)
  - Extracción de entities (servicios, fechas, tipos de urgencia)
- **Rasa Actions Custom:** 7 acciones personalizadas ("urgencias" que necesiten contexto) de cata tipo de negocio para conectar NLU con lógica de negocio
- **Sistema de Contexto:** Detección inteligente de tipo de negocio (dentista/peluquería/fisioterapia)
- **Validación Contextual:** El bot rechaza automáticamente servicios incompatibles
  - Ejemplo: No permite corte de cabello en clínica dental
- **Interfaz de Voz:** Integración de Web Speech API (STT/TTS) en frontend
- **Reconocimiento Avanzado:** Detección de intenciones complejas y flexibilidad en expresiones del usuario

#### 🎯 Motivo de la Versión
Transformar un sistema de formularios tradicional en una **interfaz conversacional inteligente**. Permitir a usuarios interactuar de forma natural sin conocer estructura de comandos.

#### ⚠️ Complicaciones Identificadas
1. **Comunicación Procesos Python:** Rasa y Flask corren como procesos separados, necesitan 3 contenedores corriendo.
2. **Dependencias Conflictivas(al trabajar con Docker dejaron de ser un problema):**
  - Rasa requiere TensorFlow 2.x
  - Backend requiere Flask + psycopg2 (para usar PostGreSQL con Python)
  - python-Levenshtein necesita compilación (gcc)
  - → Conflictos de versiones en requirements.txt
3. **Training y Actualización de Modelo:** Cambios en NLU requieren reentrenamiento manual
4. **Testing de Acciones:** Difícil mockar llamadas HTTP entre servicios
5. **Docker y PostgreSQL:** El cambio fue más difícil de lo imaginado habiendo que tocar muchas líneas de código y archivos.
6. **Deuda Técnica en Rasa (v0.5.0):** Se está realizando una refactorización profunda del módulo Rasa para eliminar la deuda técnica acumulada:
  - Centralización de toda la lógica de acciones en un único archivo y clase, evitando duplicidades.
  - Uso de metadatos para adaptar respuestas y lógica según el negocio y usuario.
  - Eliminación de archivos de acciones por tipo de negocio, simplificando el mantenimiento.
  - Respuestas contextuales y flujos más robustos para urgencias y reservas.
  - Reducción de errores, solapamientos y repetición de código.
  - El objetivo es facilitar la evolución futura y el testing, y evitar problemas de escalabilidad y mantenimiento.
