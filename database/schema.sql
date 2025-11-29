-- Esquema de la Base de Datos SQLite para Sector Mind AI

-- 1. LIMPIEZA: Eliminar tablas existentes para empezar de cero
DROP TABLE IF EXISTS citas;
DROP TABLE IF EXISTS servicios;
DROP TABLE IF EXISTS horarios_negocio;
DROP TABLE IF EXISTS negocios;
DROP TABLE IF EXISTS usuarios;

-- 2. TABLA USUARIOS
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL, -- 'cliente' o 'propietario'
    foto_perfil_url TEXT -- URL de la foto de perfil
);

-- 3. TABLA NEGOCIOS
CREATE TABLE negocios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo_negocio TEXT NOT NULL,
    direccion TEXT,
    descripcion TEXT,
    foto_url TEXT,
    propietario_id INTEGER NOT NULL,
    FOREIGN KEY (propietario_id) REFERENCES usuarios (id)
);

-- 4. TABLA SERVICIOS
CREATE TABLE servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    precio REAL NOT NULL,
    duracion_minutos INTEGER NOT NULL,
    FOREIGN KEY (negocio_id) REFERENCES negocios (id)
);

-- 5. TABLA HORARIOS_NEGOCIO (¡Esta faltaba!)
CREATE TABLE horarios_negocio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id INTEGER NOT NULL,
    dia_semana INTEGER NOT NULL, -- 0=Lunes, 6=Domingo
    hora_apertura TEXT NOT NULL, -- 'HH:MM:SS'
    hora_cierre TEXT NOT NULL,   -- 'HH:MM:SS'
    FOREIGN KEY (negocio_id) REFERENCES negocios (id)
);

-- 6. TABLA CITAS
CREATE TABLE citas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    negocio_id INTEGER NOT NULL,
    servicio_id INTEGER NOT NULL,
    fecha_hora_cita TEXT NOT NULL, -- 'YYYY-MM-DD HH:MM:SS'
    duracion_minutos INTEGER NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    FOREIGN KEY (cliente_id) REFERENCES usuarios (id),
    FOREIGN KEY (negocio_id) REFERENCES negocios (id),
    FOREIGN KEY (servicio_id) REFERENCES servicios (id)
);