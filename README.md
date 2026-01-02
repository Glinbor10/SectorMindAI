
# **Sector Mind AI (v0.5.0)**
## 🐳 **¿Cómo funciona Docker en SectorMindAI?**

SectorMindAI utiliza Docker y Docker Compose para orquestar todos los servicios necesarios (backend, base de datos, IA conversacional y acciones personalizadas) de forma profesional, reproducible y persistente.

### 1. Orquestación con Docker Compose

- El archivo `docker-compose.yml` define los 4 servicios principales:
  - **backend**: API Flask (servidor principal)
  - **db**: PostgreSQL 15-Alpine (base de datos relacional)
  - **rasa**: Motor de NLU y diálogo (IA)
  - **rasa-actions**: Acciones personalizadas de IA

- Cada servicio se ejecuta en su propio contenedor, pero todos comparten una red interna (`sector_mind_net`) para comunicarse de forma segura.

- Los volúmenes declarados (por ejemplo, `./database` para PostgreSQL) garantizan que los datos persisten aunque los contenedores se detengan o reinicien.

### 2. Scripts PowerShell para gestión sencilla

- **start_docker.ps1**: Levanta toda la infraestructura con un solo comando o botón en VS Code. Ejecuta `docker compose up -d --build`, asegurando que todo esté actualizado y corriendo.
- **stop_docker.ps1**: Detiene y elimina los contenedores de forma segura (`docker compose down`).
- **run_tests.ps1**: Ejecuta todos los tests (backend y Rasa) dentro de los contenedores, usando la misma base de datos y entorno que en producción.
- **manage_db.ps1**: Permite inicializar o resetear la base de datos manualmente, solo cuando es necesario (por ejemplo, tras cambios en el esquema).

### 3. Entrypoints y persistencia

- El backend tiene un `Dockerfile` y un `docker-entrypoint.sh` personalizado, que ahora solo arranca el servidor Flask (ya no borra ni repuebla la base de datos automáticamente, para evitar pérdida de datos).
- La base de datos PostgreSQL utiliza un volumen persistente, por lo que los datos no se pierden aunque se reinicie Docker o el sistema operativo.
- Los servicios de Rasa y Rasa Actions se levantan automáticamente y se comunican con el backend y la base de datos según la configuración de red y variables de entorno.

### 4. Flujo típico de trabajo

1. **Iniciar todo**: Ejecuta `start_docker.ps1` o el botón 🚀 START en VS Code.
2. **Desarrollar y testear**: Haz cambios en el código, ejecuta tests con `run_tests.ps1`.
3. **Detener todo**: Usa `stop_docker.ps1` o el botón 🛑 STOP.
4. **Persistencia**: Los datos de la base de datos y los modelos de IA se mantienen gracias a los volúmenes Docker declarados.

**Resumen:**
Docker Compose y los scripts PowerShell permiten levantar, detener, testear y mantener toda la infraestructura de SectorMindAI de forma profesional, con persistencia real de datos y máxima reproducibilidad. Solo es necesario inicializar la base de datos manualmente en casos excepcionales (nuevas migraciones o reseteo total).


**Plataforma de gestión de reservas inteligente con asistencia conversacional multimodal, orquestación en Docker y persistencia profesional en PostgreSQL.**

---


## 📋 **Estado del Proyecto**

