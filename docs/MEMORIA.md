
# Memoria Técnica - Sector Mind AI

## 1. Introducción y Objetivos

Sector Mind AI nace con el objetivo de modernizar la gestión de reservas en pequeños negocios (peluquerías, clínicas dentales, fisioterapia) mediante el uso de Inteligencia Artificial Conversacional. El sistema busca eliminar la barrera tecnológica de los formularios web tradicionales, permitiendo una interacción natural por voz y texto.

## 2. Arquitectura y Elección de Tecnologías

Para el desarrollo de la plataforma, se ha optado por una arquitectura modular desacoplada, separando la lógica de negocio (Backend), la interfaz de usuario (Frontend) y el motor de inteligencia (IA).

### 🧠 Motor Conversacional: Rasa Open Source

Se ha seleccionado Rasa frente a alternativas en la nube (como Dialogflow o Amazon Lex) por las siguientes razones estratégicas:

- **Control Total y Privacidad:** Al ser open-source, permite la ejecución local de todo el stack sin enviar datos sensibles de los clientes a terceros.
- **Acciones Personalizadas (Custom Actions):** Rasa ofrece una integración nativa con Python (rasa-sdk), lo que permite ejecutar lógica compleja (consultar bases de datos, calcular horarios) en respuesta a la intención del usuario, algo fundamental para un sistema de reservas dinámico.
- **Flexibilidad NLU:** Permite un entrenamiento fino de las entidades y intents específicos del dominio en español.

### 🔌 Backend y API: Flask (Python)

Flask actúa como el orquestador del sistema. Se eligió por:

- **Ligereza y Modularidad:** A diferencia de Django, Flask permite construir una API RESTful mínima y escalar según necesidad utilizando Blueprints.
- **Ecosistema Python:** Facilita la integración directa con las librerías de análisis de datos y lógica de fechas (datetime, pandas si fuera necesario).
- **Manejo de Rutas:** Gestión eficiente de endpoints para servir tanto la API JSON como los archivos estáticos del Frontend.

### 💾 Base de Datos: SQLite

Para esta fase del proyecto, se utiliza SQLite:

- **Despliegue sin Servidor:** Al ser una base de datos basada en archivos, elimina la necesidad de configurar servidores dedicados (como PostgreSQL o MySQL), simplificando enormemente el desarrollo y las pruebas (CI/CD).
- **Portabilidad:** La base de datos completa reside en un solo archivo (`tfg_data.db`), facilitando backups y reset de datos.
- **Suficiencia:** SQLite es capaz de manejar el tráfico esperado para un prototipo funcional y pequeñas implantaciones reales.

### 🎨 Frontend: HTML5 + JavaScript (Vanilla) + Tailwind CSS

- **Sin Frameworks Pesados:** Se evitó el uso de React/Vue para mantener la ligereza y reducir la complejidad de compilación.
- **Web Speech API:** Uso de estándares nativos del navegador para el reconocimiento de voz (STT) y síntesis de voz (TTS), evitando costes de APIs externas.

## 3. Desafíos Técnicos y Soluciones

Durante el ciclo de desarrollo, se identificaron y superaron varios obstáculos críticos:

### A. Sincronización Rasa-Flask en Tiempo Real

- **El Problema:** Rasa es asíncrono y "ciego" ante el estado real del negocio. No sabe si una hora está libre solo con el entrenamiento NLU.
- **La Solución:** Implementación de un servidor de acciones (`actions.py`) que actúa como puente. Cuando el usuario pide una hora, Rasa pausa la conversación, consulta el endpoint `/disponibilidad` de Flask, y devuelve una respuesta basada en datos reales, no solo en predicciones lingüísticas.

### B. Entrenamiento con Escasez de Datos (Cold Start)

- **El Problema:** Los modelos de lenguaje requieren miles de ejemplos para generalizar, pero partíamos de cero.
- **La Solución:**
	- Uso de Lookup Tables en Rasa para inyectar listas masivas de nombres de negocios y servicios sin tener que escribir miles de frases.
	- Implementación de Interactive Learning (Rasa Shell) para corregir al bot en tiempo real y reentrenar con esas correcciones.

### C. Gestión de Dependencias (Dependency Hell)

- **El Problema:** Rasa requiere versiones específicas de librerías (como SQLAlchemy < 2.0 o versiones concretas de sanic) que entraban en conflicto con las versiones modernas de Flask.
- **La Solución:**
	- Aislamiento estricto mediante entornos virtuales (`venv`).
	- Definición de un archivo `requirements.txt` con versiones "pineadas" (fijas) para garantizar la reproducibilidad del entorno en cualquier máquina.

## 4. Trabajo Futuro y Mejoras

Aun el sistema es funcional (v0.1), se plantean las siguientes líneas de evolución:

- **Migración a PostgreSQL:** Para entornos de producción con concurrencia de usuarios real.
- **Panel de Administración:** Interfaz gráfica para que los propietarios gestionen sus horarios sin tocar código.
- **Notificaciones:** Integración con WhatsApp Business API o Email para confirmar citas.
