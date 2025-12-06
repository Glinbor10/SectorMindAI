"""
Tests para backend/logic.py
Valida la lógica de disponibilidad y solapamiento de citas.
"""
import pytest
import sqlite3
from datetime import datetime, timedelta
from backend.logic import verificar_solapamiento, obtener_tramos_disponibles, PASO_BUSQUEDA


@pytest.fixture
def db_conn():
    """Crea una base de datos temporal en memoria para cada test."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Crear schema mínimo
    conn.executescript('''
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL
        );
        
        CREATE TABLE negocios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo_negocio TEXT NOT NULL,
            direccion TEXT,
            propietario_id INTEGER NOT NULL,
            FOREIGN KEY (propietario_id) REFERENCES usuarios (id)
        );
        
        CREATE TABLE servicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            negocio_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            duracion_minutos INTEGER NOT NULL,
            FOREIGN KEY (negocio_id) REFERENCES negocios (id)
        );
        
        CREATE TABLE horarios_negocio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            negocio_id INTEGER NOT NULL,
            dia_semana INTEGER NOT NULL,
            hora_apertura TEXT NOT NULL,
            hora_cierre TEXT NOT NULL,
            FOREIGN KEY (negocio_id) REFERENCES negocios (id)
        );
        
        CREATE TABLE citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            negocio_id INTEGER NOT NULL,
            cliente_id INTEGER NOT NULL,
            servicio_id INTEGER NOT NULL,
            fecha_hora_cita TEXT NOT NULL,
            estado TEXT NOT NULL,
            FOREIGN KEY (negocio_id) REFERENCES negocios (id),
            FOREIGN KEY (cliente_id) REFERENCES usuarios (id),
            FOREIGN KEY (servicio_id) REFERENCES servicios (id)
        );
    ''')
    
    # Datos de prueba
    conn.execute("INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES ('Propietario Test', 'prop@test.com', 'hash', 'propietario')")
    conn.execute("INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES ('Cliente Test', 'cliente@test.com', 'hash', 'cliente')")
    conn.execute("INSERT INTO negocios (nombre, tipo_negocio, direccion, propietario_id) VALUES ('Peluquería Test', 'peluqueria', 'Calle Test 123', 1)")
    conn.execute("INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (1, 'Corte', 15.0, 30)")
    conn.execute("INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (1, 'Tinte', 45.0, 90)")
    
    # Horarios: Lunes (0) de 9:00-13:00 y 16:00-20:00
    conn.execute("INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (1, 0, '09:00:00', '13:00:00')")
    conn.execute("INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (1, 0, '16:00:00', '20:00:00')")
    
    # Martes (1) de 9:00-14:00 (un solo turno)
    conn.execute("INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (1, 1, '09:00:00', '14:00:00')")
    
    conn.commit()
    
    yield conn
    
    conn.close()


# ======================================================================
# TESTS PARA verificar_solapamiento()
# ======================================================================

def test_verificar_solapamiento_servicio_invalido(db_conn):
    """Test con servicio_id inexistente."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=999,  # No existe
        fecha_hora_cita_str='2025-12-08 10:00:00',
        conn=db_conn
    )
    assert valido == False
    assert "Servicio no válido" in mensaje


def test_verificar_solapamiento_formato_fecha_invalido(db_conn):
    """Test con formato de fecha incorrecto."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=1,
        fecha_hora_cita_str='08-12-2025 10:00',  # Formato erróneo
        conn=db_conn
    )
    assert valido == False
    assert "Formato de fecha" in mensaje


def test_verificar_solapamiento_negocio_cerrado(db_conn):
    """Test en día que el negocio está cerrado (domingo = 6)."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=1,
        fecha_hora_cita_str='2025-12-07 10:00:00',  # Domingo
        conn=db_conn
    )
    assert valido == False
    assert "cerrado" in mensaje.lower()


def test_verificar_solapamiento_fuera_horario_apertura(db_conn):
    """Test fuera del horario de apertura (antes de las 9:00)."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=1,
        fecha_hora_cita_str='2025-12-08 08:00:00',  # Lunes a las 8:00
        conn=db_conn
    )
    assert valido == False
    assert "fuera del horario" in mensaje.lower()


def test_verificar_solapamiento_fuera_horario_cierre(db_conn):
    """Test que termina después del horario de cierre."""
    # Corte dura 30 min, si empieza a las 12:45 termina a las 13:15 (fuera)
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=1,
        fecha_hora_cita_str='2025-12-08 12:45:00',  # Lunes
        conn=db_conn
    )
    assert valido == False
    assert "fuera del horario" in mensaje.lower()


def test_verificar_solapamiento_en_pausa_comida(db_conn):
    """Test en pausa de comida (13:00-16:00 sin horario)."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=1,
        fecha_hora_cita_str='2025-12-08 14:00:00',  # Lunes 14:00
        conn=db_conn
    )
    assert valido == False
    assert "fuera del horario" in mensaje.lower()


