"""
Tests para backend/logic.py
Valida la lógica de disponibilidad y solapamiento de citas.
"""
import pytest
from datetime import datetime, timedelta
from backend.logic import verificar_solapamiento, obtener_tramos_disponibles, PASO_BUSQUEDA


# NOTE: db_conn fixture es proporcionada por conftest.py (usa PostgreSQL de Docker)
# NOTE: logic_test_data fixture prepara negocio, servicios y horarios para estos tests
# NOTE: Retorna: {'negocio_id': int, 'servicio_id_1': int, 'servicio_id_2': int, 'owner_id': int}


# ======================================================================
# TESTS PARA verificar_solapamiento()
# ======================================================================

def test_verificar_solapamiento_servicio_invalido(logic_test_data, db_conn):
    """Test con servicio_id inexistente."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=999,  # No existe
        fecha_hora_cita_str='2025-12-08 10:00:00',
        conn=db_conn
    )
    assert valido == False
    assert "Servicio no válido" in mensaje or "no encontrado" in mensaje.lower()


def test_verificar_solapamiento_formato_fecha_invalido(logic_test_data, db_conn):
    """Test con formato de fecha incorrecto."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_hora_cita_str='08-12-2025 10:00',  # Formato erróneo
        conn=db_conn
    )
    assert valido == False
    assert "Formato de fecha" in mensaje or "formato" in mensaje.lower()


def test_verificar_solapamiento_negocio_cerrado(logic_test_data, db_conn):
    """Test en día que el negocio está cerrado (domingo = 6)."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_hora_cita_str='2025-12-07 10:00:00',  # Domingo
        conn=db_conn
    )
    assert valido == False
    assert "cerrado" in mensaje.lower()


def test_verificar_solapamiento_fuera_horario_apertura(logic_test_data, db_conn):
    """Test fuera del horario de apertura (antes de las 9:00)."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_hora_cita_str='2025-12-08 08:00:00',  # Lunes a las 8:00
        conn=db_conn
    )
    assert valido == False
    assert "fuera del horario" in mensaje.lower() or "horario" in mensaje.lower()


def test_verificar_solapamiento_fuera_horario_cierre(logic_test_data, db_conn):
    """Test que termina después del horario de cierre."""
    # Corte dura 30 min, si empieza a las 12:45 termina a las 13:15 (fuera)
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_hora_cita_str='2025-12-08 12:45:00',  # Lunes
        conn=db_conn
    )
    assert valido == False
    assert "fuera del horario" in mensaje.lower() or "horario" in mensaje.lower()


def test_verificar_solapamiento_en_pausa_comida(logic_test_data, db_conn):
    """Test en pausa de comida (13:00-16:00 sin horario)."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_hora_cita_str='2025-12-08 14:00:00',  # Lunes 14:00
        conn=db_conn
    )
    assert valido == False
    assert "fuera del horario" in mensaje.lower() or "horario" in mensaje.lower()


def test_verificar_solapamiento_valido_sin_citas(logic_test_data, db_conn):
    """Test con horario válido y sin citas existentes."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_hora_cita_str='2025-12-08 10:00:00',  # Lunes 10:00
        conn=db_conn
    )
    assert valido == True
    assert "válida" in mensaje.lower() or "disponible" in mensaje.lower()


def test_verificar_solapamiento_con_cita_existente_colision(logic_test_data, db_conn):
    """Test con colisión: cita existente 10:00-10:30, nueva 10:15-10:45."""
    # Crear cita existente
    db_conn.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (%s, %s, %s, %s, %s, %s)",
        (logic_test_data['negocio_id'], logic_test_data['cliente_id'], logic_test_data['servicio_id_1'], '2025-12-08 10:00:00', 30, 'confirmada')
    )
    db_conn.commit()
    
    # Intentar nueva cita que se solapa
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_hora_cita_str='2025-12-08 10:15:00',  # Se solapa
        conn=db_conn
    )
    assert valido == False
    assert "solapa" in mensaje.lower()


