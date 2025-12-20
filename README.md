# **Sector Mind AI (v0.4.0)**

**Plataforma de gestión de reservas inteligente con asistencia conversacional multimodal, orquestación en Docker y persistencia profesional en PostgreSQL.**

---

## 📋 **Estado del Proyecto**

El proyecto ha alcanzado la versión **v0.4.0 (Profesionalización con Docker + PostgreSQL)**.
Sistema de reservas con IA contextual desplegable en contenedores, 104 tests automatizados con cobertura completa y base de datos relacional de nivel empresarial.

### ✅ Últimas Funcionalidades (v0.4.0)
- **Stack Dockerizado Profesional:** Orquestación de 4 microservicios (backend, postgres, rasa, rasa-actions) con composición declarativa
  - PostgreSQL 15-Alpine con persistencia garantizada
  - Aislamiento de red interno con comunicación segura entre servicios
  - Automatización de infraestructura mediante Docker Compose
- **Suite de Testing Integrada:** 104 tests pasando (75 backend + 29 Rasa)
  - Backend: 100% cobertura en rutas críticas
  - Rasa: Validación completa de acciones personalizadas
  - Ejecutable desde VS Code con botón 🧪 TESTS
- **Developer Experience (DX) Premium:** 
  - Action Buttons en VS Code: 🚀 START, 🛑 STOP, 🧪 TESTS
  - Scripts PowerShell automatizados
  - Gestión unificada de datos con manage_db.py
- **PostgreSQL como Estándar:** Migración completa de SQLite a PostgreSQL
  - Transacciones ACID garantizadas
  - RealDictCursor para resultados dict-like
  - Escalabilidad para producción

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

## 🏗️ **Arquitectura de Microservicios**

SectorMindAI implementa una arquitectura de microservicios containerizada para máxima escalabilidad y confiabilidad:

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │   Backend        │  │   PostgreSQL     │  │    Rasa    │ │
│  │   (Flask 5000)   │  │   (5432)         │  │   (5005)   │ │
│  │                  │  │   15-Alpine      │  │            │ │
│  │  - API REST      │  │                  │  │  - NLU     │ │
│  │  - Lógica        │  │  - ACID Trans.   │  │  - Diálogo │ │
│  │  - Auth          │  │  - Persistencia  │  │  - Reglas  │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
│          ▲                      ▲                    ▲        │
│          │                      │                    │        │
│          └──────────────────────┼────────────────────┘        │
│                                 │                             │
│          ┌──────────────────────────────────────┐             │
│          │  Rasa Actions Server (5055)          │             │
│          │  - Ejecuta lógica personalizada      │             │
│          │  - Comunica con Backend              │             │
│          └──────────────────────────────────────┘             │
│                                                               │
│  Red: sector_mind_net (aislada)                             │
│  Volúmenes: ./rasa_model, ./database (persistencia)         │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
                     Frontend (Web)
                  http://localhost:5000
