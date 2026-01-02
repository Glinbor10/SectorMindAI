-- Schema PostgreSQL para SectorMindAI
-- Compatible con PostgreSQL 15+

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(50) NOT NULL CHECK (rol IN ('cliente', 'propietario')),
    foto_perfil_url TEXT,
    foto_perfil_base64 TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de negocios
CREATE TABLE IF NOT EXISTS negocios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tipo_negocio VARCHAR(100) NOT NULL,
    direccion TEXT,
    descripcion TEXT,
    foto_base64 TEXT,
    propietario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de servicios
CREATE TABLE IF NOT EXISTS servicios (
    id SERIAL PRIMARY KEY,
    negocio_id INTEGER NOT NULL REFERENCES negocios(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    precio DECIMAL(10, 2) NOT NULL,
    duracion_minutos INTEGER NOT NULL CHECK (duracion_minutos > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de horarios de negocio
CREATE TABLE IF NOT EXISTS horarios_negocio (
    id SERIAL PRIMARY KEY,
    negocio_id INTEGER NOT NULL REFERENCES negocios(id) ON DELETE CASCADE,
    dia_semana INTEGER NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
    hora_apertura TIME NOT NULL,
    hora_cierre TIME NOT NULL,
    CHECK (hora_apertura < hora_cierre)
);

-- Tabla de citas
CREATE TABLE IF NOT EXISTS citas (
    id SERIAL PRIMARY KEY,
    negocio_id INTEGER NOT NULL REFERENCES negocios(id) ON DELETE CASCADE,
    cliente_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    servicio_id INTEGER NOT NULL REFERENCES servicios(id) ON DELETE CASCADE,
    fecha_hora_cita TIMESTAMP NOT NULL,
    duracion_minutos INTEGER NOT NULL,
    estado VARCHAR(50) DEFAULT 'confirmada' CHECK (estado IN ('confirmada', 'cancelada', 'completada')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimización
CREATE INDEX IF NOT EXISTS idx_negocios_propietario ON negocios(propietario_id);
CREATE INDEX IF NOT EXISTS idx_servicios_negocio ON servicios(negocio_id);
CREATE INDEX IF NOT EXISTS idx_horarios_negocio ON horarios_negocio(negocio_id);
CREATE INDEX IF NOT EXISTS idx_citas_cliente ON citas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_citas_negocio ON citas(negocio_id);
CREATE INDEX IF NOT EXISTS idx_citas_fecha ON citas(fecha_hora_cita);