def test_verificar_solapamiento_sin_colision_consecutiva(logic_test_data, db_conn):
    """Test sin colisión: cita existente 10:00-10:30, nueva 10:30-11:00."""
    db_conn.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (%s, %s, %s, %s, %s, %s)",
        (logic_test_data['negocio_id'], logic_test_data['cliente_id'], logic_test_data['servicio_id_1'], '2025-12-08 10:00:00', 30, 'confirmada')
    )
    db_conn.commit()
    
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_hora_cita_str='2025-12-08 10:30:00',  # Justo después
        conn=db_conn
    )
    assert valido == True
    assert "válida" in mensaje.lower() or "disponible" in mensaje.lower()


def test_verificar_solapamiento_servicio_largo_valido(logic_test_data, db_conn):
    """Test con servicio largo (Tinte 90min) en horario válido."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_2'],  # Tinte 90min
        fecha_hora_cita_str='2025-12-08 10:00:00',  # 10:00-11:30
        conn=db_conn
    )
    assert valido == True


def test_verificar_solapamiento_servicio_largo_sale_horario(logic_test_data, db_conn):
    """Test con servicio largo que sale del horario (Tinte empieza 11:45)."""
    valido, mensaje = verificar_solapamiento(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_2'],  # Tinte 90min
        fecha_hora_cita_str='2025-12-08 11:45:00',  # Terminaría 13:15 (fuera)
        conn=db_conn
    )
    assert valido == False



# ======================================================================
# TESTS PARA obtener_tramos_disponibles()
# ======================================================================

def test_obtener_tramos_servicio_inexistente(logic_test_data, db_conn):
    """Test con servicio_id inexistente."""
    resultado = obtener_tramos_disponibles(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=999,
        fecha_solicitada='2025-12-08',
        conn=db_conn
    )
    assert 'error' in resultado or len(resultado.get('disponibles', [])) == 0


def test_obtener_tramos_formato_fecha_invalido(logic_test_data, db_conn):
    """Test con formato de fecha incorrecto."""
    resultado = obtener_tramos_disponibles(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_solicitada='08/12/2025',  # Formato erróneo
        conn=db_conn
    )
    assert 'error' in resultado or len(resultado.get('disponibles', [])) == 0


def test_obtener_tramos_negocio_cerrado(logic_test_data, db_conn):
    """Test en día cerrado (domingo)."""
    resultado = obtener_tramos_disponibles(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_solicitada='2025-12-07',  # Domingo
        conn=db_conn
    )
    # Debe estar vacío o indicar cierre
    assert len(resultado.get('disponibles', [])) == 0


def test_obtener_tramos_sin_citas_lunes(logic_test_data, db_conn):
    """Test con día libre (Lunes sin citas): 9:00-13:00 y 16:00-20:00."""
    resultado = obtener_tramos_disponibles(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],  # Corte 30min
        fecha_solicitada='2025-12-08',  # Lunes
        conn=db_conn
    )
    
    tramos = resultado.get('disponibles', [])
    
    # Turno mañana: 9:00-13:00 (240 min) → puede empezar hasta 12:30
    # Con paso 15min: 9:00, 9:15, 9:30... 12:30 = 15 slots
    # Turno tarde: 16:00-20:00 (240 min) → puede empezar hasta 19:30
    # Con paso 15min: 16:00, 16:15... 19:30 = 15 slots
    # Total esperado: 30 slots
    
    assert len(tramos) > 20  # Al menos 20 slots
    assert any('09:00' in t for t in tramos)
    assert any('16:00' in t for t in tramos)


def test_obtener_tramos_con_cita_existente(logic_test_data, db_conn):
    """Test con cita existente que bloquea un tramo."""
    # Crear cita 10:00-10:30
    db_conn.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (%s, %s, %s, %s, %s, %s)",
        (logic_test_data['negocio_id'], logic_test_data['cliente_id'], logic_test_data['servicio_id_1'], '2025-12-08 10:00:00', 30, 'confirmada')
    )
    db_conn.commit()
    
    resultado = obtener_tramos_disponibles(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_solicitada='2025-12-08',
        conn=db_conn
    )
    
    tramos = resultado.get('disponibles', [])
    
    # 10:00 NO debe estar (cita existente)
    assert not any('10:00:00' in t for t in tramos)
    
    # 10:30 SÍ debe estar (justo después)
    assert any('10:30:00' in t for t in tramos)
    
    # 9:00 debe estar disponible
    assert any('09:00:00' in t for t in tramos)


def test_obtener_tramos_servicio_largo_reduce_opciones(logic_test_data, db_conn):
    """Test con servicio largo (Tinte 90min) que reduce slots disponibles."""
    resultado = obtener_tramos_disponibles(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_2'],  # Tinte 90min
        fecha_solicitada='2025-12-08',  # Lunes
        conn=db_conn
    )
    
    tramos = resultado.get('disponibles', [])
    
    # Turno mañana: 9:00-13:00 (240 min), servicio 90min
    # Puede empezar hasta 11:30 (termina 13:00)
    # Turno tarde: 16:00-20:00, puede hasta 18:30
    
    assert len(tramos) >= 15  # Al menos algunos slots
    assert any('09:00' in t for t in tramos)  # Debe haber inicio
    assert any('16:00' in t for t in tramos)  # Tarde


def test_obtener_tramos_martes_un_turno(logic_test_data, db_conn):
    """Test con día de dos turnos (Martes 9:00-13:00 y 16:00-20:00)."""
    resultado = obtener_tramos_disponibles(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],  # Corte 30min
        fecha_solicitada='2025-12-09',  # Martes
        conn=db_conn
    )

    tramos = resultado.get('disponibles', [])

    # Martes tiene dos turnos: 9:00-13:00 (240 min) y 16:00-20:00 (240 min)
    # Servicio 30min → puede hacer slots hasta 12:30 y 19:30
    # Con paso 15min: múltiples slots en ambos turnos

    assert len(tramos) >= 15
    assert any('09:00' in t for t in tramos)

    # Debe haber slots en ambos turnos (antes de 13:00 y después de 16:00)
    has_morning = any(int(t.split()[-1].split(':')[0]) < 13 for t in tramos if ':' in t)
    has_afternoon = any(int(t.split()[-1].split(':')[0]) >= 16 for t in tramos if ':' in t)
    assert has_morning and has_afternoon

def test_obtener_tramos_paso_busqueda_correcto(logic_test_data, db_conn):
    """Test que valida el paso de búsqueda (15 minutos)."""
    resultado = obtener_tramos_disponibles(
        negocio_id=logic_test_data['negocio_id'],
        servicio_id=logic_test_data['servicio_id_1'],
        fecha_solicitada='2025-12-08',
        conn=db_conn
    )
    
    tramos = resultado.get('disponibles', [])
    
    # Verificar que los minutos son múltiplos de PASO_BUSQUEDA (15)
    for tramo_str in tramos[:10]:  # Revisar primeros 10
        if ':' in tramo_str:
            minutos = int(tramo_str.split(':')[1])
            assert minutos % PASO_BUSQUEDA == 0


def test_obtener_tramos_multiples_citas_dia(logic_test_data, db_conn):
    """Test con múltiples citas en el mismo día."""
    # Crear 3 citas: 10:00, 11:00, 17:00
    negocio_id = logic_test_data['negocio_id']
    servicio_id = logic_test_data['servicio_id_1']
    cliente_id = logic_test_data['cliente_id']
    
    db_conn.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (%s, %s, %s, %s, %s, %s)",
        (negocio_id, cliente_id, servicio_id, '2025-12-08 10:00:00', 30, 'confirmada')
    )
    db_conn.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (%s, %s, %s, %s, %s, %s)",
        (negocio_id, cliente_id, servicio_id, '2025-12-08 11:00:00', 30, 'confirmada')
    )
    db_conn.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (%s, %s, %s, %s, %s, %s)",
        (negocio_id, cliente_id, servicio_id, '2025-12-08 17:00:00', 30, 'confirmada')
    )
    db_conn.commit()
    
    resultado = obtener_tramos_disponibles(
        negocio_id=negocio_id,
        servicio_id=servicio_id,
        fecha_solicitada='2025-12-08',
        conn=db_conn
    )
    
    tramos = resultado.get('disponibles', [])
    
    # Verificar que todas las citas están bloqueadas
    assert not any('10:00:00' in t for t in tramos)
    assert not any('11:00:00' in t for t in tramos)
    assert not any('17:00:00' in t for t in tramos)
    
    # Pero hay slots disponibles antes, entre y después
    assert any('09:00' in t for t in tramos)  # Antes de 10:00
    assert any('10:30' in t for t in tramos)  # Entre 10:00 y 11:00
    assert any('11:30' in t for t in tramos)  # Después de 11:00
    assert any('17:30' in t for t in tramos)  # Después de 17:00

