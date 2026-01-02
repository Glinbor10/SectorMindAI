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

### **v0.5.0 - Refactorización Rasa y Flujo Propietario**
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
- ✅ Sistema de tests robusto: 101 tests (89 backend + 12 Rasa acciones)

**Detalles Técnicos:**
1. **Arquitectura Modular Rasa:** 9 archivos especializados con responsabilidades claras
   - `extractores.py`: Parsing de fechas/horas naturales con soporte de espacios
   - `reservas.py`, `cambios.py`, `cancelaciones.py`: Flujos multi-paso
   - `actions.py`: Cerebro central con ActionFallbackInteligente (421 líneas)
2. **Gestión de Urgencias Contextual:** Respuestas adaptadas por tipo de negocio
3. **FuzzyWuzzy:** Detección de servicios con errores ("tinti" → "Tinte")
4. **Frontend Avanzado:** Calendario mensual interactivo con validación en tiempo real
5. **Tests Actualizados:** Tests de stories deshabilitados, solo unitarios (más confiables)

**Métricas:**
- 101 tests: 100% passing (89 backend + 12 Rasa)
- Reducción 82% en actions.py (2356 → 421 líneas)
- 9 módulos Rasa especializados
- Producción estable ✅


---

## 💻 Flujo Actual de Desarrollo (v0.5.0)

### Flujo de trabajo como propietario

1. Inicia sesión como propietario.
2. Gestiona servicios, horarios y clientes desde la plataforma.
3. Accede a la gestión de citas y visualiza el historial de clientes.
4. El bot de IA responde a preguntas sobre el negocio, servicios y urgencias específicas.
5. Las reservas y consultas se gestionan de forma centralizada usando Rasa y metadatos.
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
| **v0.5.1** | (previsto) Feb, 2026 | Contexto Profundo |
| **v0.6.0** | (previsto) Ene, 2026 | Reservas por Voz correctamente |
| **v1.0.0** | (previsto) Feb/Mar, 2026 | SaaS Multi-Tenant |

---

## 📋 Criterios de Aceptación

Cada release debe cumplir:
1. ✅ 100% tests pasando
2. ✅ Documentación actualizada
3. ✅ Demo funcional

---

**Actualizado:** 20 Diciembre 2025
**Versión Actual:** v0.5.0 (Refactorización Rasa + Propietario)  
**Estado:** ✅ Refactorización en marcha y flujo propietario completo
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
