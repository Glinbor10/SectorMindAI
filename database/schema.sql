-- TABLA DE USUARIOS
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL DEFAULT 'cliente', -- 'cliente' o 'propietario'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- TABLA DE NEGOCIOS (Actualizada)
CREATE TABLE negocios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo_negocio TEXT NOT NULL,
    -- Nuevos campos de personalización
    direccion TEXT,
    descripcion TEXT,
    foto_url TEXT, -- URL de la imagen principal
    -- Vínculo con el dueño
    propietario_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (propietario_id) REFERENCES usuarios(id)
);

-- TABLA DE SERVICIOS
CREATE TABLE servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    precio DECIMAL(10, 2),
    duracion_minutos INTEGER NOT NULL,
    FOREIGN KEY (negocio_id) REFERENCES negocios(id)
);

-- TABLA DE HORARIOS
CREATE TABLE horarios_negocio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id INTEGER NOT NULL,
    dia_semana INTEGER NOT NULL,
    hora_apertura TIME,
    hora_cierre TIME,
    FOREIGN KEY (negocio_id) REFERENCES negocios(id)
);

-- TABLA DE CITAS
CREATE TABLE citas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id INTEGER NOT NULL,
    servicio_id INTEGER NOT NULL,
    fecha_hora_cita DATETIME NOT NULL,
    estado TEXT DEFAULT 'confirmado',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (negocio_id) REFERENCES negocios(id),
    FOREIGN KEY (servicio_id) REFERENCES servicios(id)
);