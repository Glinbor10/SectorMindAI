"""
Tests para backend/routes/citas.py
Valida los endpoints de creación, consulta, disponibilidad y cancelación de citas.
REESCRITURA: Todos los tests son 100% atómicos - crean sus propios datos.
"""
import pytest
import json
import uuid
from datetime import datetime, timedelta


# ======================================================================
# FIXTURES AUXILIARES: Crear datos mínimos para cada test
# ======================================================================

@pytest.fixture
def usuario_cliente(app, db_conn):
    """Fixture que crea un usuario cliente para citas."""
    cursor = db_conn.cursor()
    email = f'cliente_{uuid.uuid4().hex[:8]}@test.com'
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Cliente Test', email, 'hash', 'cliente')
    )
    user_id = cursor.fetchone()['id']
    db_conn.commit()
    cursor.close()
    return user_id


@pytest.fixture
def propietario_con_negocio(app, db_conn):
    """Fixture que crea un propietario con un negocio y 2 servicios."""
    cursor = db_conn.cursor()
    
    # Crear propietario
    email = f'prop_{uuid.uuid4().hex[:8]}@test.com'
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Propietario Test', email, 'hash', 'propietario')
    )
    prop_id = cursor.fetchone()['id']
    
    # Crear negocio
    cursor.execute(
        "INSERT INTO negocios (nombre, tipo_negocio, propietario_id, direccion) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Peluquería Test', 'peluqueria', prop_id, 'Calle Test 123')
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
    
    # Crear horarios: Lunes (0) y Martes (1)
    cursor.execute(
        "INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (%s, %s, %s, %s)",
        (neg_id, 0, '09:00:00', '13:00:00')  # Lunes mañana
    )
    cursor.execute(
        "INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (%s, %s, %s, %s)",
        (neg_id, 0, '16:00:00', '20:00:00')  # Lunes tarde
    )
    cursor.execute(
        "INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (%s, %s, %s, %s)",
        (neg_id, 1, '09:00:00', '14:00:00')  # Martes
    )
    
    db_conn.commit()
    cursor.close()
    
    return {
        'negocio_id': neg_id,
        'servicio_id_1': serv_id_1,
        'servicio_id_2': serv_id_2,
        'propietario_id': prop_id
    }


# ======================================================================
# TESTS PARA GET /citas (Listar citas)
# ======================================================================

def test_get_citas_sin_filtros(client):
    """Test GET /citas sin parámetros devuelve array (puede estar vacío o tener datos de manage_db)."""
    response = client.get('/citas')
    
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_get_citas_filtro_cliente_id(client, usuario_cliente, propietario_con_negocio):
    """Test GET /citas?cliente_id=X filtra por cliente."""
    # 🔧 Crear una cita para este cliente
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08 10:00:00'
    }
    
    create_response = client.post('/citas',
                                  data=json.dumps(payload),
                                  content_type='application/json')
    
    assert create_response.status_code == 201
    
    # 🔧 Ahora filtrar por cliente_id
    response = client.get(f'/citas?cliente_id={usuario_cliente}')
    
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) >= 1
    assert data[0]['cliente_id'] == usuario_cliente


def test_get_citas_filtro_negocio_id(client, usuario_cliente, propietario_con_negocio):
    """Test GET /citas?negocio_id=X filtra por negocio."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    # 🔧 Crear cita
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08 10:00:00'
    }
    
    client.post('/citas', data=json.dumps(payload), content_type='application/json')
    
    # 🔧 Filtrar por negocio
    response = client.get(f'/citas?negocio_id={negocio_id}')
    
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) >= 1
    # Todos deben tener el mismo negocio_id
    assert all(c['negocio_id'] == negocio_id for c in data)


def test_get_citas_sin_citas(client):
    """Test GET /citas puede devolver array vacío."""
    response = client.get('/citas')
    
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


# ======================================================================
# TESTS PARA POST /citas (Crear cita)
# ======================================================================

def test_post_citas_exitoso(client, usuario_cliente, propietario_con_negocio):
    """Test POST /citas crea una cita válida correctamente."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08 10:00:00'  # Lunes a las 10:00
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data
    assert 'exitosamente' in data['message'].lower()


