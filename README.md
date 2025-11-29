# **Sector Mind AI (v0.2.0)**

**Plataforma de gestión de reservas inteligente con asistencia conversacional multimodal.**

---

## 📋 **Estado del Proyecto**

El proyecto ha evolucionado a la versión **v0.2.0 (Beta Funcional)**.
Se han integrado capacidades multimedia y mejoras de experiencia de usuario (UX) significativas.

### ✅ Nuevas Funcionalidades (v0.2)
- **IA Multimodal (Voz):** El asistente ahora permite hablar por micrófono y responde con voz sintetizada (usando Web Speech API), además del chat de texto tradicional.
- **Gestión de Archivos:** Los usuarios pueden subir su **foto de perfil** real, que se guarda físicamente en el servidor (`/frontend/uploads`).
- **Seguridad UX:** El chat inteligente aparece bloqueado con un candado si el usuario no ha iniciado sesión.
- **Auto-Login:** Al registrarse, la sesión se inicia automáticamente.
- **Interfaz Mejorada:** Notificaciones visuales con *SweetAlert2* y navegación persistente entre negocios.

---

## 📂 **Estructura del Proyecto** 
El sistema sigue una arquitectura modular moderna:

```plaintext
SectorMindAI/
│
├── backend/              # API Flask (lógica principal)
│   ├── routes/           # Endpoints (Auth, Negocios, Citas)
│   ├── app.py            # Punto de entrada del servidor
│   ├── logic.py          # Algoritmos de disponibilidad de horarios
│   └── manage_db.py      # Script maestro para gestión de Base de Datos
│
├── frontend/             # Cliente Web
│   ├── index.html        # Home (Buscador y Login)
│   └── negocio.html      # Página de detalle y Chatbot específico
│
├── database/             # Base de datos y esquema
│   ├── schema.sql        # Plano de la base de datos
│   └── tfg_data.db       # Archivo de datos (SQLite)
│
└── rasa_model/           # Inteligencia Artificial (Rasa)
  ├── actions/          # Código Python que ejecuta el bot (consultar API)
  ├── data/             # Ejemplos de entrenamiento (NLU, Stories)
  └── domain.yml        # Configuración del dominio del bot
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
## 🧪 **Cómo probar la demo (v0.1)** 

### Usuarios de desarrollo disponibles

✨ ¡SISTEMA RESTAURADO COMPLETAMENTE! ✨
  -> Login Propietario: propietario@sectormind.com / p
  -> Login Cliente:     cliente@sectormind.com / u
1. Abre tu navegador en http://localhost:5000. 
2. **Login:** Pulsa "Iniciar Sesión" (o regístrate como nuevo usuario). 
2. **Explorar:** Haz clic en una tarjeta de negocio (ej. "Peluquería Estilo"). 
2. **Interactuar:** 
- Pulsa **"Chatear"** para escribir. 
- Pulsa **"Hablar"** para usar tu micrófono (Solo Chrome). 
- *Nota: Si el bot no entiende algo complejo, recuerda que está en fase de entrenamiento.* 

🛠 **Desarrollo y Contribución** 
### **Comandos útiles manuales** 
Entrenar el modelo de IA: 

Si modificas archivos en rasa\_model/data/: cd rasa\_model 

rasa train 

Resetear base de datos: 

Si cambias el schema.sql o quieres limpiar datos: python -m backend.manage\_db 

*Proyecto desarrollado como parte de TFG/Investigación en IA Conversacional.* 
