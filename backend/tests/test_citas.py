"""
Tests para backend/routes/citas.py
Valida los endpoints de creación, consulta, disponibilidad y cancelación de citas.
"""
import pytest
import json
import sqlite3
import tempfile
import os
from backend.app import create_app


@pytest.fixture
def app():
    """Crea aplicación Flask con BD temporal para testing."""
    # Crear archivo temporal para BD
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app()
    app.config['TESTING'] = True
    
    # Modificar DATABASE en backend.db
    import backend.db as db_module
    db_module.DATABASE = db_path
    
    with app.app_context():
        # Inicializar BD con schema
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        
        # Datos de prueba
        conn.execute("INSERT INTO usuarios (id, nombre, email, password_hash, rol) VALUES (1, 'Propietario Test', 'prop@test.com', 'hash123', 'propietario')")
        conn.execute("INSERT INTO usuarios (id, nombre, email, password_hash, rol) VALUES (2, 'Cliente Test', 'cliente@test.com', 'hash456', 'cliente')")
        conn.execute("INSERT INTO negocios (id, nombre, tipo_negocio, direccion, propietario_id) VALUES (1, 'Peluquería Test', 'peluqueria', 'Calle Test 123', 1)")
        conn.execute("INSERT INTO servicios (id, negocio_id, nombre, precio, duracion_minutos) VALUES (1, 1, 'Corte', 15.0, 30)")
        conn.execute("INSERT INTO servicios (id, negocio_id, nombre, precio, duracion_minutos) VALUES (2, 1, 'Tinte', 45.0, 90)")
        conn.execute("INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (1, 0, '09:00:00', '13:00:00')")
        conn.execute("INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (1, 0, '16:00:00', '20:00:00')")
        conn.execute("INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (1, 1, '09:00:00', '14:00:00')")
        conn.commit()
        conn.close()
    
    yield app
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Cliente de prueba que usa la app con BD temporal."""
    return app.test_client()


@pytest.fixture
def db_conn(app):
    """Fixture que da acceso directo a la BD temporal."""
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        yield conn
        # No cerramos aquí, Flask lo hace automáticamente


# ======================================================================
# TESTS PARA GET /citas (Listar citas)
# ======================================================================

def test_get_citas_sin_filtros(client, db_conn):
    """Test GET /citas sin parámetros devuelve todas las citas."""
    # Crear 2 citas
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 30, 'confirmado')")
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (1, 2, 2, '2025-12-09 11:00:00', 90, 'confirmado')")
    db_conn.commit()
    
    response = client.get('/citas')
    assert response.status_code == 200
    
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['servicio_nombre'] in ['Corte', 'Tinte']


def test_get_citas_filtro_cliente_id(client, db_conn):
    """Test GET /citas?cliente_id=2 filtra por cliente."""
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 30, 'confirmado')")
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (1, 1, 1, '2025-12-08 11:00:00', 30, 'confirmado')")
    db_conn.commit()
    
    response = client.get('/citas?cliente_id=2')
    assert response.status_code == 200
    
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['cliente_nombre'] == 'Cliente Test'


def test_get_citas_filtro_negocio_id(client, db_conn):
    """Test GET /citas?negocio_id=1 filtra por negocio."""
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 30, 'confirmado')")
    db_conn.commit()
    
    response = client.get('/citas?negocio_id=1')
    assert response.status_code == 200
    
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['negocio_nombre'] == 'Peluquería Test'


def test_get_citas_sin_citas(client, db_conn):
    """Test GET /citas con BD vacía devuelve array vacío."""
    response = client.get('/citas')
    assert response.status_code == 200
    assert response.get_json() == []


# ======================================================================
# TESTS PARA POST /citas (Crear cita)
# ======================================================================

def test_post_citas_exitoso(client, db_conn):
    """Test POST /citas crea una cita válida correctamente."""
    payload = {
        'negocio_id': 1,
        'servicio_id': 1,
        'cliente_id': 2,
        'fecha_hora_cita': '2025-12-08 10:00:00'  # Lunes a las 10:00
    }
    
    response = client.post('/citas', 
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data
    assert 'exitosamente' in data['message']


def test_post_citas_sin_datos_obligatorios(client, db_conn):
    """Test POST /citas sin datos obligatorios devuelve 400."""
    payload = {
        'negocio_id': 1
        # Faltan servicio_id y fecha_hora_cita
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    assert 'error' in response.get_json()


def test_post_citas_fuera_horario(client, db_conn):
    """Test POST /citas con horario fuera de apertura devuelve 409."""
    payload = {
        'negocio_id': 1,
        'servicio_id': 1,
        'cliente_id': 2,
        'fecha_hora_cita': '2025-12-08 08:00:00'  # Antes de las 9:00
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 409
    data = response.get_json()
    assert 'fuera del horario' in data['error'].lower()


def test_post_citas_solapamiento(client, db_conn):
    """Test POST /citas con solapamiento devuelve 409."""
    # Crear cita existente
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 30, 'confirmado')")
    db_conn.commit()
    
    # Intentar crear cita que se solapa
    payload = {
        'negocio_id': 1,
        'servicio_id': 1,
        'cliente_id': 2,
        'fecha_hora_cita': '2025-12-08 10:15:00'  # Se solapa con 10:00-10:30
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 409
    data = response.get_json()
    assert 'solapa' in data['error'].lower()


def test_post_citas_dia_cerrado(client, db_conn):
    """Test POST /citas en día cerrado (domingo) devuelve 409."""
    payload = {
        'negocio_id': 1,
        'servicio_id': 1,
        'cliente_id': 2,
        'fecha_hora_cita': '2025-12-07 10:00:00'  # Domingo
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 409
    data = response.get_json()
    assert 'cerrado' in data['error'].lower()


def test_post_citas_servicio_largo_valido(client, db_conn):
    """Test POST /citas con servicio largo (Tinte 90min) válido."""
    payload = {
        'negocio_id': 1,
        'servicio_id': 2,  # Tinte 90min
        'cliente_id': 2,
        'fecha_hora_cita': '2025-12-08 10:00:00'  # 10:00-11:30 (dentro de 9:00-13:00)
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 201


def test_post_citas_servicio_largo_sale_horario(client, db_conn):
    """Test POST /citas con servicio largo que sale del horario."""
    payload = {
        'negocio_id': 1,
        'servicio_id': 2,  # Tinte 90min
        'cliente_id': 2,
        'fecha_hora_cita': '2025-12-08 11:45:00'  # Terminaría 13:15 (fuera)
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 409


# ======================================================================
# TESTS PARA POST /disponibilidad (Consultar disponibilidad)
# ======================================================================

def test_post_disponibilidad_exitoso(client, db_conn):
    """Test POST /disponibilidad devuelve tramos disponibles."""
    payload = {
        'negocio_id': 1,
        'servicio_id': 1,
        'fecha': '2025-12-08'  # Lunes
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'disponibles' in data
    assert len(data['disponibles']) > 10  # Debe haber varios tramos
    assert '2025-12-08 09:00:00' in data['disponibles']


def test_post_disponibilidad_sin_datos(client, db_conn):
    """Test POST /disponibilidad sin datos obligatorios devuelve 400."""
    payload = {
        'negocio_id': 1
        # Faltan servicio_id y fecha
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_post_disponibilidad_dia_cerrado(client, db_conn):
    """Test POST /disponibilidad en día cerrado devuelve array vacío."""
    payload = {
        'negocio_id': 1,
        'servicio_id': 1,
        'fecha': '2025-12-07'  # Domingo (cerrado)
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['disponibles'] == []


def test_post_disponibilidad_con_citas_existentes(client, db_conn):
    """Test POST /disponibilidad con citas existentes bloquea tramos."""
    # Crear cita 10:00-10:30
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 30, 'confirmado')")
    db_conn.commit()
    
    payload = {
        'negocio_id': 1,
        'servicio_id': 1,
        'fecha': '2025-12-08'
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = response.get_json()
    
    # 10:00 NO debe estar disponible
    assert '2025-12-08 10:00:00' not in data['disponibles']
    
    # Pero 10:30 SÍ (justo después)
    assert '2025-12-08 10:30:00' in data['disponibles']


def test_post_disponibilidad_servicio_inexistente(client, db_conn):
    """Test POST /disponibilidad con servicio_id inválido devuelve error."""
    payload = {
        'negocio_id': 1,
        'servicio_id': 999,  # No existe
        'fecha': '2025-12-08'
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


# ======================================================================
# TESTS PARA DELETE /citas/<id> (Cancelar cita)
# ======================================================================

def test_delete_cita_exitoso(client, app):
    """Test DELETE /citas/<id> cancela una cita correctamente."""
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        
        # Crear cita
        cursor = conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 30, 'confirmado')")
        cita_id = cursor.lastrowid
        conn.commit()
    
    response = client.delete(f'/citas/{cita_id}')
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'cancelada' in data['message'].lower()
    
    # Verificar que estado cambió a 'cancelado'
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        cita = conn.execute('SELECT estado FROM citas WHERE id = ?', (cita_id,)).fetchone()
        assert cita['estado'] == 'cancelado'


def test_delete_cita_inexistente(client, db_conn):
    """Test DELETE /citas/<id> con ID inexistente devuelve 404."""
    response = client.delete('/citas/9999')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'no encontrada' in data['error'].lower()


def test_delete_cita_no_elimina_registro(client, app):
    """Test DELETE /citas/<id> NO elimina el registro físicamente."""
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        
        # Crear cita
        cursor = conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 30, 'confirmado')")
        cita_id = cursor.lastrowid
        conn.commit()
    
    client.delete(f'/citas/{cita_id}')
    
    # Verificar que el registro sigue existiendo
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        cita = conn.execute('SELECT * FROM citas WHERE id = ?', (cita_id,)).fetchone()
        assert cita is not None
        assert cita['estado'] == 'cancelado'


def test_post_disponibilidad_ignora_citas_canceladas(client, db_conn):
    """Test POST /disponibilidad no bloquea tramos de citas canceladas."""
    # Crear cita cancelada
    db_conn.execute("INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (1, 2, 1, '2025-12-08 10:00:00', 30, 'cancelado')")
    db_conn.commit()
    
    payload = {
        'negocio_id': 1,
        'servicio_id': 1,
        'fecha': '2025-12-08'
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = response.get_json()
    
    # 10:00 DEBE estar disponible (cita está cancelada)
    assert '2025-12-08 10:00:00' in data['disponibles']


# ======================================================================
# TESTS DE INTEGRACIÓN (Flujos completos)
# ======================================================================

def test_flujo_completo_reserva_y_cancelacion(client, app):
    """Test de flujo completo: consultar disponibilidad → crear cita → cancelar."""
    # 1. Consultar disponibilidad
    payload_disponibilidad = {
        'negocio_id': 1,
        'servicio_id': 1,
        'fecha': '2025-12-08'
    }
    response = client.post('/disponibilidad',
                          data=json.dumps(payload_disponibilidad),
                          content_type='application/json')
    assert response.status_code == 200
    tramos = response.get_json()['disponibles']
    assert len(tramos) > 0
    
    # 2. Crear cita con primer tramo disponible (10:00 AM para evitar conflictos)
    payload_cita = {
        'negocio_id': 1,
        'servicio_id': 1,
        'cliente_id': 2,
        'fecha_hora_cita': '2025-12-08 10:00:00'  # Hora específica conocida
    }
    response = client.post('/citas',
                          data=json.dumps(payload_cita),
                          content_type='application/json')
    assert response.status_code == 201
    cita_id = response.get_json()['id']
    
    # 3. Verificar que el tramo ya no está disponible
    response = client.post('/disponibilidad',
                          data=json.dumps(payload_disponibilidad),
                          content_type='application/json')
    tramos_actualizados = response.get_json()['disponibles']
    assert '2025-12-08 10:00:00' not in tramos_actualizados
    
    # 4. Cancelar la cita
    response = client.delete(f'/citas/{cita_id}')
    assert response.status_code == 200
    
    # 5. Verificar que el tramo vuelve a estar disponible
    response = client.post('/disponibilidad',
                          data=json.dumps(payload_disponibilidad),
                          content_type='application/json')
    tramos_final = response.get_json()['disponibles']
    assert '2025-12-08 10:00:00' in tramos_final