def test_post_citas_formato_iso_T(client, usuario_cliente, propietario_con_negocio):
    """Acepta fecha con formato ISO 'YYYY-MM-DDTHH:MM' (sin segundos)."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']

    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08T10:00'
    }

    response = client.post('/citas', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data


def test_post_citas_con_usuario_id(client, propietario_con_negocio, db_conn):
    """Se puede crear cita usando 'usuario_id' en lugar de 'cliente_id'."""
    # Crear cliente
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Cliente UsuarioId', 'usuario_id@test.com', 'hash', 'cliente')
    )
    usuario_id = cursor.fetchone()['id']
    db_conn.commit()
    cursor.close()

    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']

    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'usuario_id': usuario_id,
        'fecha_hora_cita': '2025-12-08T11:00'
    }

    response = client.post('/citas', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data


def test_post_citas_sin_datos_obligatorios(client):
    """Test POST /citas sin datos obligatorios devuelve 400."""
    payload = {'negocio_id': 1}  # Faltan servicio_id y fecha_hora_cita
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    assert 'error' in response.get_json()


def test_post_citas_fuera_horario(client, usuario_cliente, propietario_con_negocio):
    """Test POST /citas fuera del horario devuelve 409."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    # 🔧 Lunes a las 8:00 (fuera de horario 9:00-13:00)
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08 08:00:00'
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 409
    assert 'error' in response.get_json()


def test_post_citas_solapamiento(client, usuario_cliente, propietario_con_negocio, app, db_conn):
    """Test POST /citas con solapamiento rechaza."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    # 🔧 Crear cita preexistente: Lunes 10:00-10:30
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (negocio_id, usuario_cliente, servicio_id, '2025-12-08 10:00:00', 30, 'confirmada')
    )
    db_conn.commit()
    cursor.close()
    
    # 🔧 Intentar crear cita solapada: Lunes 10:15-10:45
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08 10:15:00'
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 409
    assert 'solapa' in response.get_json()['error'].lower()


def test_post_citas_dia_cerrado(client, usuario_cliente, propietario_con_negocio):
    """Test POST /citas en día cerrado devuelve 409."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    # 🔧 Domingo (día cerrado)
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-07 10:00:00'  # Domingo
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 409
    assert 'cerrado' in response.get_json()['error'].lower()


