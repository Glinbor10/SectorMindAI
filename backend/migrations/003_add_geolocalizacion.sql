-- Migración: Agregar campos de geolocalización a la tabla negocios
-- Fecha: 2026-01-06
-- Descripción: Añade columnas latitud y longitud para búsqueda por proximidad

-- 1. Agregar columnas de coordenadas
ALTER TABLE negocios 
ADD COLUMN IF NOT EXISTS latitud DECIMAL(10, 8),
ADD COLUMN IF NOT EXISTS longitud DECIMAL(11, 8);

-- 2. Crear índice para búsquedas geográficas eficientes
CREATE INDEX IF NOT EXISTS idx_negocios_ubicacion ON negocios(latitud, longitud);

-- 3. Agregar comentarios para documentación
COMMENT ON COLUMN negocios.latitud IS 'Latitud en formato decimal (-90 a +90). Ej: 40.4168 para Madrid';
COMMENT ON COLUMN negocios.longitud IS 'Longitud en formato decimal (-180 a +180). Ej: -3.7038 para Madrid';

-- 4. (Opcional) Script de geocodificación manual para negocios existentes
-- Descomenta y ajusta según tus datos:

-- UPDATE negocios SET latitud = 40.4168, longitud = -3.7038 
-- WHERE direccion ILIKE '%madrid%' AND latitud IS NULL;

-- UPDATE negocios SET latitud = 41.3874, longitud = 2.1686 
-- WHERE direccion ILIKE '%barcelona%' AND latitud IS NULL;

-- UPDATE negocios SET latitud = 39.4699, longitud = -0.3763 
-- WHERE direccion ILIKE '%valencia%' AND latitud IS NULL;
