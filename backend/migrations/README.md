# Backend Migrations

Sistema de migraciones de base de datos para SectorMindAI (v0.7.5).

## Estructura

- `migrate.py` - Script principal de migraciones (mejorado en v0.7.1)
- `001_initial_schema.sql` - Migración inicial del schema
- `002_migrar_base64_negocios.sql` - Migración de fotos base64
- `003_add_geolocalizacion.sql` - Migración de geolocalización (v0.6.0)
- `migrate_sqlite_to_postgres.py` - Script de migración de datos (v0.4.0)

## Uso

### Aplicar migraciones

```bash
# Desde el contenedor Docker (recomendado)
docker compose exec backend python -m backend.migrations.migrate

# Localmente (desarrollo)
python -m backend.migrations.migrate
```

### Migrar datos de SQLite a PostgreSQL

```bash
# Asegúrate de que PostgreSQL está corriendo
docker compose up -d db

# Ejecuta el script de migración
python backend/migrations/migrate_sqlite_to_postgres.py
```

## Crear nueva migración

1. Crea un archivo SQL con formato: `XXX_descripcion.sql`
2. Usa sintaxis PostgreSQL (principalmente soportado desde v0.4.0)
3. Ejecuta `migrate.py` para aplicarla

## Historial de Migraciones

- **v0.4.0**: Migración completa SQLite → PostgreSQL
- **v0.6.0**: Agregadas columnas `latitud` y `longitud` con índices
- **v0.7.1**: Limpieza de migraciones y mejor manejo de statements SQL

## Notas

- Las migraciones se aplican en orden alfabético
- Se registran en la tabla `schema_migrations`
- PostgreSQL es la base de datos principal desde v0.4.0
- Todas las migraciones probadas con 100% tests passing
