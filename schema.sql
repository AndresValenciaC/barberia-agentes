CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    celular VARCHAR(20),
    correo VARCHAR(150),
    canal_preferido VARCHAR(30),
    creado_en TIMESTAMP DEFAULT NOW()
);

CREATE TABLE servicios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    duracion_minutos INT NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE citas (
    id SERIAL PRIMARY KEY,
    cliente_id INT REFERENCES clientes(id),
    servicio_id INT REFERENCES servicios(id),
    fecha_hora TIMESTAMP NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente' 
        CHECK (estado IN ('pendiente','confirmada','cancelada')),
    google_event_id VARCHAR(255),
    canal_origen VARCHAR(30),
    creado_en TIMESTAMP DEFAULT NOW()
);

CREATE TABLE interacciones_agente (
    id SERIAL PRIMARY KEY,
    cliente_id INT REFERENCES clientes(id),
    canal VARCHAR(30),
    mensaje_entrada TEXT NOT NULL,
    respuesta_json JSONB,
    estado VARCHAR(30),
    creado_en TIMESTAMP DEFAULT NOW()
);