El proyecto ha alcanzado la versión **v0.5.0 (Arquitectura modular + IA contextual + Frontend avanzado + Búsqueda de Clientes)**.
Sistema de reservas con IA contextual desplegable en contenedores, 104 tests automatizados (92 backend + 12 Rasa), base de datos relacional de nivel empresarial, frontend con calendario interactivo y búsqueda de clientes por email.


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
- **Intento de agradecimiento (`thanks`):** El bot reconoce y responde a agradecimientos en español (13 ejemplos, 3 respuestas)
- **Frontend avanzado:** Calendario interactivo para crear y editar citas visualmente
- **Búsqueda de Clientes por Email:** Autocomplete inteligente que muestra solo clientes (excluyendo propietarios), con fotos, nombres y emails
- **Corrección de Timezone:** Formato local de fecha/hora sin conversión UTC (elimina desplazamientos de horario)

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
│   ├── tests/            # Suite de testing (89 tests, 100% passing)
│   ├── app.py            # Punto de entrada del servidor
│   ├── logic.py          # Algoritmos de disponibilidad de horarios
│   ├── db.py             # Gestión de conexiones PostgreSQL
│   └── manage_db.py      # Script maestro para gestión de BD
│
├── frontend/             # Cliente Web
│   ├── index.html        # Home (Buscador y Login)
│   ├── detalle.html      # Página de detalle de negocio
│   ├── perfil.html       # Gestión de perfil de usuario
│   ├── gestion_negocio.html # Gestión de negocio con calendario
│   ├── app.js            # Lógica JavaScript del cliente
│   └── uploads/          # Fotos de perfil (generadas en runtime)
│
├── database/             # Base de datos y esquema
│   └── schema_postgres.sql # Plano de la BD (7 tablas relacionales)
│
├── rasa_model/           # Inteligencia Artificial (Rasa 3.6.2)
│   ├── actions/          # Acciones personalizadas (9 módulos)
│   │   ├── actions.py        # Cerebro central (421 líneas)
│   │   ├── utils.py         # Funciones comunes (106 líneas)
│   │   ├── extractores.py   # Parsing fechas/horas (150 líneas)
│   │   ├── contexto.py      # Inicialización (131 líneas)
│   │   ├── reservas.py      # Flujo reserva (132 líneas)
│   │   ├── cambios.py       # Flujo cambio (204 líneas)
│   │   ├── cancelaciones.py # Flujo cancelación (143 líneas)
│   │   ├── consultas.py     # Consultas sin flujos (209 líneas)
│   │   └── __init__.py      # Exports de módulos
│   ├── tests/            # 12 tests unitarios (100% passing)
│   ├── data/             # Ejemplos de entrenamiento por contexto
│   │   ├── nlu.yml           # Intents unificados (incluye thanks)
│   │   ├── stories.yml       # Flujos conversacionales
│   │   └── rules.yml         # Reglas globales
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
  Password: u
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



## 🧪 **Tests y Calidad del Código**

El proyecto cuenta con **104 tests automatizados** (92 backend + 12 Rasa) que validan toda la funcionalidad dentro de Docker:

### **Ejecutar TODOS los tests (Recomendado):**
```bash
.\run_tests.ps1
```
Resultado: `[OK] Total: 104 tests passed (92 backend + 12 Rasa)`

### **Con reporte de cobertura:**
```bash
.\run_tests.ps1 -Coverage
```

### **Ejecuciones Selectivas:**
```bash
.\run_tests.ps1 -BackendOnly   # 92 tests del API
.\run_tests.ps1 -RasaOnly      # 12 tests de IA
.\run_tests.ps1 -Verbose       # Con output detallado
```

### **Cobertura de Tests:**

| Módulo | Tests | Estado |
|--------|-------|--------|
| **Backend API** | 92 | ✅ 100% Passing |
| **Rasa Actions** | 12 | ✅ 100% Passing |
| **Total** | 104 | ✅ 100% Passing |

**Nota:** Los tests de stories están deshabilitados (solo unitarios). Los tests se ejecutan dentro del contenedor backend con BD PostgreSQL dedicada. Cada test es independiente y limpia su estado automáticamente.

**Tests Nuevos (v0.5.0 - Enero 2, 2026):**
- ✅ `test_buscar_usuarios_filtra_por_rol_cliente` - Verifica filtro de búsqueda solo clientes
- ✅ `test_post_citas_formato_iso_T` - Valida formato `YYYY-MM-DDTHH:MM` sin segundos
- ✅ `test_post_citas_con_usuario_id` - Valida alias `usuario_id` para `cliente_id`

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
| **Motor IA** | Rasa | 3.6.2 |
| **Orquestación** | Docker Compose | 2.x |
| **Testing** | pytest + unittest.mock | 7.4.3 |
| **CI/CD Ready** | Dockerfile multi-stage | ✅ |

---

*Proyecto desarrollado con enfoque profesional siguiendo mejores prácticas de DevOps, testing y arquitectura cloud-native.*

---

**Cambios v0.5.0 (Diciembre 20, 2025 - Enero 2, 2026):**
- ✅ Refactorización arquitectónica de Rasa: 9 módulos especializados, 82% reducción en actions.py (2356 → 421 líneas)
- ✅ Intento de agradecimiento (`thanks`) con 13 ejemplos y 3 respuestas
- ✅ Frontend con calendario interactivo para gestión de citas
- ✅ Tests de stories deshabilitados, solo unitarios (104 tests: 92 backend + 12 Rasa)
- ✅ **Búsqueda de Clientes por Email** (Enero 2):
  - Endpoint `GET /usuarios/buscar?q=<email>` filtra solo clientes
  - Autocomplete interactivo con dropdown visual
  - Validación: requiere seleccionar cliente antes de crear cita
- ✅ **Correcciones UX Frontend** (Enero 2):
  - Bug Timezone: Formato local sin conversión UTC
  - Modal Close: Limpieza correcta de campos
  - Response Parsing: Manejo seguro de respuestas vacías