def test_verificar_solapamiento_valido_sin_citas(db_conn):
    """Test con horario válido y sin citas existentes."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=1,
        fecha_hora_cita_str='2025-12-08 10:00:00',  # Lunes 10:00
        conn=db_conn
    )
    assert valido == True
    assert "válida" in mensaje.lower()


def test_verificar_solapamiento_con_cita_existente_colision(db_conn):
    """Test con colisión: cita existente 10:00-10:30, nueva 10:15-10:45."""
    # Crear cita existente
    db_conn.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 'confirmado')"
    )
    db_conn.commit()
    
    # Intentar nueva cita que se solapa
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=1,
        fecha_hora_cita_str='2025-12-08 10:15:00',  # Se solapa
        conn=db_conn
    )
    assert valido == False
    assert "solapa" in mensaje.lower()


def test_verificar_solapamiento_sin_colision_consecutiva(db_conn):
    """Test sin colisión: cita existente 10:00-10:30, nueva 10:30-11:00."""
    db_conn.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 'confirmado')"
    )
    db_conn.commit()
    
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=1,
        fecha_hora_cita_str='2025-12-08 10:30:00',  # Justo después
        conn=db_conn
    )
    assert valido == True
    assert "válida" in mensaje.lower()


def test_verificar_solapamiento_servicio_largo_valido(db_conn):
    """Test con servicio largo (Tinte 90min) en horario válido."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=2,  # Tinte 90min
        fecha_hora_cita_str='2025-12-08 10:00:00',  # 10:00-11:30
        conn=db_conn
    )
    assert valido == True


