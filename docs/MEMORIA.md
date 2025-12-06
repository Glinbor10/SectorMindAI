# Memoria Técnica - Sector Mind AI

## 1. Introducción y Objetivos

Sector Mind AI nace con el objetivo de modernizar la gestión de reservas en pequeños negocios (peluquerías, clínicas dentales, fisioterapia) mediante el uso de Inteligencia Artificial Conversacional. El sistema busca eliminar la barrera tecnológica de los formularios web tradicionales, permitiendo una interacción natural por voz y texto.

## 2. Arquitectura y Elección de Tecnologías

Para el desarrollo de la plataforma, se ha optado por una arquitectura modular desacoplada:

### 🧠 Motor Conversacional: Rasa Open Source
Se ha seleccionado Rasa frente a alternativas en la nube por su capacidad de ejecución local y privacidad de datos.
- **Estado Actual:** Configurado para detección de intenciones (NLU) y gestión de diálogo básica mediante reglas e historias.
- **Conectividad:** Se comunica con el backend a través de un *Action Server* dedicado.

### 🔌 Backend y API: Flask (Python)
Actúa como el orquestador central del sistema:
- **Gestión de Archivos:** Sistema de subida física de imágenes de perfil (`multipart/form-data`) almacenadas en servidor local.
- **Autenticación:** Sistema de usuarios seguro con roles (Cliente/Propietario).
- **Lógica de Negocio:** Algoritmos de disponibilidad horaria y gestión de base de datos SQLite.

## 3. Retos Técnicos y Soluciones (Evolución del Proyecto)

### Fase v0.1: Infraestructura y Conectividad (Pasado)
El objetivo inicial fue lograr que piezas tecnológicas dispares (Python, JS, SQLite, Rasa) se comunicaran entre sí sin errores.

- **A. Integración de Servicios:**
    - *Reto:* Rasa y Flask son procesos independientes que no comparten memoria.
    - *Solución:* Implementación de una arquitectura orientada a servicios (SOA) local usando REST API. El `action_server` de Rasa actúa como puente HTTP para consultar la base de datos de Flask.

- **B. Despliegue Local (Dependency Hell):**
    - *Reto:* Conflictos de versiones entre las librerías de IA (TensorFlow, Rasa) y el Backend web.
    - *Solución:* Aislamiento estricto con entornos virtuales y control de dependencias mediante `requirements.txt`.

### Fase v0.2: Experiencia de Usuario y Multimedia (Presente)
Una vez el sistema funcionaba, el reto fue hacerlo usable, seguro y moderno.

- **A. Interacción por Voz (Web Speech API):**
    - *Reto:* Permitir hablar con el bot sin latencia extrema ni costes de APIs en la nube.
    - *Solución:* Delegar el reconocimiento de voz (STT) y la síntesis (TTS) al navegador del cliente. Esto envía texto limpio al servidor, reduciendo drásticamente la carga de procesamiento y la latencia.

- **B. Persistencia y Seguridad:**
    - *Reto:* El sistema olvidaba qué negocio visitaba el usuario al recargar la página y permitía el uso anónimo de la IA.
    - *Solución:* Implementación de `localStorage` para mantener el estado de navegación y un sistema de "Lock Screen" (Pantalla de Bloqueo) que restringe el acceso al agente hasta que existe una sesión válida.

- **C. Gestión de Errores e Integridad:**
    - *Reto:* Inconsistencias entre la sesión del navegador y la base de datos tras reinicios (IDs de usuario obsoletos).
    - *Solución:* Blindaje de los endpoints de la API. Si un ID no existe, el servidor devuelve un 404 controlado que fuerza el cierre de sesión en el cliente, evitando bloqueos.

## 4. Calidad y Testing del Sistema

### A. Estrategia de Testing Implementada
El proyecto cuenta con **123 tests automatizados** distribuidos estratégicamente:

#### **Backend (106 tests - 92% coverage)**
- **test_auth.py (21 tests):** Validación completa de registro y login
  - Tests de seguridad: password hashing, no exposición de credenciales
  - Validación de uploads de archivos (foto de perfil)
  - Coverage: 98%

- **test_citas.py (21 tests):** Sistema de reservas
  - Tests de lógica de negocio: solapamientos, horarios, disponibilidad
  - Validación de estados (confirmado, cancelado)
  - Coverage: 92%

- **test_negocios.py (23 tests):** Gestión de negocios
  - CRUD completo con validaciones
  - Tests de relaciones (servicios, horarios, propietarios)
  - Coverage: 92%

