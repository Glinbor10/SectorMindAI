# Scripts de Sector Mind AI

Esta carpeta contiene los scripts PowerShell para gestionar el proyecto Sector Mind AI.

## 📋 Scripts Disponibles

### 🚀 start_docker.ps1
Inicia todos los servicios Docker (backend, base de datos, Rasa, etc.).

```bash
.\scripts\start_docker.ps1
```

### 🛑 stop_docker.ps1
Detiene y elimina todos los contenedores Docker.

```bash
.\scripts\stop_docker.ps1
```

### 🧪 run_tests.ps1
Ejecuta los tests automatizados del proyecto.

**Opciones:**
- **Por defecto**: Tests unitarios (backend + Rasa)
  ```bash
  .\scripts\run_tests.ps1
  ```

- **Tests de integración** (requiere internet):
  ```bash
  .\scripts\run_tests.ps1 -Integration
  ```

- **Solo backend**:
  ```bash
  .\scripts\run_tests.ps1 -BackendOnly
  ```

- **Solo Rasa**:
  ```bash
  .\scripts\run_tests.ps1 -RasaOnly
  ```

- **Con reporte de cobertura**:
  ```bash
  .\scripts\run_tests.ps1 -Coverage
  ```

- **Archivo específico**:
  ```bash
  .\scripts\run_tests.ps1 -TestFile "backend/tests/test_auth.py"
  ```

### 🤖 train_rasa.ps1
Entrena los modelos de IA de Rasa (Discovery y Model).

```bash
.\scripts\train_rasa.ps1
```

### 🗄️ manage_db.ps1
Gestiona la base de datos PostgreSQL (inicialización, reseteo, etc.).

```bash
.\scripts\manage_db.ps1
```

## 📝 Notas
- Todos los scripts requieren que Docker esté instalado y corriendo
- Los tests requieren que los contenedores estén activos
- Ejecuta desde la raíz del proyecto usando rutas relativas (`.\scripts\nombre.ps1`)
- En VS Code, puedes usar los botones de tareas para ejecutar algunos scripts automáticamente