def test_post_citas_servicio_largo_valido(client, usuario_cliente, propietario_con_negocio):
    """Test POST /citas con servicio largo (90 min) que cabe en horario."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_2']  # Tinte 90 min
    
    # 🔧 Lunes 10:00-11:30 debe caber en 9:00-13:00
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08 10:00:00'
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 201


def test_post_citas_servicio_largo_sale_horario(client, usuario_cliente, propietario_con_negocio):
    """Test POST /citas con servicio que sale del horario devuelve 409."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_2']  # Tinte 90 min
    
    # 🔧 Lunes 11:45-13:15 sale del horario (cierra a 13:00)
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08 11:45:00'
    }
    
    response = client.post('/citas',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 409


def test_post_citas_rechaza_servicio_de_otro_negocio(client, usuario_cliente, propietario_con_negocio, db_conn):
    """POST /citas debe rechazar un servicio que no pertenece al negocio indicado."""
    negocio_id = propietario_con_negocio['negocio_id']

    cursor = db_conn.cursor()
    # Segundo negocio con su servicio propio
    email = f'prop_cross_{uuid.uuid4().hex[:8]}@test.com'
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Propietario Cross', email, 'hash', 'propietario')
    )
    prop2_id = cursor.fetchone()['id']
    cursor.execute(
        "INSERT INTO negocios (nombre, tipo_negocio, propietario_id, direccion) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Negocio Cross', 'estetica', prop2_id, 'Calle Cross 1')
    )
    negocio2_id = cursor.fetchone()['id']
    cursor.execute(
        "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s) RETURNING id",
        (negocio2_id, 'Maquillaje Profesional', 60.0, 60)
    )
    servicio_otro_negocio_id = cursor.fetchone()['id']
    db_conn.commit()
    cursor.close()

    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_otro_negocio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08 10:00:00'
    }

    response = client.post('/citas', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 400
    assert 'servicio no válido para este negocio' in response.get_json()['error'].lower()


# ======================================================================
# TESTS PARA POST /disponibilidad (Consultar disponibilidad)
# ======================================================================

def test_post_disponibilidad_exitoso(client, propietario_con_negocio):
    """Test POST /disponibilidad devuelve tramos disponibles."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'fecha': '2025-12-08'  # Lunes
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'disponibles' in data
    assert len(data['disponibles']) > 0


def test_post_disponibilidad_sin_datos(client):
    """Test POST /disponibilidad sin datos devuelve 400."""
    payload = {'negocio_id': 1}
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400


def test_post_disponibilidad_dia_cerrado(client, propietario_con_negocio):
    """Test POST /disponibilidad en día cerrado devuelve array vacío."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'fecha': '2025-12-07'  # Domingo (cerrado)
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['disponibles'] == []


def test_post_disponibilidad_con_citas_existentes(client, usuario_cliente, propietario_con_negocio, app, db_conn):
    """Test POST /disponibilidad bloquea tramos con citas existentes."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    # 🔧 Crear cita a las 10:00
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (negocio_id, usuario_cliente, servicio_id, '2025-12-08 10:00:00', 30, 'confirmada')
    )
    db_conn.commit()
    cursor.close()
    
    # 🔧 Consultar disponibilidad
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'fecha': '2025-12-08'
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = response.get_json()
    
    # 10:00 NO debe estar disponible
    assert '2025-12-08 10:00:00' not in data['disponibles']


def test_post_disponibilidad_servicio_inexistente(client, propietario_con_negocio):
    """Test POST /disponibilidad con servicio inexistente."""
    negocio_id = propietario_con_negocio['negocio_id']
    
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': 999999,  # No existe
        'fecha': '2025-12-08'
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code in [400, 404]


def test_post_disponibilidad_rechaza_servicio_de_otro_negocio(client, propietario_con_negocio, db_conn):
    """POST /disponibilidad debe rechazar un servicio de otro negocio."""
    negocio_id = propietario_con_negocio['negocio_id']

    cursor = db_conn.cursor()
    email = f'prop_disp_{uuid.uuid4().hex[:8]}@test.com'
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Propietario Disp', email, 'hash', 'propietario')
    )
    prop2_id = cursor.fetchone()['id']
    cursor.execute(
        "INSERT INTO negocios (nombre, tipo_negocio, propietario_id, direccion) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Negocio Disp', 'estetica', prop2_id, 'Calle Disp 1')
    )
    negocio2_id = cursor.fetchone()['id']
    cursor.execute(
        "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s) RETURNING id",
        (negocio2_id, 'Servicio Ajeno', 40.0, 45)
    )
    servicio_otro_negocio_id = cursor.fetchone()['id']
    db_conn.commit()
    cursor.close()

    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_otro_negocio_id,
        'fecha': '2025-12-08'
    }

    response = client.post('/disponibilidad', data=json.dumps(payload), content_type='application/json')

    assert response.status_code == 400
    assert 'servicio' in response.get_json()['error'].lower()


# ======================================================================
# TESTS PARA DELETE /citas/<id> (Cancelar cita)
# ======================================================================

def test_delete_cita_exitoso(client, usuario_cliente, propietario_con_negocio):
    """Test DELETE /citas/<id> cancela una cita."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    # 🔧 Crear cita
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08 10:00:00'
    }
    
    create_response = client.post('/citas',
                                  data=json.dumps(payload),
                                  content_type='application/json')
    
    assert create_response.status_code == 201
    cita_id = create_response.get_json()['id']
    
    # 🔧 Cancelar cita
    response = client.delete(f'/citas/{cita_id}')
    
    assert response.status_code == 200
    assert 'cancelada' in response.get_json()['message'].lower()


def test_delete_cita_inexistente(client):
    """Test DELETE /citas/999999 con ID inexistente devuelve 404."""
    response = client.delete('/citas/999999')
    
    assert response.status_code == 404


