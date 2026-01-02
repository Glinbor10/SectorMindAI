-- Migración 002: Migrar a imágenes base64 en negocios
-- Agrega columna foto_base64 y elimina foto_url de la tabla negocios

ALTER TABLE negocios ADD COLUMN IF NOT EXISTS foto_base64 TEXT;

-- Elimina la columna foto_url si existe (opcional, solo si ya no se usa)
ALTER TABLE negocios DROP COLUMN IF EXISTS foto_url;