```

### **Detalles de Servicios:**

| Servicio | Puerto | Imagen | Propósito |
|----------|--------|--------|----------|
| **Backend** | 5000 | `sectormindai-backend:latest` | API REST, lógica de negocio, autenticación |
| **PostgreSQL** | 5432 | `postgres:15-alpine` | Base de datos relacional con ACID |
| **Rasa** | 5005 | `rasa/rasa:3.6.2` | Motor de NLU y gestión de diálogo |
| **Rasa Actions** | 5055 | `sectormindai-rasa-actions:latest` | Servidor de acciones personalizadas |

---

## 📂 **Estructura del Proyecto** 
El sistema sigue una arquitectura modular moderna:

```plaintext
SectorMindAI/
│
├── .venv/                # Entorno virtual Python
├── .vscode/              # Configuración de VS Code (tasks.json)
│
├── backend/              # API Flask (lógica principal)
│   ├── routes/           # Endpoints (auth, citas, negocios, usuarios)
│   ├── tests/            # Suite de testing (75 tests, 100% passing)
│   ├── app.py            # Punto de entrada del servidor
│   ├── logic.py          # Algoritmos de disponibilidad de horarios
│   ├── db.py             # Gestión de conexiones PostgreSQL
│   ├── db_utils.py       # Utilities para adaptación de queries
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
│   └── schema.sql        # Plano de la BD (7 tablas relacionales)
│
├── rasa_model/           # Inteligencia Artificial (Rasa 3.6.13)
│   ├── actions/          # 11 Custom actions (Python)
│   │   ├── actions.py    # 6 core actions
│   │   ├── dentista_actions.py
│   │   ├── peluqueria_actions.py
│   │   └── fisioterapia_actions.py
│   ├── tests/            # 29 tests (100% passing)
│   ├── data/             # Ejemplos de entrenamiento por contexto
│   │   ├── nlu/          # 3 archivos NLU especializados
│   │   ├── stories/      # 3 archivos de historias por tipo
│   │   └── rules.yml
│   └── [config files]    # domain.yml, config.yml, etc.
│
├── docs/                 # Documentación técnica
│   ├── MEMORIA.md        # Memoria técnica completa
│   ├── CHANGELOG.md      # Historial de cambios por versión
│   └── RASA.md           # Documentación específica de Rasa
│
├── .env                  # Variables de entorno (PostgreSQL, puerto, etc.)
├── docker-compose.yml    # Orquestación de servicios
├── Dockerfile            # Construcción de imagen backend
├── pytest.ini            # Configuración de pytest
├── requirements.txt      # Dependencias Python (pinned versions)
│
├── run_tests.ps1         # Script unificado de tests (backend + Rasa)
├── start_docker.ps1      # Script para iniciar Docker Compose
├── stop_docker.ps1       # Script para detener Docker Compose
│
└── README.md             # Este archivo
```
## 🚀 **Uso Rápido (VS Code Action Buttons)**

### **Método Recomendado: Action Buttons**

El proyecto incluye botones configurados directamente en VS Code para máxima comodidad:

#### **Paso 1: Iniciar la Infraestructura**
1. Abre VS Code en la carpeta del proyecto
2. Busca el botón en la barra lateral: **🚀 START**
3. O ejecuta manualmente: `Ctrl + Shift + P` → `Run Task` → selecciona `🚀 INICIAR TODO SECTOR MIND`

Esto levanta automáticamente:
- ✅ **PostgreSQL** (puerto 5432)
- ✅ **Backend Flask** (puerto 5000)
- ✅ **Rasa Core** (puerto 5005)
- ✅ **Rasa Actions** (puerto 5055)

#### **Paso 2: Acceder a la Aplicación**
```
Frontend:    http://localhost:5000
API Backend: http://localhost:5000/api
Rasa:        http://localhost:5005
```

#### **Paso 3: Ejecutar Tests**
Desde VS Code: `Run Task` → **🧪 TESTS**

O desde PowerShell:
```powershell
.\run_tests.ps1                # Ambas suites (104 tests)
.\run_tests.ps1 -BackendOnly   # Solo backend (75 tests)
.\run_tests.ps1 -RasaOnly      # Solo Rasa (29 tests)
.\run_tests.ps1 -Coverage      # Con reporte HTML
```

#### **Paso 4: Detener Infraestructura**
Desde VS Code: `Run Task` → **🛑 STOP**

O desde PowerShell:
```powershell
.\stop_docker.ps1
```

---

### **Credenciales de Prueba**

```
Propietario (Admin):
  Email:    propietario@sectormind.com
  Password: p

Cliente (User):
  Email:    cliente@sectormind.com
  Password: c
```

---

## 🚀 **Instalación y Puesta en Marcha (Método Manual)**
### **Prerrequisitos**

- **Docker Desktop** (obligatorio para orquestación de microservicios)
  - Windows: [Docker Desktop para Windows](https://docs.docker.com/desktop/install/windows-install/)
  - Mac: [Docker Desktop para Mac](https://docs.docker.com/desktop/install/mac-install/)
  - Linux: [Docker Engine](https://docs.docker.com/engine/install/)

- **Python 3.10+** (para desarrollo local del backend sin Docker)

- **VS Code** (recomendado para usar los Action Buttons)

---

### **Instalación Rápida (Recomendado)**

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/SectorMindAI.git
cd SectorMindAI
```

2. **Verificar Docker**
```bash
docker --version
docker compose --version
```

3. **Levantar servicios con Action Button**
- Abre VS Code
- Busca `🚀 INICIAR TODO SECTOR MIND` en la barra inferior
- Espera a que todas las terminales muestren "✅ LISTO"

4. **Abrir en navegador**
```
http://localhost:5000
```

---

### **Instalación Manual (Desarrollo Local)**

Si prefieres no usar Docker:

1. **Crear entorno virtual**
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate
# Mac/Linux
source .venv/bin/activate
```

2. **Instalar dependencias**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. **Configurar PostgreSQL manualmente**
   - Instala [PostgreSQL 15](https://www.postgresql.org/download/)
   - Crea BD: `createdb sectormind_db`
   - Actualiza `.env` con credenciales locales

4. **Inicializar BD**
```bash
python -m backend.manage_db
```

5. **Ejecutar servicios en terminales separadas**

Terminal 1 - Backend:
```bash
python -m backend.app
```

Terminal 2 - Rasa:
```bash
cd rasa_model
rasa run --enable-api --cors "*"
```

Terminal 3 - Rasa Actions:
```bash
cd rasa_model
rasa run actions
``` 
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
| **Tests Totales** | 104 (75 backend + 29 rasa) |
| **Tests Pasando** | 104/104 (100%) ✅ |
| **Coverage Backend** | 100% en rutas críticas |
| **Coverage Rasa** | 100% en acciones |
| **Tasa de Éxito** | 100% (104/104) |
| **Base de Datos** | PostgreSQL 15-Alpine |
| **Servicios Containerizados** | 4 (backend, postgres, rasa, rasa-actions) |
| **Tiempo de Deploy** | ~30 segundos con Docker Compose |



## 🧪 **Tests y Calidad del Código**

El proyecto cuenta con **104 tests automatizados** que validan toda la funcionalidad dentro de Docker:

### **Ejecutar TODOS los tests (Recomendado):**
```bash
.\run_tests.ps1
```
Resultado: `[OK] Total: 104 tests passed`

### **Con reporte de cobertura:**
```bash
.\run_tests.ps1 -Coverage
```

### **Ejecuciones Selectivas:**
```bash
.\run_tests.ps1 -BackendOnly   # 75 tests del API
.\run_tests.ps1 -RasaOnly      # 29 tests de IA
.\run_tests.ps1 -Verbose       # Con output detallado
```

### **Cobertura de Tests:**

| Módulo | Tests | Estado |
|--------|-------|--------|
| **Backend API** | 75 | ✅ 100% Passing |
| **Rasa Actions** | 29 | ✅ 100% Passing |
| **Total** | 104 | ✅ 100% Passing |

**Nota:** Los tests se ejecutan dentro del contenedor backend con BD PostgreSQL dedicada. Cada test es independiente y limpia su estado automáticamente.

---

## 🛠 **Desarrollo y Contribución** 

### **Workflow de Desarrollo (con Docker)**

#### **1. Iniciar el Stack**
```bash
docker-compose up -d
```

#### **2. Hacer cambios en el código**
- Backend: Edita archivos en `backend/`
- Rasa: Edita en `rasa_model/`
- Frontend: Edita en `frontend/`

**Hot Reload:**
- Backend: Reinicia automáticamente si editas archivos (modo debug)
- Rasa: Requiere reentrenamiento (`rasa train`)
- Frontend: Recarga en navegador (cache limpio con Ctrl+F5)

#### **3. Entrenar modelo Rasa (si modificas archivos de IA)**
```bash
docker-compose exec rasa rasa train
```

#### **4. Ejecutar tests**
```bash
.\run_tests.ps1
```

#### **5. Resetear base de datos**
```bash
docker-compose exec backend python -m backend.manage_db
```

#### **6. Inspeccionar logs**
```bash
docker-compose logs -f backend   # Backend logs
docker-compose logs -f rasa      # Rasa core logs
docker-compose logs -f postgres  # PostgreSQL logs
```

---

### **Comandos Docker Útiles**

```bash
# Ver estado de servicios
docker-compose ps

# Acceder a terminal del backend
docker-compose exec backend bash

# Ver variables de entorno del backend
docker-compose exec backend env | grep DATABASE

# Limpiar todo (contenedores + volúmenes)
docker-compose down -v

# Rebuild de imágenes
docker-compose build --no-cache
```

---

### **Workflow de Desarrollo: Trunk-Based Development**

El proyecto utiliza **trunk-based development** con integración continua automática:

```
trunk (rama principal de desarrollo)
  │
  ├─ Commit 1 (feature X)
  │   ↓ [Automático: CI/CD - Tests + Lint]
  │   ✅ Pass → Merge a main
  │
  ├─ Commit 2 (fix bug Y)
  │   ↓ [Automático: CI/CD - Tests + Lint]
  │   ✅ Pass → Merge a main
  │
  └─ Commit N
      ↓ [Automático: CI/CD - Tests + Rasa Validation]
      ✅ Pass → Merge a main (Release)
```

#### **Flujo de Trabajo:**

1. **Hacer cambios en `trunk`**
```bash
git checkout trunk
git pull origin trunk
# ... editar código ...
git add .
git commit -m "feat: descripción clara"
```

2. **Push a trunk (automático CI/CD)**
```bash
git push origin trunk
```

3. **Verificación automática (GitHub Actions):**
   - ✅ **Lint Flake8:** Validación de sintaxis Python
   - ✅ **Backend Tests:** 75 tests pytest
   - ✅ **Rasa Validation:** domain.yml, nlu.yml, stories.yml
   - ✅ **Rasa NLU Test:** Cross-validation de modelo

4. **Si todo pasa → Merge a main (Release)**
```bash
git checkout main
git merge trunk
git tag v0.4.x  # Opcional: versionar
git push origin main --tags
```

#### **Ventajas del Flujo Trunk-Based:**
- ✅ Cambios en master/main continuamente
- ✅ CI/CD valida automáticamente
- ✅ Sin dead branches ni conflictos crónicos
- ✅ Deploy frecuente (daily releases posibles)
- ✅ Máximo 5 commits de diferencia entre trunk y main

---

### **Stack Técnico Profesional**

| Capa | Tecnología | Versión |
|------|-----------|---------|
| **Frontend** | HTML5 + Vanilla JS + Tailwind | Latest |
| **Backend API** | Flask | 3.0.0 |
| **Base de Datos** | PostgreSQL | 15-Alpine |
| **Motor IA** | Rasa | 3.6.13 |
| **Orquestación** | Docker Compose | 2.x |
| **Testing** | pytest + unittest.mock | 7.4.3 |
| **CI/CD Ready** | Dockerfile multi-stage | ✅ |

---

*Proyecto desarrollado con enfoque profesional siguiendo mejores prácticas de DevOps, testing y arquitectura cloud-native.*
