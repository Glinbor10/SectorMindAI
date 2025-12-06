# **Sector Mind AI (v0.3.0)**

**Plataforma de gestión de reservas inteligente con asistencia conversacional multimodal y testing comprehensivo.**

---

## 📋 **Estado del Proyecto**

El proyecto ha alcanzado la versión **v0.4.0 (Context-Aware AI)**.
Sistema de reservas con IA contextual que adapta respuestas según el tipo de negocio (dentista/peluquería/fisioterapia), 126 tests automatizados y validación inteligente de servicios.

### ✅ Últimas Funcionalidades (v0.4.0)
- **Sistema de Contexto Inteligente:** Detección automática del tipo de negocio (dentista/peluquería/fisioterapia)
  - Respuestas contextuales específicas según el tipo de servicio
  - 24 intents especializados con protocolos de primeros auxilios
  - Validación automática: rechaza servicios incompatibles con el tipo de negocio
  - 37 tests con validación de contexto (100% passing)
- **Suite de Testing Completa:** 126 tests automatizados con cobertura global
  - Backend: 92% coverage (106 tests)
  - Rasa Actions: 37 tests con validación de contexto

### 🎯 Funcionalidades Principales (Sistema Completo)
- **IA Contextual por Tipo de Negocio:** Respuestas especializadas según contexto (dentista/peluquería/fisioterapia)
  - 🦷 **Dentista:** Urgencias dentales, protocolos de primeros auxilios, consejos específicos
  - 💇 **Peluquería:** Emergencias de imagen, desastres de tinte, eventos importantes
  - 🏥 **Fisioterapia:** Protocolo RICE, lesiones deportivas, dolor agudo
- **Reservas Automáticas End-to-End:** El agente IA completa reservas reales sin intervención manual
- **IA Multimodal (Voz):** Reconocimiento de voz y síntesis (Web Speech API)
- **Gestión de Archivos:** Sistema de subida de fotos de perfil con validaciones
- **Detección Inteligente:** Matching fuzzy de servicios y consultas en tiempo real
- **Interpretación NLU:** Procesamiento de fechas en lenguaje natural ("mañana", "el lunes")

---

## 📂 **Estructura del Proyecto** 
El sistema sigue una arquitectura modular moderna:

```plaintext
SectorMindAI/
│
├── .venv/                # Entorno virtual Python
├── .vscode/              # Configuración de VS Code (tasks.json)
├── .github/              # Workflows de GitHub
│
├── backend/              # API Flask (lógica principal)
│   ├── routes/           # Endpoints (auth, citas, negocios, usuarios)
│   ├── tests/            # Suite de testing (106 tests, 92% coverage)
│   ├── app.py            # Punto de entrada del servidor
│   ├── logic.py          # Algoritmos de disponibilidad de horarios
│   ├── db.py             # Gestión de conexiones SQLite
│   └── manage_db.py      # Script maestro para gestión de BD
│
├── frontend/             # Cliente Web
│   ├── index.html        # Home (Buscador y Login)
│   ├── detalle.html      # Página de detalle de negocio
│   ├── perfil.html       # Gestión de perfil de usuario
│   ├── app.js            # Lógica JavaScript del cliente
│   └── uploads/          # Fotos de perfil (generadas en runtime)
│
├── database/             # Base de datos y esquema
│   ├── schema.sql        # Plano de la BD (5 tablas relacionales)
│   └── tfg_data.db       # Archivo de datos SQLite
│
├── rasa_model/           # Inteligencia Artificial (Rasa)
│   ├── actions/          # 7 Custom actions (Python)
│   │   └── actions.py    # Lógica de las acciones custom
│   ├── tests/            # Tests de Rasa (17 tests, 50% coverage)
│   ├── data/             # Ejemplos de entrenamiento
│   │   ├── nlu.yml       # Intenciones y entidades
│   │   ├── stories.yml   # Historias conversacionales
│   │   └── rules.yml     # Reglas de diálogo
│   ├── domain.yml        # Configuración del dominio del bot
│   ├── config.yml        # Pipeline de NLU y políticas
│   ├── credentials.yml   # Credenciales de canales
│   └── endpoints.yml     # Configuración de endpoints
│
├── docs/                 # Documentación técnica
│   ├── MEMORIA.md        # Memoria técnica completa
│   ├── CHANGELOG.md      # Historial de cambios por versión
│   └── RASA.md           # Documentación específica de Rasa
│
├── htmlcov/              # Reportes de coverage (generado)
│   └── index.html        # Dashboard de cobertura de tests
│
├── pytest.ini            # Configuración de pytest y coverage
├── requirements.txt      # Dependencias Python del proyecto
└── README.md             # Este archivo
```
## 🚀 **Instalación y Puesta en Marcha** 
### **Prerrequisitos** 
- **Python 3.10** (Obligatorio para compatibilidad con Rasa). 
- **Git** (Para clonar el repo). 
1. ### **Preparar el Entorno** 
Ejecuta estos comandos en tu terminal (PowerShell) desde la carpeta raíz: 

