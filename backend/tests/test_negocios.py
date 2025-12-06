"""
Tests para backend/routes/negocios.py
Valida los endpoints de gestión de negocios, servicios y horarios.
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
        conn.execute("INSERT INTO negocios (id, nombre, tipo_negocio, direccion, descripcion, propietario_id) VALUES (1, 'Peluquería Test', 'peluqueria', 'Calle Test 123', 'Descripción test', 1)")
        conn.execute("INSERT INTO servicios (id, negocio_id, nombre, precio, duracion_minutos) VALUES (1, 1, 'Corte', 15.0, 30)")
        conn.execute("INSERT INTO servicios (id, negocio_id, nombre, precio, duracion_minutos) VALUES (2, 1, 'Tinte', 45.0, 90)")
        conn.execute("INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (1, 0, '09:00:00', '13:00:00')")
        conn.execute("INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (1, 0, '16:00:00', '20:00:00')")
        
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


# ======================================================================
# TESTS PARA GET /negocios/ (Listar negocios)
# ======================================================================

def test_listar_negocios_sin_filtro(client, db_conn):
    """Test GET /negocios/ sin filtros devuelve todos los negocios."""
    response = client.get('/negocios/')
    
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['nombre'] == 'Peluquería Test'
    assert data[0]['propietario_nombre'] == 'Propietario Test'


def test_listar_negocios_con_filtro_propietario(client, app):
    """Test GET /negocios/?propietario_id=1 filtra por propietario."""
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        conn.execute("INSERT INTO negocios (nombre, tipo_negocio, direccion, propietario_id) VALUES ('Negocio 2', 'dentista', 'Calle 2', 2)")
        conn.commit()
    
    response = client.get('/negocios/?propietario_id=1')
    
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['propietario_id'] == 1


def test_listar_negocios_vacio(client, app):
    """Test GET /negocios/ con BD sin negocios devuelve array vacío."""
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        conn.execute("DELETE FROM servicios")
        conn.execute("DELETE FROM horarios_negocio")
        conn.execute("DELETE FROM negocios")
        conn.commit()
    
    response = client.get('/negocios/')
    assert response.status_code == 200
    assert response.get_json() == []


# ======================================================================
# TESTS PARA GET /negocios/<id> (Obtener negocio)
# ======================================================================

def test_obtener_negocio_existente(client, db_conn):
    """Test GET /negocios/1 devuelve datos completos del negocio."""
    response = client.get('/negocios/1')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == 1
    assert data['nombre'] == 'Peluquería Test'
    assert data['direccion'] == 'Calle Test 123'
    assert data['propietario_nombre'] == 'Propietario Test'
    assert data['propietario_id'] == 1


def test_obtener_negocio_inexistente(client, db_conn):
    """Test GET /negocios/999 con ID inexistente devuelve 404."""
    response = client.get('/negocios/999')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert 'no encontrado' in data['error'].lower()


# ======================================================================
# TESTS PARA POST /negocios/ (Crear negocio)
# ======================================================================

def test_crear_negocio_exitoso(client, app):
    """Test POST /negocios/ crea un negocio correctamente."""
    payload = {
        'nombre': 'Nuevo Negocio',
        'tipo_negocio': 'peluqueria',
        'direccion': 'Nueva Dirección 456',
        'propietario_id': 1
    }
    
    response = client.post('/negocios/',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data
    assert 'exitosamente' in data['message']
    
    # Verificar que se creó en BD
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        negocio = conn.execute('SELECT * FROM negocios WHERE id = ?', (data['id'],)).fetchone()
        assert negocio['nombre'] == 'Nuevo Negocio'


def test_crear_negocio_sin_nombre(client, db_conn):
    """Test POST /negocios/ sin nombre devuelve 400."""
    payload = {
        'direccion': 'Dirección',
        'propietario_id': 1
    }
    
    response = client.post('/negocios/',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    assert 'Faltan datos obligatorios' in response.get_json()['error']


def test_crear_negocio_sin_direccion(client, db_conn):
    """Test POST /negocios/ sin dirección devuelve 400."""
    payload = {
        'nombre': 'Negocio',
        'propietario_id': 1
    }
    
    response = client.post('/negocios/',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400


def test_crear_negocio_sin_propietario(client, db_conn):
    """Test POST /negocios/ sin propietario_id devuelve 400."""
    payload = {
        'nombre': 'Negocio',
        'direccion': 'Dirección'
    }
    
    response = client.post('/negocios/',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400


# ======================================================================
# TESTS PARA PUT /negocios/<id> (Actualizar negocio)
# ======================================================================

def test_actualizar_negocio_descripcion(client, app):
    """Test PUT /negocios/1 actualiza descripción."""
    payload = {
        'descripcion': 'Nueva descripción actualizada'
    }
    
    response = client.put('/negocios/1',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 200
    assert 'actualizado' in response.get_json()['message']
    
    # Verificar actualización
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        negocio = conn.execute('SELECT descripcion FROM negocios WHERE id = 1').fetchone()
        assert negocio['descripcion'] == 'Nueva descripción actualizada'


def test_actualizar_negocio_foto(client, app):
    """Test PUT /negocios/1 actualiza foto_url."""
    payload = {
        'foto_url': '/uploads/nuevo_negocio.jpg'
    }
    
    response = client.put('/negocios/1',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 200
    
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        negocio = conn.execute('SELECT foto_url FROM negocios WHERE id = 1').fetchone()
        assert negocio['foto_url'] == '/uploads/nuevo_negocio.jpg'


def test_actualizar_negocio_direccion(client, app):
    """Test PUT /negocios/1 actualiza dirección."""
    payload = {
        'direccion': 'Calle Nueva 789'
    }
    
    response = client.put('/negocios/1',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 200
    
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        negocio = conn.execute('SELECT direccion FROM negocios WHERE id = 1').fetchone()
        assert negocio['direccion'] == 'Calle Nueva 789'


def test_actualizar_negocio_multiples_campos(client, app):
    """Test PUT /negocios/1 actualiza múltiples campos."""
    payload = {
        'descripcion': 'Descripción multi',
        'direccion': 'Dirección multi',
        'foto_url': '/uploads/multi.jpg'
    }
    
    response = client.put('/negocios/1',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 200
    
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        negocio = conn.execute('SELECT * FROM negocios WHERE id = 1').fetchone()
        assert negocio['descripcion'] == 'Descripción multi'
        assert negocio['direccion'] == 'Dirección multi'
        assert negocio['foto_url'] == '/uploads/multi.jpg'


def test_actualizar_negocio_sin_datos(client, db_conn):
    """Test PUT /negocios/1 sin datos devuelve 400."""
    payload = {}
    
    response = client.put('/negocios/1',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 400
    assert 'No hay datos para actualizar' in response.get_json()['error']


def test_actualizar_negocio_inexistente(client, db_conn):
    """Test PUT /negocios/999 con ID inexistente devuelve 404."""
    payload = {
        'descripcion': 'Test'
    }
    
    response = client.put('/negocios/999',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 404


# ======================================================================
# TESTS PARA GET /negocios/<id>/servicios (Servicios de negocio)
# ======================================================================

def test_obtener_servicios_negocio(client, db_conn):
    """Test GET /negocios/1/servicios devuelve lista de servicios."""
    response = client.get('/negocios/1/servicios')
    
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['nombre'] == 'Corte'
    assert data[0]['precio'] == 15.0
    assert data[0]['duracion_minutos'] == 30
    assert data[1]['nombre'] == 'Tinte'


def test_obtener_servicios_negocio_sin_servicios(client, app):
    """Test GET /negocios/1/servicios con negocio sin servicios devuelve array vacío."""
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        conn.execute("DELETE FROM servicios WHERE negocio_id = 1")
        conn.commit()
    
    response = client.get('/negocios/1/servicios')
    assert response.status_code == 200
    assert response.get_json() == []


def test_obtener_servicios_negocio_inexistente(client, db_conn):
    """Test GET /negocios/999/servicios con negocio inexistente devuelve array vacío."""
    response = client.get('/negocios/999/servicios')
    assert response.status_code == 200
    assert response.get_json() == []


# ======================================================================
# TESTS PARA GET /negocios/<id>/horarios (Horarios de negocio)
# ======================================================================

def test_obtener_horarios_negocio(client, db_conn):
    """Test GET /negocios/1/horarios devuelve horarios ordenados."""
    response = client.get('/negocios/1/horarios')
    
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['dia_semana'] == 0
    assert data[0]['hora_apertura'] == '09:00:00'
    assert data[0]['hora_cierre'] == '13:00:00'
    assert data[1]['hora_apertura'] == '16:00:00'


def test_obtener_horarios_negocio_sin_horarios(client, app):
    """Test GET /negocios/1/horarios con negocio sin horarios devuelve array vacío."""
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        conn.execute("DELETE FROM horarios_negocio WHERE negocio_id = 1")
        conn.commit()
    
    response = client.get('/negocios/1/horarios')
    assert response.status_code == 200
    assert response.get_json() == []


def test_obtener_horarios_negocio_inexistente(client, db_conn):
    """Test GET /negocios/999/horarios con negocio inexistente devuelve array vacío."""
    response = client.get('/negocios/999/horarios')
    assert response.status_code == 200
    assert response.get_json() == []


# ======================================================================
# TESTS DE INTEGRACIÓN
# ======================================================================

def test_flujo_completo_crear_y_consultar(client, app):
    """Test de flujo completo: crear negocio → consultar → actualizar."""
    # 1. Crear negocio
    payload_crear = {
        'nombre': 'Integración Test',
        'tipo_negocio': 'dentista',
        'direccion': 'Calle Integración',
        'propietario_id': 1
    }
    response = client.post('/negocios/',
                          data=json.dumps(payload_crear),
                          content_type='application/json')
    assert response.status_code == 201
    negocio_id = response.get_json()['id']
    
    # 2. Consultar negocio
    response = client.get(f'/negocios/{negocio_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['nombre'] == 'Integración Test'
    
    # 3. Actualizar negocio
    payload_actualizar = {
        'descripcion': 'Descripción añadida'
    }
    response = client.put(f'/negocios/{negocio_id}',
                         data=json.dumps(payload_actualizar),
                         content_type='application/json')
    assert response.status_code == 200
    
    # 4. Verificar actualización
    response = client.get(f'/negocios/{negocio_id}')
    assert response.get_json()['descripcion'] == 'Descripción añadida'


def test_multiples_negocios_mismo_propietario(client, app):
    """Test que un propietario puede tener múltiples negocios."""
    negocios = [
        {'nombre': 'Negocio 1', 'tipo_negocio': 'peluqueria', 'direccion': 'Dir 1', 'propietario_id': 1},
        {'nombre': 'Negocio 2', 'tipo_negocio': 'dentista', 'direccion': 'Dir 2', 'propietario_id': 1},
        {'nombre': 'Negocio 3', 'tipo_negocio': 'mecanico', 'direccion': 'Dir 3', 'propietario_id': 1}
    ]
    
    for negocio in negocios:
        response = client.post('/negocios/',
                              data=json.dumps(negocio),
                              content_type='application/json')
        assert response.status_code == 201
    
    # Verificar que se listaron todos
    response = client.get('/negocios/?propietario_id=1')
    data = response.get_json()
    assert len(data) >= 3  # Al menos 3 (puede haber el de la fixture)