def test_verificar_solapamiento_servicio_largo_sale_horario(db_conn):
    """Test con servicio largo que sale del horario (Tinte empieza 11:45)."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=1,
        servicio_id=2,  # Tinte 90min
        fecha_hora_cita_str='2025-12-08 11:45:00',  # Terminaría 13:15 (fuera)
        conn=db_conn
    )
    assert valido == False


# ======================================================================
# TESTS PARA obtener_tramos_disponibles()
# ======================================================================

def test_obtener_tramos_servicio_inexistente(db_conn):
    """Test con servicio_id inexistente."""
    resultado = obtener_tramos_disponibles(
        negocio_id=1,
        servicio_id=999,
        fecha_solicitada='2025-12-08',
        conn=db_conn
    )
    assert 'error' in resultado
    assert 'no encontrado' in resultado['error'].lower()


def test_obtener_tramos_formato_fecha_invalido(db_conn):
    """Test con formato de fecha incorrecto."""
    resultado = obtener_tramos_disponibles(
        negocio_id=1,
        servicio_id=1,
        fecha_solicitada='08/12/2025',  # Formato erróneo
        conn=db_conn
    )
    assert 'error' in resultado
    assert 'formato' in resultado['error'].lower()


def test_obtener_tramos_negocio_cerrado(db_conn):
    """Test en día cerrado (domingo)."""
    resultado = obtener_tramos_disponibles(
        negocio_id=1,
        servicio_id=1,
        fecha_solicitada='2025-12-07',  # Domingo
        conn=db_conn
    )
    assert 'disponibles' in resultado
    assert len(resultado['disponibles']) == 0
    assert 'cerrado' in resultado['mensaje'].lower()


def test_obtener_tramos_sin_citas_lunes(db_conn):
    """Test con día libre (Lunes sin citas): 9:00-13:00 y 16:00-20:00."""
    resultado = obtener_tramos_disponibles(
        negocio_id=1,
        servicio_id=1,  # Corte 30min
        fecha_solicitada='2025-12-08',  # Lunes
        conn=db_conn
    )
    
    assert 'disponibles' in resultado
    tramos = resultado['disponibles']
    
    # Turno mañana: 9:00-13:00 (240 min) → puede empezar hasta 12:30
    # Con paso 15min: 9:00, 9:15, 9:30... 12:30 = 15 slots
    # Turno tarde: 16:00-20:00 (240 min) → puede empezar hasta 19:30
    # Con paso 15min: 16:00, 16:15... 19:30 = 15 slots
    # Total esperado: 30 slots
    
    assert len(tramos) > 20  # Al menos 20 slots
    assert '2025-12-08 09:00:00' in tramos
    assert '2025-12-08 16:00:00' in tramos
    assert '2025-12-08 12:30:00' in tramos  # Último slot mañana
    assert '2025-12-08 19:30:00' in tramos  # Último slot tarde


def test_obtener_tramos_con_cita_existente(db_conn):
    """Test con cita existente que bloquea un tramo."""
    # Crear cita 10:00-10:30
    db_conn.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 'confirmado')"
    )
    db_conn.commit()
    
    resultado = obtener_tramos_disponibles(
        negocio_id=1,
        servicio_id=1,
        fecha_solicitada='2025-12-08',
        conn=db_conn
    )
    
    tramos = resultado['disponibles']
    
    # 10:00 NO debe estar (cita existente)
    assert '2025-12-08 10:00:00' not in tramos
    
    # 10:15 tampoco (se solaparía: 10:15-10:45 con 10:00-10:30)
    assert '2025-12-08 10:15:00' not in tramos
    
    # 10:30 SÍ debe estar (justo después)
    assert '2025-12-08 10:30:00' in tramos
    
    # 9:45 NO debe estar (se solaparía: 9:45-10:15 con 10:00-10:30)
    assert '2025-12-08 09:45:00' not in tramos


def test_obtener_tramos_servicio_largo_reduce_opciones(db_conn):
    """Test con servicio largo (Tinte 90min) que reduce slots disponibles."""
    resultado = obtener_tramos_disponibles(
        negocio_id=1,
        servicio_id=2,  # Tinte 90min
        fecha_solicitada='2025-12-08',  # Lunes
        conn=db_conn
    )
    
    tramos = resultado['disponibles']
    
    # Turno mañana: 9:00-13:00 (240 min), servicio 90min
    # Puede empezar hasta 11:30 (termina 13:00)
    # Con paso 15min: 9:00, 9:15... 11:30 = 11 slots
    # Turno tarde: 16:00-20:00, puede hasta 18:30 = 11 slots
    # Total esperado: 22 slots
    
    assert len(tramos) >= 20
    assert '2025-12-08 11:30:00' in tramos  # Último válido mañana
    assert '2025-12-08 11:45:00' not in tramos  # Terminaría fuera (13:15)
    assert '2025-12-08 18:30:00' in tramos  # Último válido tarde


def test_obtener_tramos_martes_un_turno(db_conn):
    """Test con día de un solo turno (Martes 9:00-14:00)."""
    resultado = obtener_tramos_disponibles(
        negocio_id=1,
        servicio_id=1,  # Corte 30min
        fecha_solicitada='2025-12-09',  # Martes
        conn=db_conn
    )
    
    tramos = resultado['disponibles']
    
    # 9:00-14:00 (300 min), servicio 30min → puede hasta 13:30
    # Con paso 15min: 9:00, 9:15... 13:30 = 19 slots
    
    assert len(tramos) >= 18
    assert '2025-12-09 09:00:00' in tramos
    assert '2025-12-09 13:30:00' in tramos
    assert '2025-12-09 13:45:00' not in tramos  # Fuera de horario
    
    # No debe haber slots de tarde
    for tramo in tramos:
        hora = datetime.strptime(tramo, '%Y-%m-%d %H:%M:%S').hour
        assert hora < 14  # Todos antes de las 14:00


def test_obtener_tramos_paso_busqueda_correcto(db_conn):
    """Test que valida el paso de búsqueda (15 minutos)."""
    resultado = obtener_tramos_disponibles(
        negocio_id=1,
        servicio_id=1,
        fecha_solicitada='2025-12-08',
        conn=db_conn
    )
    
    tramos = resultado['disponibles']
    
    # Verificar que los minutos son múltiplos de PASO_BUSQUEDA (15)
    for tramo_str in tramos[:10]:  # Revisar primeros 10
        dt = datetime.strptime(tramo_str, '%Y-%m-%d %H:%M:%S')
        assert dt.minute % PASO_BUSQUEDA == 0


def test_obtener_tramos_multiples_citas_dia(db_conn):
    """Test con múltiples citas en el mismo día."""
    # Crear 3 citas: 10:00, 11:00, 17:00
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 'confirmado')")
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, estado) VALUES (1, 2, 1, '2025-12-08 11:00:00', 'confirmado')")
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, estado) VALUES (1, 2, 1, '2025-12-08 17:00:00', 'confirmado')")
    db_conn.commit()
    
    resultado = obtener_tramos_disponibles(
        negocio_id=1,
        servicio_id=1,
        fecha_solicitada='2025-12-08',
        conn=db_conn
    )
    
    tramos = resultado['disponibles']
    
    # Verificar que todas las citas están bloqueadas
    assert '2025-12-08 10:00:00' not in tramos
    assert '2025-12-08 11:00:00' not in tramos
    assert '2025-12-08 17:00:00' not in tramos
    
    # Pero hay slots disponibles antes, entre y después
    assert '2025-12-08 09:00:00' in tramos  # Antes de 10:00
    assert '2025-12-08 10:30:00' in tramos  # Entre 10:00 y 11:00
    assert '2025-12-08 11:30:00' in tramos  # Después de 11:00
    assert '2025-12-08 17:30:00' in tramos  # Después de 17:00
