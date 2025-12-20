# Backend Migrations

Sistema de migraciones de base de datos para SectorMindAI.

## Estructura

- `migrate.py` - Script principal de migraciones
- `001_initial_schema.sql` - Migración inicial del schema
- `migrate_sqlite_to_postgres.py` - Script de migración de datos

## Uso

### Aplicar migraciones

```bash
# Desde el contenedor Docker
docker compose exec backend python -m backend.migrations.migrate

# Localmente
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
2. Usa sintaxis compatible con ambas BD cuando sea posible
3. Ejecuta `migrate.py` para aplicarla

## Notas

- Las migraciones se aplican en orden alfabético
- Se registran en la tabla `schema_migrations`
- Soporta SQLite (desarrollo) y PostgreSQL (producción)
