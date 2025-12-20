"""
Tests para backend/routes/negocios.py
Valida los endpoints de gestión de negocios.
REESCRITURA: Todos los tests son 100% atómicos - crean sus propios datos.
"""
import pytest
import json
import uuid
from io import BytesIO


# ======================================================================
# FIXTURES AUXILIARES
# ======================================================================

@pytest.fixture
def propietario(app, db_conn):
    """Fixture que crea un usuario propietario."""
    cursor = db_conn.cursor()
    email = f'prop_{uuid.uuid4().hex[:8]}@test.com'
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Propietario Test', email, 'hash', 'propietario')
    )
    prop_id = cursor.fetchone()['id']
    db_conn.commit()
    cursor.close()
    return prop_id


@pytest.fixture
def negocio_con_servicios(app, db_conn, propietario):
    """Fixture que crea un negocio con servicios."""
    cursor = db_conn.cursor()
    
    # Crear negocio
    cursor.execute(
        "INSERT INTO negocios (nombre, tipo_negocio, propietario_id, direccion, descripcion) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        ('Negocio Test', 'peluqueria', propietario, 'Calle Test 123', 'Descripción')
    )
    neg_id = cursor.fetchone()['id']
    
    # Crear 2 servicios
    cursor.execute(
        "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s) RETURNING id",
        (neg_id, 'Corte', 15.0, 30)
    )
    serv_id_1 = cursor.fetchone()['id']
    
    cursor.execute(
        "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s) RETURNING id",
        (neg_id, 'Tinte', 45.0, 90)
    )
    serv_id_2 = cursor.fetchone()['id']
    
    db_conn.commit()
    cursor.close()
    
    return {
        'negocio_id': neg_id,
        'propietario_id': propietario,
        'servicio_id_1': serv_id_1,
        'servicio_id_2': serv_id_2
    }


# ======================================================================
# TESTS PARA GET /negocios/ (Listar negocios)
# ======================================================================

def test_listar_negocios_sin_filtro(client, negocio_con_servicios):
    """Test GET /negocios/ devuelve lista de negocios."""
    response = client.get('/negocios/')
    
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1  # Al menos el que creamos


def test_listar_negocios_con_filtro_propietario(client, propietario, negocio_con_servicios):
    """Test GET /negocios/?propietario_id=X filtra por propietario."""
    response = client.get(f'/negocios/?propietario_id={propietario}')
    
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) >= 1
    assert all(n['propietario_id'] == propietario for n in data)


def test_listar_negocios_vacio(client):
    """Test GET /negocios/ con propietario sin negocios devuelve array vacío."""
    # Usar propietario_id que no existe
    response = client.get('/negocios/?propietario_id=999999')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data == []


# ======================================================================
# TESTS PARA GET /negocios/<id> (Obtener negocio)
# ======================================================================

def test_obtener_negocio_existente(client, negocio_con_servicios):
    """Test GET /negocios/<id> devuelve datos del negocio."""
    neg_id = negocio_con_servicios['negocio_id']
    
    response = client.get(f'/negocios/{neg_id}')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == neg_id
    assert data['nombre'] == 'Negocio Test'
    assert data['tipo_negocio'] == 'peluqueria'


def test_obtener_negocio_inexistente(client):
    """Test GET /negocios/999999 con ID inexistente devuelve 404."""
    response = client.get('/negocios/999999')
    
    assert response.status_code == 404


# ======================================================================
# TESTS PARA POST /negocios/ (Crear negocio)
# ======================================================================

