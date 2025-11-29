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

## 4. Próximos Pasos: Inteligencia y Ejecución (Fase v0.3)

Actualmente, el sistema cuenta con una interfaz avanzada y una infraestructura robusta, pero el modelo de IA tiene capacidades de ejecución limitadas. Los retos inmediatos son:

- **Perfeccionamiento del Slot Filling:**
    - *Problema Actual:* El bot reconoce intenciones pero puede perder datos (hora, servicio) en conversaciones largas o no estructuradas.
    - *Objetivo:* Implementar *Rasa Forms* para asegurar la recolección estricta de todos los datos necesarios antes de intentar una reserva.

- **Gestión de Contexto Complejo:**
    - *Objetivo:* Que el bot recuerde el contexto de conversaciones pasadas (ej: "quiero lo mismo de la última vez").

-- **Migración a Producción:**
    - *Objetivo:* Migrar de SQLite a PostgreSQL y desplegar en contenedores Docker.

### Usuarios de desarrollo disponibles

✨ ¡SISTEMA RESTAURADO COMPLETAMENTE! ✨
   -> Login Propietario: propietario@sectormind.com / p
   -> Login Cliente:     cliente@sectormind.com / u