- **test_usuarios.py (19 tests):** Perfiles de usuario
  - Sistema de actualización con file uploads
  - Validación de extensiones de archivos
  - Tests de seguridad (404 para usuarios inexistentes)
  - Coverage: 93%

- **test_logic.py (20 tests):** Algoritmos de disponibilidad
  - 11 tests para `verificar_solapamiento()`
  - 9 tests para `obtener_tramos_disponibles()`
  - Coverage: 92%

#### **Rasa Actions (17 tests - 50% coverage)**
Tests unitarios con mocking de API calls para las 7 acciones custom:
- ActionSetContexto, ActionNormalizarServicio
- ActionMostrarDisponibilidad, ActionReservarCita
- ActionInfoNegocio, ActionCancelarCita
- ActionResponderBotChallenge

### B. Técnicas de Testing Aplicadas
1. **Aislamiento de Tests:** Uso de BD temporales (`tempfile.mkstemp()`) para evitar contaminación entre tests
2. **Mocking de APIs:** `unittest.mock` para simular llamadas HTTP sin dependencias externas
3. **Test Fixtures:** Fixtures de pytest para configuración reutilizable
4. **Coverage Analysis:** Reporte HTML detallado con líneas específicas no cubiertas

### C. Comandos de Testing
```bash
# Ejecutar TODOS los tests del proyecto (123 tests: backend + Rasa)
pytest -v

# TODOS los tests con coverage completo y reporte HTML
pytest --cov=backend --cov=rasa_model/actions --cov-report=html --cov-report=term

# Solo backend (106 tests)
pytest backend/tests/ -v --cov=backend --cov-report=term-missing

# Solo Rasa (17 tests)
pytest rasa_model/tests/ -v

# Tests específicos por módulo
pytest backend/tests/test_auth.py -v        # 21 tests de autenticación
pytest backend/tests/test_citas.py -v       # 21 tests de reservas
pytest backend/tests/test_usuarios.py -v    # 19 tests de usuarios
```

## 5. Estado Actual: v0.3.0 (Producción-Ready con Testing Comprehensivo)

El sistema ha alcanzado un estado de **madurez enterprise-grade** con:

### ✅ Logros Completados
- **Infraestructura Robusta:** Arquitectura modular con separación clara de responsabilidades
- **IA Funcional:** Sistema de reservas automáticas end-to-end con NLU avanzado
- **Testing Comprehensivo:** 123 tests con 82% de coverage global
- **Calidad de Código:** Tests aislados, fixtures reutilizables, mocking de APIs
- **Documentación Completa:** README, MEMORIA y CHANGELOG actualizados

### 📊 Métricas de Calidad
- **Backend Coverage:** 92% (routes: 92-98%, logic: 92%)
- **Rasa Coverage:** 50% (17 tests unitarios con mocking)
- **Tiempo de Ejecución:** ~13 segundos para 123 tests
- **Tasa de Éxito:** 100% (123/123 tests passing)

## 6. Próximos Pasos: Optimización y Producción (Fase v0.4)

Actualmente el sistema está **production-ready** para despliegues locales. Los siguientes pasos son:

- **Perfeccionamiento del Slot Filling:**
    - *Objetivo:* Implementar *Rasa Forms* para asegurar la recolección estricta de todos los datos necesarios antes de intentar una reserva
    - *Beneficio:* Reducir errores de usuario y mejorar la tasa de conversión de reservas

- **Gestión de Contexto Complejo:**
    - *Objetivo:* Que el bot recuerde el contexto de conversaciones pasadas (ej: "quiero lo mismo de la última vez")
    - *Implementación:* Persistencia de slots en base de datos

- **Migración a Producción Cloud:**
    - *Objetivo:* Migrar de SQLite a PostgreSQL para entornos multi-usuario
    - *Infraestructura:* Desplegar en contenedores Docker con Docker Compose
    - *CI/CD:* Integración de tests automáticos en pipeline de despliegue

- **Incrementar Coverage de Rasa:**
    - *Objetivo:* Alcanzar 80%+ de coverage en actions mediante tests de integración completos
    - *Estrategia:* Tests de flujos completos sin mocking para validar integración real

- **Optimización de Performance:**
    - *Objetivo:* Reducir latencia de respuesta del bot a <500ms
    - *Implementación:* Caché de servicios y horarios, optimización de queries SQL

### Usuarios de desarrollo disponibles

✨ ¡SISTEMA RESTAURADO COMPLETAMENTE! ✨
   -> Login Propietario: propietario@sectormind.com / p
   -> Login Cliente:     cliente@sectormind.com / u