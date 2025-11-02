-- Tabla para los negocios registrados
CREATE TABLE negocios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo_negocio TEXT NOT NULL, -- "peluqueria", "dentista", etc.
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para los servicios que ofrece cada negocio
CREATE TABLE servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    precio DECIMAL(10, 2),
    duracion_minutos INTEGER NOT NULL, -- Ej: 30 (para 30 minutos)
    FOREIGN KEY (negocio_id) REFERENCES negocios(id)
);

-- Tabla para los horarios de apertura de cada negocio
CREATE TABLE horarios_negocio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id INTEGER NOT NULL,
    dia_semana INTEGER NOT NULL, -- 0=Lunes, 1=Martes, ..., 6=Domingo
    hora_apertura TIME,
    hora_cierre TIME,
    FOREIGN KEY (negocio_id) REFERENCES negocios(id)
);

-- Tabla para las citas confirmadas
CREATE TABLE citas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id INTEGER NOT NULL,
    servicio_id INTEGER NOT NULL,
    fecha_hora_cita DATETIME NOT NULL, -- Hora de inicio de la cita
    estado TEXT DEFAULT 'confirmado', -- "confirmado", "cancelado"
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (negocio_id) REFERENCES negocios(id),
    FOREIGN KEY (servicio_id) REFERENCES servicios(id)
);
