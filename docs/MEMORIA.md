# Memoria Técnica - Sector Mind AI

## 📋 Introducción

**Sector Mind AI** es una plataforma de gestión de reservas inteligente con IA conversacional para pequeños negocios (peluquerías, clínicas dentales, fisioterapia). Elimina la fricción de formularios web permitiendo reservas por voz y texto natural.

---

## 🏷️ Evolución por Versiones

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
**Fecha:** Diciembre 20, 2025 ← **ESTADO ACTUAL**

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

## 📊 Comparativa v0.1.0 vs v0.4.0

| Aspecto | v0.1.0 | v0.4.0 | Mejora |
|---------|--------|--------|--------|
| **BD** | SQLite | PostgreSQL | ACID + escalable |
| **Concurrencia** | 1 writer | Multi-cliente | Production-ready |
| **Containerización** | Manual | Docker Compose | Reproducible |
| **Setup Time** | 30+ min | 2 min | -93% |
| **Testing** | ❌ Ninguno | 104 tests | Confiable |
| **Entorno** | ≠ Producción | = Producción | Sin sorpresas |
| **CI/CD** | ❌ No | ✅ GitHub Actions | Automatizado |

---

## 💻 Flujo Actual de Desarrollo (v0.4.0)

### Inicio de Sesión

**Opción A: VS Code Action Button (Recomendado)**
```
🚀 START → Click
```
Resultado: Stack completo en 2 minutos
- Backend: http://localhost:5000
- PostgreSQL: Conectado
- Rasa: http://localhost:5005

**Opción B: Terminal**
```bash
docker-compose up -d
```

### Ejecutar Tests

**Opción A: VS Code**
```
🧪 TESTS → Click
```

**Opción B: Terminal**
```bash
.\run_tests.ps1                    # Todos (104)
.\run_tests.ps1 -BackendOnly       # Solo backend (75)
.\run_tests.ps1 -RasaOnly          # Solo Rasa (29)
.\run_tests.ps1 -Coverage          # Con reporte HTML
```

**Output Esperado:**
```
[BACKEND] 75 tests passed ✅
[RASA] 29 tests passed ✅
[TOTAL] 104 tests passed ✅
```

### Cierre de Sesión

**Opción A: VS Code**
```
🛑 STOP → Click
```

**Opción B: Terminal**
```bash
.\stop_docker.ps1
```

---

## 🎙️ Próximos Pasos (v0.5.0+)

### **v0.5.0 - Urgencias y Habla Avanzada** (Enero)
- Detección de urgencias por palabras clave más exactas
- Variaciones lingüísticas (sinónimos, regiones corporales, intensidades)
- Flujos conversacionales mejorados
- Usar JWT y React si las jefas lo recomiendan


---

## 🚀 Roadmap General

| Versión | Fecha | Foco |
|---------|-------|------|
| **v0.4.0** | ✅ Dec 20 | Profesionalización Docker |
| **v0.5.0** | Jan 10 | Urgencias + Habla Avanzada |
| **v0.5.1** | Jan 24 | Reservas por Voz |
| **v0.5.2** | Feb 7 | Contexto Profundo |
| **v0.6.0** | Feb 28 | Dashboard Admin |
| **v1.0.0** | Mar 31 | SaaS Multi-Tenant |

---

## 📋 Criterios de Aceptación

Cada release debe cumplir:
1. ✅ 100% tests pasando
2. ✅ Documentación actualizada
3. ✅ Demo funcional

---

**Actualizado:** 20 Diciembre 2025  
**Versión Actual:** v0.4.0 (Production-Ready)  
**Estado:** ✅ Profesionalización Completa
  - 24 intents iniciales (distribuidos entre dentista, peluquería, fisioterapia)
  - Extracción de entities (servicios, fechas, tipos de urgencia)
- **Rasa Actions Custom:** 7 acciones personalizadas para conectar NLU con lógica de negocio
  - `ActionSetContexto`: Detecta tipo de negocio
  - `ActionNormalizarServicio`: Fuzzy matching de servicios
  - `ActionMostrarDisponibilidad`: Consulta horarios
  - `ActionReservarCita`: Creación de citas
  - `ActionCancelarCita`: Cancelación de citas
  - `ActionInfoNegocio`: Información del negocio
  - `ActionResponderBotChallenge`: Respuestas contextuales
- **Sistema de Contexto:** Detección inteligente de tipo de negocio (dentista/peluquería/fisioterapia)
- **Validación Contextual:** El bot rechaza automáticamente servicios incompatibles
  - Ejemplo: No permite corte de cabello en clínica dental
- **Interfaz de Voz:** Integración de Web Speech API (STT/TTS) en frontend
- **Reconocimiento Avanzado:** Detección de intenciones complejas y flexibilidad en expresiones del usuario

#### 🎯 Motivo de la Versión
Transformar un sistema de formularios tradicional en una **interfaz conversacional inteligente**. Permitir a usuarios interactuar de forma natural sin conocer estructura de comandos.

#### ⚠️ Complicaciones Identificadas
1. **Comunicación Procesos Python:** Rasa y Flask corren como procesos separados
   - Necesidad de IPC (Inter-Process Communication) vía HTTP
   - Latencia adicional entre llamadas
2. **Dependencias Conflictivas:**
   - Rasa requiere TensorFlow 2.x
   - Backend requiere Flask + psycopg2
   - python-Levenshtein necesita compilación (gcc)
   - → Conflictos de versiones en requirements.txt
3. **Training y Actualización de Modelo:** Cambios en NLU requieren reentrenamiento manual
4. **Testing de Acciones:** Difícil mockar llamadas HTTP entre servicios
5.**Docker y PostgreSQL:** El cambio fue más difícil de lo imaginado habiendo que tocar muchas líneas de código y archivos.
