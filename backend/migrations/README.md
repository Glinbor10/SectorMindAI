# Backend Migrations - SectorMindAI v1.0.0

Sistema de migraciones SQL para backend PostgreSQL.

## Estructura

- `migrate.py`: ejecutor principal
- `001_initial_schema.sql`
- `002_migrar_base64_negocios.sql`
- `003_add_geolocalizacion.sql`

## Uso

Aplicar migraciones en Docker:
```bash
docker compose exec backend python -m backend.migrations.migrate
```

## Reglas

- Las migraciones se aplican en orden alfanumerico.
- Solo PostgreSQL es entorno objetivo.

## Estado

Version documental: 1.0.0
Cambios futuros en migraciones solo por correccion o necesidades tecnicas reales.