- 1. Crear entorno virtual python -m venv .venv 
- 2. Activar entorno .\.venv\Scripts\Activate 
- 3. Instalar dependencias pip install --upgrade pip 

  pip install -r requirements.txt 
2. ### **Inicializar la Base de Datos** 
Antes de arrancar, necesitamos crear las tablas y el usuario administrador. Asegúrate de tener una terminal con Flask corriendo o simplemente ejecuta: 

- Esto borrará la DB antigua, creará las tablas y meterá datos de prueba python -m backend.manage\_db 
3. ### **Ejecutar el Sistema (Modo Fácil)** 
Si usas **VS Code**, el proyecto incluye una configuración automática. 

1. Pulsa Ctrl + Shift + P. 
1. Escribe "Run Task" (Ejecutar Tarea). 
1. Selecciona 🚀 **INICIAR TODO SECTOR MIND**. 

Esto abrirá automáticamente las 3 terminales necesarias: 

1. **Backend Flask** (Puerto 5000) 
1. **Rasa Actions** (Puerto 5055) 
1. **Rasa Core** (Puerto 5005) 
## 🧪 **Cómo probar la demo** 

### Usuarios de desarrollo disponibles

✨ ¡SISTEMA LISTO PARA USAR! ✨
```
Login Propietario: propietario@sectormind.com / p
Login Cliente:     cliente@sectormind.com / u
```
1. Abre tu navegador en http://localhost:5000. 
2. **Login:** Pulsa "Iniciar Sesión" (o regístrate como nuevo usuario). 
2. **Explorar:** Haz clic en una tarjeta de negocio (ej. "Peluquería Estilo"). 
2. **Interactuar:** 
- Pulsa **"Chatear"** para escribir. 
- Pulsa **"Hablar"** para usar tu micrófono (Solo Chrome). 
- *Nota: Si el bot no entiende algo complejo, recuerda que está en fase de entrenamiento.* 

---

## 📊 **Métricas de Calidad (v0.4.0)**

| Métrica | Valor |
|---------|-------|
| **Tests Totales** | 143 (106 backend + 37 rasa) |
| **Coverage Backend** | 92% |
| **Tests Context-Aware** | 37 (100% passing) |
| **Intents Contextuales** | 24 (8 dental + 7 salon + 9 physio) |
| **Validación de Contexto** | ✅ Activa |
| **Tasa de Éxito** | 100% (143/143) |

---

## 🧪 **Tests y Calidad del Código**

El proyecto cuenta con **123 tests automatizados** que validan toda la funcionalidad:

### **Ejecutar TODOS los tests del proyecto (más simple):**
```bash
pytest -v
```

### **Con reporte de cobertura completo:**
```bash
pytest --cov=backend --cov=rasa_model/actions --cov-report=html --cov-report=term
```

### **Comandos específicos:**
```bash
# Solo backend (106 tests)
pytest backend/tests/ -v

# Solo Rasa (17 tests)
pytest rasa_model/tests/ -v
```

### **Coverage actual del proyecto:**
- **Backend:** 92% (106 tests)
  - `routes/auth.py`: 98%
  - `routes/citas.py`: 92%
  - `routes/negocios.py`: 92%
  - `routes/usuarios.py`: 93%
  - `logic.py`: 92%
- **Rasa Actions:** 50% (17 tests con mocking)
- **Coverage Global:** 82%

El reporte HTML se genera en `htmlcov/index.html` para análisis detallado.

---

## 🛠 **Desarrollo y Contribución** 
### **Comandos útiles manuales** 
Entrenar el modelo de IA: 

Si modificas archivos en rasa\_model/data/: 
```bash
cd rasa_model 
rasa train
```

Resetear base de datos: 

Si cambias el schema.sql o quieres limpiar datos: 
```bash
python -m backend.manage_db
``` 

*Proyecto desarrollado como parte de TFG/Investigación en IA Conversacional.* 