def test_put_cita_rechaza_servicio_de_otro_negocio(client, usuario_cliente, propietario_con_negocio, db_conn):
    """PUT /citas/{id} debe rechazar cambiar una cita a un servicio de otro negocio."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_valido = propietario_con_negocio['servicio_id_1']

    # Crear cita válida inicial
    payload_create = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_valido,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': '2025-12-08 10:00:00'
    }
    create_response = client.post('/citas', data=json.dumps(payload_create), content_type='application/json')
    assert create_response.status_code == 201
    cita_id = create_response.get_json()['id']

    # Crear servicio de otro negocio
    cursor = db_conn.cursor()
    email = f'prop_put_{uuid.uuid4().hex[:8]}@test.com'
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Propietario PUT', email, 'hash', 'propietario')
    )
    prop2_id = cursor.fetchone()['id']
    cursor.execute(
        "INSERT INTO negocios (nombre, tipo_negocio, propietario_id, direccion) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Negocio PUT', 'estetica', prop2_id, 'Calle PUT 1')
    )
    negocio2_id = cursor.fetchone()['id']
    cursor.execute(
        "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s) RETURNING id",
        (negocio2_id, 'Servicio PUT Ajeno', 55.0, 30)
    )
    servicio_ajeno_id = cursor.fetchone()['id']
    db_conn.commit()
    cursor.close()

    payload_update = {
        'servicio_id': servicio_ajeno_id,
        'fecha_hora_cita': '2025-12-08 11:00:00'
    }
    response = client.put(f'/citas/{cita_id}', data=json.dumps(payload_update), content_type='application/json')

    assert response.status_code == 400
    assert 'servicio no válido para este negocio' in response.get_json()['error'].lower()


def test_get_citas_marca_servicio_invalido_si_hay_dato_corrupto(client, usuario_cliente, propietario_con_negocio, db_conn):
    """GET /citas no debe mostrar nombre de servicio ajeno cuando hay una cita corrupta histórica."""
    negocio_id = propietario_con_negocio['negocio_id']

    cursor = db_conn.cursor()
    # Crear otro negocio + servicio para forzar inconsistencia histórica
    email = f'prop_get_{uuid.uuid4().hex[:8]}@test.com'
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Propietario GET', email, 'hash', 'propietario')
    )
    prop2_id = cursor.fetchone()['id']
    cursor.execute(
        "INSERT INTO negocios (nombre, tipo_negocio, propietario_id, direccion) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Negocio GET', 'estetica', prop2_id, 'Calle GET 1')
    )
    negocio2_id = cursor.fetchone()['id']
    cursor.execute(
        "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s) RETURNING id",
        (negocio2_id, 'Servicio Extrano', 70.0, 60)
    )
    servicio_ajeno_id = cursor.fetchone()['id']

    # Insertar cita corrupta manualmente (simula datos históricos previos al fix)
    cursor.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (%s, %s, %s, %s, %s, %s)",
        (negocio_id, usuario_cliente, servicio_ajeno_id, '2025-12-08 12:00:00', 60, 'confirmada')
    )
    db_conn.commit()
    cursor.close()

    response = client.get(f'/citas?negocio_id={negocio_id}')

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) >= 1
    assert any(c['servicio_nombre'] == 'Servicio no válido para este negocio' for c in data)


def test_post_disponibilidad_ignora_citas_canceladas(client, usuario_cliente, propietario_con_negocio, app, db_conn):
    """Test POST /disponibilidad no bloquea tramos de citas canceladas."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    # 🔧 Crear cita cancelada
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (negocio_id, usuario_cliente, servicio_id, '2025-12-08 10:00:00', 30, 'cancelada')
    )
    db_conn.commit()
    cursor.close()
    
    # 🔧 Consultar disponibilidad
    payload = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'fecha': '2025-12-08'
    }
    
    response = client.post('/disponibilidad',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = response.get_json()
    
    # 10:00 SÍ debe estar disponible (porque la cita está cancelada)
    assert '2025-12-08 10:00:00' in data['disponibles']


# ======================================================================
# TESTS DE INTEGRACIÓN
# ======================================================================

def test_flujo_completo_reserva_y_cancelacion(client, usuario_cliente, propietario_con_negocio):
    """Test de flujo completo: consultar disponibilidad → crear cita → cancelar."""
    negocio_id = propietario_con_negocio['negocio_id']
    servicio_id = propietario_con_negocio['servicio_id_1']
    
    # 1. Consultar disponibilidad
    payload_disponibilidad = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'fecha': '2025-12-08'
    }
    response = client.post('/disponibilidad',
                          data=json.dumps(payload_disponibilidad),
                          content_type='application/json')
    
    assert response.status_code == 200
    disponibles = response.get_json()['disponibles']
    assert len(disponibles) > 0
    
    # 2. Crear cita en primer tramo disponible
    payload_cita = {
        'negocio_id': negocio_id,
        'servicio_id': servicio_id,
        'cliente_id': usuario_cliente,
        'fecha_hora_cita': disponibles[0]
    }
    response = client.post('/citas',
                          data=json.dumps(payload_cita),
                          content_type='application/json')
    
    assert response.status_code == 201
    cita_id = response.get_json()['id']
    
    # 3. Verificar que la cita fue creada
    response = client.get('/citas')
    assert any(c['id'] == cita_id for c in response.get_json())
    
    # 4. Cancelar la cita
    response = client.delete(f'/citas/{cita_id}')
    assert response.status_code == 200
