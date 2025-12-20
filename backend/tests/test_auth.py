"""
Tests para backend/routes/auth.py
Valida los endpoints de registro y login con autenticación segura.
"""
import pytest
import json
import uuid
from io import BytesIO


# NOTE: Fixtures app, client y db_conn son proporcionadas por conftest.py (PostgreSQL Docker)


# ======================================================================
# TESTS PARA POST /auth/register (Registro)
# ======================================================================

def test_register_sin_foto_exitoso(client, app):
    """Test registro sin foto de perfil."""
    data = {
        'nombre': 'Juan Test',
        'email': f'juan_{uuid.uuid4().hex[:8]}@test.com',  # Email único
        'password': 'password123',
        'rol': 'cliente'
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['message'] == 'Registro exitoso'
    assert json_data['nombre'] == 'Juan Test'
    assert '@test.com' in json_data['email']  # Email dinámico con UUID
    assert json_data['rol'] == 'cliente'
    assert 'id' in json_data
    assert json_data['foto_perfil_url'] is None


def test_register_con_foto_exitoso(client, app):
    """Test registro con foto de perfil válida."""
    data = {
        'nombre': 'María Test',
        'email': f'maria_{uuid.uuid4().hex[:8]}@test.com',
        'password': 'password123',
        'rol': 'propietario',
        'foto_perfil': (BytesIO(b'fake image content'), 'test.jpg')
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['message'] == 'Registro exitoso'
    assert json_data['nombre'] == 'María Test'
    assert '@test.com' in json_data['email']  # Email dinámico con UUID
    assert json_data['rol'] == 'propietario'
    assert json_data['foto_perfil_url'] is not None
    assert json_data['foto_perfil_url'].startswith('/uploads/user_')
    assert json_data['foto_perfil_url'].endswith('.jpg')


def test_register_sin_nombre(client, app):
    """Test registro sin nombre devuelve 400."""
    data = {
        'email': f'test_{uuid.uuid4().hex[:8]}@test.com',
        'password': 'password123',
        'rol': 'cliente'
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'Faltan datos obligatorios' in json_data['error']


def test_register_sin_email(client, app):
    """Test registro sin email devuelve 400."""
    data = {
        'nombre': 'Test User',
        'password': 'password123',
        'rol': 'cliente'
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'Faltan datos obligatorios' in json_data['error']


def test_register_sin_password(client, app):
    """Test registro sin password devuelve 400."""
    data = {
        'nombre': 'Test User',
        'email': f'test_{uuid.uuid4().hex[:8]}@test.com',
        'rol': 'cliente'
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'Faltan datos obligatorios' in json_data['error']


def test_register_sin_rol(client, app):
    """Test registro sin rol devuelve 400."""
    data = {
        'nombre': 'Test User',
        'email': f'test_{uuid.uuid4().hex[:8]}@test.com',
        'password': 'password123'
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'Faltan datos obligatorios' in json_data['error']

# backend/tests/test_auth.py
# filepath: backend/tests/test_auth.py
# ... (mantener inicio igual) ...

def test_register_email_duplicado(client, app):
    """Test registro con email ya existente devuelve 409."""
    email_unico = f'test_{uuid.uuid4().hex[:8]}@example.com'
    
    # 🔧 Primer registro
    response1 = client.post('/auth/register', data={
        'nombre': 'Usuario 1',
        'email': email_unico,
        'password': 'password123',
        'rol': 'cliente'
    }, content_type='multipart/form-data')
    
    assert response1.status_code == 201
    
    # 🔧 Segundo registro con MISMO email
    response2 = client.post('/auth/register', data={
        'nombre': 'Usuario 2',
        'email': email_unico,  # MISMO email
        'password': 'password123',
        'rol': 'cliente'
    }, content_type='multipart/form-data')
    
    assert response2.status_code == 409
    assert 'error' in response2.get_json()


def test_login_exitoso(client, app):
    """Test login con credenciales válidas."""
    # 🔧 ATÓMICO: Registrar primero
    email_unico = f'test_{uuid.uuid4().hex[:8]}@example.com'
    
    reg_response = client.post('/auth/register', data={
        'nombre': 'Login Test',
        'email': email_unico,
        'password': 'password123',
        'rol': 'cliente'
    }, content_type='multipart/form-data')
    
    assert reg_response.status_code == 201
    
    # 🔧 Ahora hacer login
    login_response = client.post('/auth/login',
                                data=json.dumps({
                                    'email': email_unico,
                                    'password': 'password123'
                                }),
                                content_type='application/json')
    
    assert login_response.status_code == 200
    json_data = login_response.get_json()
    assert json_data['message'] == 'Login exitoso'
    assert json_data['nombre'] == 'Login Test'
    assert json_data['email'] == email_unico


def test_multiples_usuarios_independientes(client, app):
    """Test que múltiples usuarios pueden registrarse y hacer login independientemente."""
    # 🔧 Registrar 3 usuarios
    usuarios = [
        {'nombre': 'Usuario 1', 'email': f'user1_{uuid.uuid4().hex[:8]}@test.com', 'password': 'pass1', 'rol': 'cliente'},
        {'nombre': 'Usuario 2', 'email': f'user2_{uuid.uuid4().hex[:8]}@test.com', 'password': 'pass2', 'rol': 'propietario'},
        {'nombre': 'Usuario 3', 'email': f'user3_{uuid.uuid4().hex[:8]}@test.com', 'password': 'pass3', 'rol': 'cliente'}
    ]
    
    ids = []
    for user_data in usuarios:
        response = client.post('/auth/register', data=user_data, content_type='multipart/form-data')
        assert response.status_code == 201
        ids.append(response.get_json()['id'])
    
    # 🔧 Verificar que todos los IDs son diferentes
    assert len(set(ids)) == 3
    
    # 🔧 Hacer login con cada usuario
    for user_data in usuarios:
        login_response = client.post('/auth/login',
                                    data=json.dumps({
                                        'email': user_data['email'],
                                        'password': user_data['password']
                                    }),
                                    content_type='application/json')
        
        assert login_response.status_code == 200
        assert login_response.get_json()['nombre'] == user_data['nombre']