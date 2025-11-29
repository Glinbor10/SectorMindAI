# Historial de Cambios (Changelog)

Todas las modificaciones notables en el proyecto Sector Mind AI se documentarán en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/), y este proyecto se adhiere al versionado semántico.

## [v0.2.0] - 2025-11-29 (Mejoras UX, Voz y Multimedia)

### 🚀 Novedades (Added)
- **Agente IA Multimodal:** Implementación de reconocimiento de voz (Speech-to-Text) y síntesis de voz (Text-to-Speech) mediante Web Speech API en la vista de negocio.
- **Sistema de Archivos:** Soporte para subida física de imágenes de perfil (`multipart/form-data`) con almacenamiento en carpeta local `frontend/uploads`.
- **UX Avanzada:** Integración de **SweetAlert2** para notificaciones visuales modernas en lugar de alertas nativas.
- **Control de Acceso:** Pantalla de bloqueo ("Lock Screen") sobre el agente de IA que obliga a iniciar sesión para interactuar.
- **Navbar Unificado:** Diseño consistente de la barra de navegación en todas las vistas, mostrando avatar y menú de usuario.
- **Auto-Login:** Al registrarse, el usuario inicia sesión automáticamente.

### 🔧 Cambios (Changed)
- **Script `manage_db.py`:** Reescrito totalmente. Ahora limpia la carpeta `uploads`, reinicia la DB y crea usuarios con emails válidos y fotos de demostración.
- **Persistencia de Navegación:** Corregido el flujo de selección de negocio. Ahora se guarda correctamente el negocio seleccionado en `localStorage` al hacer clic.
- **Gestión de Errores API:** Mejorado el manejo de errores HTTP 404 y 500 en los endpoints de usuarios.

### 🐛 Correcciones (Fixed)
- Solucionado error `500 Internal Server Error` cuando se intentaba actualizar un usuario inexistente (ahora devuelve 404).
- Corregida la validación de emails en el script de población de datos (se usan emails con formato válido `user@domain.com`).

---

## [v0.1.0] - 2025-11-28 (Versión Funcional / Prototipo)

### 🚀 Novedades (Added)

**Infraestructura Base:**
- Automatización de base de datos: Script `manage_db.py` para resetear y poblar tablas en un solo paso.
- Automatización de arranque: Script `start_services.bat` y tareas de VS Code (`tasks.json`) para ejecución simultánea de servicios.

**Backend (Flask API):**
- Servidor Flask configurado con soporte CORS para permitir peticiones locales.
- Modularización de rutas mediante Blueprints (auth, negocios, citas).

**Base de Datos SQLite Completa:**
- Tabla usuarios con roles (cliente/propietario) y contraseñas hasheadas.
- Tabla negocios vinculada a propietarios, con campos para foto_url, direccion y descripcion.
- Tablas relacionales para servicios, horarios_negocio y citas.
- Algoritmo de lógica de negocio (`logic.py`) para calcular disponibilidad en intervalos de 15 minutos.

**Frontend (Web Client):**
- Interfaz SPA simulada con HTML5 + Vanilla JS + Tailwind CSS.