def test_crear_negocio_exitoso(client, propietario):
    """Test POST /negocios/ crea un negocio correctamente."""
    payload = {
        'nombre': 'Mi Negocio Nuevo',
        'tipo_negocio': 'dentista',
        'direccion': 'Calle Nueva 456',
        'propietario_id': propietario,
        'descripcion': 'Descripción del negocio'
    }
    
    response = client.post('/negocios/',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data
    
    # ✅ Verificar consultando el negocio
    get_response = client.get(f"/negocios/{data['id']}")
    assert get_response.status_code == 200
    assert get_response.get_json()['nombre'] == 'Mi Negocio Nuevo'


def test_crear_negocio_sin_nombre(client, propietario):
    """Test POST /negocios/ sin nombre devuelve 400."""
    payload = {
        'tipo_negocio': 'dentista',
        'direccion': 'Calle Test',
        'propietario_id': propietario
    }
    
    response = client.post('/negocios/',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400


def test_crear_negocio_sin_direccion(client, propietario):
    """Test POST /negocios/ sin dirección devuelve 400."""
    payload = {
        'nombre': 'Negocio Test',
        'tipo_negocio': 'peluqueria',
        'propietario_id': propietario
    }
    
    response = client.post('/negocios/',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400


def test_crear_negocio_sin_propietario(client):
    """Test POST /negocios/ sin propietario devuelve 400."""
    payload = {
        'nombre': 'Negocio Test',
        'tipo_negocio': 'peluqueria',
        'direccion': 'Calle Test 123'
    }
    
    response = client.post('/negocios/',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400


# ======================================================================
# TESTS PARA PUT /negocios/<id> (Actualizar negocio)
# ======================================================================

def test_actualizar_negocio_descripcion(client, negocio_con_servicios):
    """Test PUT /negocios/<id> actualiza descripción."""
    neg_id = negocio_con_servicios['negocio_id']
    
    payload = {'descripcion': 'Nueva descripción'}
    
    response = client.put(f'/negocios/{neg_id}',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 200
    
    # ✅ Verificar consultando
    get_response = client.get(f'/negocios/{neg_id}')
    assert get_response.get_json()['descripcion'] == 'Nueva descripción'


def test_actualizar_negocio_foto(client, negocio_con_servicios):
    """Test PUT /negocios/<id> actualiza foto_url."""
    neg_id = negocio_con_servicios['negocio_id']
    
    payload = {'foto_url': 'https://example.com/new-photo.jpg'}
    
    response = client.put(f'/negocios/{neg_id}',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 200
    
    # ✅ Verificar consultando
    get_response = client.get(f'/negocios/{neg_id}')
    assert get_response.get_json()['foto_url'] == 'https://example.com/new-photo.jpg'


def test_actualizar_negocio_direccion(client, negocio_con_servicios):
    """Test PUT /negocios/<id> actualiza dirección."""
    neg_id = negocio_con_servicios['negocio_id']
    
    payload = {'direccion': 'Nueva Calle 789'}
    
    response = client.put(f'/negocios/{neg_id}',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 200
    
    # ✅ Verificar consultando
    get_response = client.get(f'/negocios/{neg_id}')
    assert get_response.get_json()['direccion'] == 'Nueva Calle 789'


def test_actualizar_negocio_multiples_campos(client, negocio_con_servicios):
    """Test PUT /negocios/<id> actualiza múltiples campos."""
    neg_id = negocio_con_servicios['negocio_id']
    
    payload = {
        'nombre': 'Nombre Actualizado',
        'descripcion': 'Nueva descripción',
        'direccion': 'Calle Actualizada'
    }
    
    response = client.put(f'/negocios/{neg_id}',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 200
    
    # ✅ Verificar consultando
    get_response = client.get(f'/negocios/{neg_id}')
    data = get_response.get_json()
    assert data['nombre'] == 'Nombre Actualizado'
    assert data['descripcion'] == 'Nueva descripción'
    assert data['direccion'] == 'Calle Actualizada'


def test_actualizar_negocio_sin_datos(client, negocio_con_servicios):
    """Test PUT /negocios/<id> sin datos no falla."""
    neg_id = negocio_con_servicios['negocio_id']
    
    payload = {}
    
    response = client.put(f'/negocios/{neg_id}',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code in [200, 400]  # Puede ser 200 (sin cambios) o 400 (error)


def test_actualizar_negocio_inexistente(client):
    """Test PUT /negocios/999999 con ID inexistente devuelve 404."""
    payload = {'descripcion': 'Nueva descripción'}
    
    response = client.put('/negocios/999999',
                         data=json.dumps(payload),
                         content_type='application/json')
    
    assert response.status_code == 404


# ======================================================================
# TESTS PARA GET /negocios/<id>/servicios (Obtener servicios)
# ======================================================================

def test_obtener_servicios_negocio(client, negocio_con_servicios):
    """Test GET /negocios/<id>/servicios devuelve servicios del negocio."""
    neg_id = negocio_con_servicios['negocio_id']
    
    response = client.get(f'/negocios/{neg_id}/servicios')
    
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2  # Creamos 2 servicios
    assert data[0]['nombre'] in ['Corte', 'Tinte']
    assert data[1]['nombre'] in ['Corte', 'Tinte']


def test_obtener_servicios_negocio_sin_servicios(client, propietario, app, db_conn):
    """Test GET /negocios/<id>/servicios con negocio sin servicios."""
    # 🔧 Crear negocio SIN servicios
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO negocios (nombre, tipo_negocio, propietario_id, direccion) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Negocio Sin Servicios', 'peluqueria', propietario, 'Calle Test')
    )
    neg_id = cursor.fetchone()['id']
    db_conn.commit()
    cursor.close()
    
    response = client.get(f'/negocios/{neg_id}/servicios')
    
    assert response.status_code == 200
    assert response.get_json() == []


def test_obtener_servicios_negocio_inexistente(client):
    """Test GET /negocios/999999/servicios con negocio inexistente."""
    response = client.get('/negocios/999999/servicios')
    
    assert response.status_code == 200
    assert response.get_json() == []


# ======================================================================
# TESTS PARA GET /negocios/<id>/horarios (Obtener horarios)
# ======================================================================

def test_obtener_horarios_negocio(client, propietario, app, db_conn):
    """Test GET /negocios/<id>/horarios devuelve horarios creados."""
    # 🔧 Crear negocio con horarios
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO negocios (nombre, tipo_negocio, propietario_id, direccion) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Negocio Con Horarios', 'peluqueria', propietario, 'Calle Test')
    )
    neg_id = cursor.fetchone()['id']
    
    # Insertar horarios
    cursor.execute(
        "INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (%s, %s, %s, %s)",
        (neg_id, 0, '09:00:00', '13:00:00')  # Lunes mañana
    )
    cursor.execute(
        "INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (%s, %s, %s, %s)",
        (neg_id, 0, '16:00:00', '20:00:00')  # Lunes tarde
    )
    
    db_conn.commit()
    cursor.close()
    
    response = client.get(f'/negocios/{neg_id}/horarios')
    
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['dia_semana'] == 0
    assert data[0]['hora_apertura'] == '09:00:00'


def test_obtener_horarios_negocio_sin_horarios(client, propietario, app, db_conn):
    """Test GET /negocios/<id>/horarios con negocio sin horarios."""
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO negocios (nombre, tipo_negocio, propietario_id, direccion) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Negocio Sin Horarios', 'dentista', propietario, 'Calle Test')
    )
    neg_id = cursor.fetchone()['id']
    db_conn.commit()
    cursor.close()
    
    response = client.get(f'/negocios/{neg_id}/horarios')
    
    assert response.status_code == 200
    assert response.get_json() == []


def test_obtener_horarios_negocio_inexistente(client):
    """Test GET /negocios/999999/horarios con negocio inexistente."""
    response = client.get('/negocios/999999/horarios')
    
    assert response.status_code == 200
    assert response.get_json() == []


# ======================================================================
# TESTS DE INTEGRACIÓN
# ======================================================================

def test_flujo_completo_crear_y_consultar(client, propietario):
    """Test de flujo completo: crear negocio → consultar → actualizar."""
    # 1. Crear negocio
    payload = {
        'nombre': 'Mi Nuevo Negocio',
        'tipo_negocio': 'fisioterapia',
        'direccion': 'Av. Principal 100',
        'propietario_id': propietario,
        'descripcion': 'Descripción inicial'
    }
    
    create_response = client.post('/negocios/',
                                 data=json.dumps(payload),
                                 content_type='application/json')
    
    assert create_response.status_code == 201
    neg_id = create_response.get_json()['id']
    
    # 2. Consultar negocio
    get_response = client.get(f'/negocios/{neg_id}')
    assert get_response.status_code == 200
    assert get_response.get_json()['nombre'] == 'Mi Nuevo Negocio'
    
    # 3. Actualizar negocio
    update_payload = {'descripcion': 'Descripción actualizada'}
    update_response = client.put(f'/negocios/{neg_id}',
                                data=json.dumps(update_payload),
                                content_type='application/json')
    
    assert update_response.status_code == 200
    
    # ✅ Verificar cambio
    verify_response = client.get(f'/negocios/{neg_id}')
    assert verify_response.get_json()['descripcion'] == 'Descripción actualizada'


def test_multiples_negocios_mismo_propietario(client, propietario):
    """Test que un propietario puede tener múltiples negocios."""
    # 🔧 Crear 3 negocios para el mismo propietario
    payloads = [
        {'nombre': 'Negocio 1', 'tipo_negocio': 'peluqueria', 'direccion': 'Calle 1', 'propietario_id': propietario},
        {'nombre': 'Negocio 2', 'tipo_negocio': 'dentista', 'direccion': 'Calle 2', 'propietario_id': propietario},
        {'nombre': 'Negocio 3', 'tipo_negocio': 'fisioterapia', 'direccion': 'Calle 3', 'propietario_id': propietario}
    ]
    
    ids = []
    for payload in payloads:
        response = client.post('/negocios/',
                              data=json.dumps(payload),
                              content_type='application/json')
        assert response.status_code == 201
        ids.append(response.get_json()['id'])
    
    # 🔧 Filtrar por propietario
    response = client.get(f'/negocios/?propietario_id={propietario}')
    data = response.get_json()
    
    assert len(data) >= 3  # Al menos los 3 que creamos
    propietario_ids = [n['propietario_id'] for n in data]
    assert all(pid == propietario for pid in propietario_ids)
