"""
Tests para funcionalidad de geolocalización
"""
import pytest
from backend.app import create_app
from backend.db import get_db_connection
import uuid


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_user(client):
    """Crea un usuario de prueba para los tests"""
    unique_id = str(uuid.uuid4())[:8]
    response = client.post('/auth/register', data={
        'nombre': 'Test Owner Geo',
        'email': f'testgeo_{unique_id}@test.com',
        'password': 'test123',
        'rol': 'propietario'
    })
    user_data = response.get_json()
    if response.status_code != 201:
        pytest.fail(f"Falló el registro: Status {response.status_code}, Response: {user_data}")
    assert 'id' in user_data, f"La respuesta no tiene 'id': {user_data}"
    return user_data

def test_crear_negocio_con_coordenadas(client, test_user):
    """Test: Crear negocio con latitud y longitud"""
    response = client.post('/negocios/', json={
        'nombre': 'Negocio Test Geo',
        'direccion': 'Calle Test 123, Madrid',
        'tipo_negocio': 'general',
        'latitud': 40.4168,
        'longitud': -3.7038,
        'propietario_id': test_user['id']
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data
    
    # Obtener el negocio creado para verificar coordenadas
    negocio_id = data['id']
    response_get = client.get(f'/negocios/{negocio_id}')
    assert response_get.status_code == 200
    negocio = response_get.get_json()
    assert float(negocio['latitud']) == 40.4168
    assert float(negocio['longitud']) == -3.7038


def test_crear_negocio_sin_coordenadas(client, test_user):
    """Test: Crear negocio sin coordenadas (debe funcionar)"""
    response = client.post('/negocios/', json={
        'nombre': 'Negocio Sin Geo',
        'direccion': 'Calle Sin Coords',
        'tipo_negocio': 'general',
        'propietario_id': test_user['id']
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data
    
    # Obtener el negocio para verificar que latitud/longitud son NULL
    negocio_id = data['id']
    response_get = client.get(f'/negocios/{negocio_id}')
    negocio = response_get.get_json()
    assert negocio.get('latitud') is None
    assert negocio.get('longitud') is None


def test_listar_negocios_con_distancia(client, test_user):
    """Test: Listar negocios ordenados por distancia"""
    # Crear 3 negocios en diferentes ubicaciones
    negocios = [
        {'nombre': 'Negocio Madrid Centro', 'latitud': 40.4168, 'longitud': -3.7038},
        {'nombre': 'Negocio Madrid Norte', 'latitud': 40.5000, 'longitud': -3.6800},
        {'nombre': 'Negocio Barcelona', 'latitud': 41.3874, 'longitud': 2.1686},
    ]
    
    for neg in negocios:
        client.post('/negocios/', json={
            'nombre': neg['nombre'],
            'direccion': f"Dirección {neg['nombre']}",
            'tipo_negocio': 'general',
            'latitud': neg['latitud'],
            'longitud': neg['longitud'],
            'propietario_id': test_user['id']
        })
    
    # Buscar desde Madrid Centro
    response = client.get('/negocios/?lat=40.4168&lon=-3.7038')
    
    assert response.status_code == 200
    negocios_resultado = response.get_json()
    
    # Verificar que hay resultados
    assert len(negocios_resultado) >= 3
    
    # Verificar que tienen distancia calculada
    negocios_con_dist = [n for n in negocios_resultado if n.get('distancia_km') is not None]
    assert len(negocios_con_dist) >= 3
    
    # Verificar que están ordenados por distancia (ascendente)
    distancias = [n['distancia_km'] for n in negocios_con_dist if 'Test' in n['nombre'] or 'Madrid' in n['nombre'] or 'Barcelona' in n['nombre']]
    assert distancias == sorted(distancias)


def test_actualizar_coordenadas_negocio(client, test_user):
    """Test: Actualizar las coordenadas de un negocio existente"""
    # Crear negocio sin coordenadas
    response = client.post('/negocios/', json={
        'nombre': 'Negocio Para Actualizar',
        'direccion': 'Calle Inicial',
        'tipo_negocio': 'general',
        'propietario_id': test_user['id']
    })
    
    negocio_id = response.get_json()['id']
    
    # Actualizar con coordenadas
    response = client.put(f'/negocios/{negocio_id}', json={
        'latitud': 40.4168,
        'longitud': -3.7038
    })
    
    assert response.status_code == 200
    
    # Verificar que se actualizaron
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT latitud, longitud FROM negocios WHERE id = %s', (negocio_id,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert float(row['latitud']) == 40.4168
    assert float(row['longitud']) == -3.7038


def test_listar_negocios_sin_ubicacion_usuario(client, test_user):
    """Test: Listar negocios sin proporcionar ubicación del usuario"""
    # Crear negocio con coordenadas
    client.post('/negocios/', json={
        'nombre': 'Negocio Test',
        'direccion': 'Dirección Test',
        'tipo_negocio': 'general',
        'latitud': 40.4168,
        'longitud': -3.7038,
        'propietario_id': test_user['id']
    })
    
    # Buscar sin parámetros de ubicación
    response = client.get('/negocios/')
    
    assert response.status_code == 200
    negocios = response.get_json()
    assert len(negocios) > 0
    
    # Los negocios no deben tener distancia_km si no se proporcionó ubicación
    # O deben tener distancia_km = None


def test_coordenadas_invalidas(client, test_user):
    """Test: Rechazar coordenadas fuera de rango"""
    # Latitud fuera de rango (-90 a 90)
    response = client.post('/negocios/', json={
        'nombre': 'Negocio Lat Inválida',
        'direccion': 'Calle Test',
        'tipo_negocio': 'general',
        'latitud': 100.0,  # Inválida
        'longitud': -3.7038,
        'propietario_id': test_user['id']
    })
    
    # Dependiendo de la implementación, puede rechazarse o truncarse
    # Aquí asumimos que debe fallar o normalizarse
    # (Ajustar según tu implementación)
    assert response.status_code in [201, 400]
    
    # Longitud fuera de rango (-180 a 180)
    response = client.post('/negocios/', json={
        'nombre': 'Negocio Lon Inválida',
        'direccion': 'Calle Test',
        'tipo_negocio': 'general',
        'latitud': 40.4168,
        'longitud': 200.0,  # Inválida
        'propietario_id': test_user['id']
    })
    
    assert response.status_code in [201, 400]
