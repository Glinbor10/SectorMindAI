"""
Tests para backend/routes/auth.py
Valida los endpoints de registro y login con autenticación segura.
"""
import pytest
import json
import sqlite3
import tempfile
import os
from io import BytesIO
from backend.app import create_app


@pytest.fixture
def app():
    """Crea aplicación Flask con BD temporal y carpeta de uploads temporal."""
    # Crear archivo temporal para BD
    db_fd, db_path = tempfile.mkstemp()
    upload_dir = tempfile.mkdtemp()  # Carpeta temporal para uploads
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = upload_dir  # Configurar carpeta temporal
    
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
        
        conn.commit()
        conn.close()
    
    yield app
    
    # Cleanup: eliminar BD y archivos de uploads temporales
    os.close(db_fd)
    os.unlink(db_path)
    
    import shutil
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)


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
# TESTS PARA POST /auth/register (Registro)
# ======================================================================

def test_register_sin_foto_exitoso(client, app):
    """Test registro sin foto de perfil."""
    data = {
        'nombre': 'Juan Test',
        'email': 'juan@test.com',
        'password': 'password123',
        'rol': 'cliente'
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['message'] == 'Registro exitoso'
    assert json_data['nombre'] == 'Juan Test'
    assert json_data['email'] == 'juan@test.com'
    assert json_data['rol'] == 'cliente'
    assert 'id' in json_data
    assert json_data['foto_perfil_url'] is None


def test_register_con_foto_exitoso(client, app):
    """Test registro con foto de perfil válida."""
    data = {
        'nombre': 'María Test',
        'email': 'maria@test.com',
        'password': 'password123',
        'rol': 'propietario',
        'foto_perfil': (BytesIO(b'fake image content'), 'test.jpg')
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['message'] == 'Registro exitoso'
    assert json_data['nombre'] == 'María Test'
    assert json_data['email'] == 'maria@test.com'
    assert json_data['rol'] == 'propietario'
    assert json_data['foto_perfil_url'] is not None
    assert json_data['foto_perfil_url'].startswith('/uploads/user_')
    assert json_data['foto_perfil_url'].endswith('.jpg')


def test_register_sin_nombre(client, app):
    """Test registro sin nombre devuelve 400."""
    data = {
        'email': 'test@test.com',
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
        'email': 'test@test.com',
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
        'email': 'test@test.com',
        'password': 'password123'
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'Faltan datos obligatorios' in json_data['error']


def test_register_email_duplicado(client, app):
    """Test registro con email ya existente devuelve 409."""
    data = {
        'nombre': 'Usuario 1',
        'email': 'duplicado@test.com',
        'password': 'password123',
        'rol': 'cliente'
    }
    
    # Primer registro
    response1 = client.post('/auth/register', data=data, content_type='multipart/form-data')
    assert response1.status_code == 201
    
    # Segundo registro con mismo email
    data2 = {
        'nombre': 'Usuario 2',
        'email': 'duplicado@test.com',
        'password': 'otrapassword',
        'rol': 'propietario'
    }
    
    response2 = client.post('/auth/register', data=data2, content_type='multipart/form-data')
    assert response2.status_code == 409
    json_data = response2.get_json()
    assert 'email ya está registrado' in json_data['error']


def test_register_password_se_hashea(client, app):
    """Test que la contraseña se guarda hasheada en BD."""
    data = {
        'nombre': 'Test Hash',
        'email': 'hash@test.com',
        'password': 'MiPasswordSecreta123',
        'rol': 'cliente'
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    user_id = response.get_json()['id']
    
    # Verificar que el password en BD NO es el original
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        user = conn.execute('SELECT password_hash FROM usuarios WHERE id = ?', (user_id,)).fetchone()
        
        assert user['password_hash'] != 'MiPasswordSecreta123'
        assert user['password_hash'].startswith('scrypt:')  # Hash de Werkzeug


def test_register_foto_extension_invalida(client, app):
    """Test registro con extensión de imagen inválida."""
    data = {
        'nombre': 'Test Invalid',
        'email': 'invalid@test.com',
        'password': 'password123',
        'rol': 'cliente',
        'foto_perfil': (BytesIO(b'fake image'), 'test.txt')  # Extensión no permitida
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    
    # El registro debería ser exitoso pero sin foto
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['foto_perfil_url'] is None


def test_register_diferentes_roles(client, app):
    """Test registro con diferentes roles (cliente y propietario)."""
    # Registro como cliente
    data_cliente = {
        'nombre': 'Cliente Test',
        'email': 'cliente@test.com',
        'password': 'password123',
        'rol': 'cliente'
    }
    response1 = client.post('/auth/register', data=data_cliente, content_type='multipart/form-data')
    assert response1.status_code == 201
    assert response1.get_json()['rol'] == 'cliente'
    
    # Registro como propietario
    data_propietario = {
        'nombre': 'Propietario Test',
        'email': 'propietario@test.com',
        'password': 'password123',
        'rol': 'propietario'
    }
    response2 = client.post('/auth/register', data=data_propietario, content_type='multipart/form-data')
    assert response2.status_code == 201
    assert response2.get_json()['rol'] == 'propietario'


# ======================================================================
# TESTS PARA POST /auth/login (Login)
# ======================================================================

def test_login_exitoso(client, app):
    """Test login con credenciales válidas."""
    # Primero registrar usuario
    data_registro = {
        'nombre': 'Login Test',
        'email': 'login@test.com',
        'password': 'password123',
        'rol': 'cliente'
    }
    client.post('/auth/register', data=data_registro, content_type='multipart/form-data')
    
    # Ahora hacer login
    data_login = {
        'email': 'login@test.com',
        'password': 'password123'
    }
    
    response = client.post('/auth/login',
                          data=json.dumps(data_login),
                          content_type='application/json')
    
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['message'] == 'Login exitoso'
    assert json_data['nombre'] == 'Login Test'
    assert json_data['email'] == 'login@test.com'
    assert json_data['rol'] == 'cliente'
    assert 'id' in json_data


def test_login_sin_email(client, app):
    """Test login sin email devuelve 400."""
    data = {
        'password': 'password123'
    }
    
    response = client.post('/auth/login',
                          data=json.dumps(data),
                          content_type='application/json')
    
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'Faltan credenciales' in json_data['error']


def test_login_sin_password(client, app):
    """Test login sin password devuelve 400."""
    data = {
        'email': 'test@test.com'
    }
    
    response = client.post('/auth/login',
                          data=json.dumps(data),
                          content_type='application/json')
    
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'Faltan credenciales' in json_data['error']


def test_login_email_inexistente(client, app):
    """Test login con email que no existe devuelve 401."""
    data = {
        'email': 'noexiste@test.com',
        'password': 'password123'
    }
    
    response = client.post('/auth/login',
                          data=json.dumps(data),
                          content_type='application/json')
    
    assert response.status_code == 401
    json_data = response.get_json()
    assert 'Credenciales inválidas' in json_data['error']


def test_login_password_incorrecta(client, app):
    """Test login con password incorrecta devuelve 401."""
    # Registrar usuario
    data_registro = {
        'nombre': 'Test Wrong Pass',
        'email': 'wrongpass@test.com',
        'password': 'password123',
        'rol': 'cliente'
    }
    client.post('/auth/register', data=data_registro, content_type='multipart/form-data')
    
    # Intentar login con password incorrecta
    data_login = {
        'email': 'wrongpass@test.com',
        'password': 'passwordINCORRECTA'
    }
    
    response = client.post('/auth/login',
                          data=json.dumps(data_login),
                          content_type='application/json')
    
    assert response.status_code == 401
    json_data = response.get_json()
    assert 'Credenciales inválidas' in json_data['error']


def test_login_devuelve_todos_los_datos(client, app):
    """Test que login devuelve todos los datos del usuario incluyendo foto."""
    # Registrar usuario con foto
    data_registro = {
        'nombre': 'Full Data Test',
        'email': 'fulldata@test.com',
        'password': 'password123',
        'rol': 'propietario',
        'foto_perfil': (BytesIO(b'fake image'), 'photo.png')
    }
    reg_response = client.post('/auth/register', data=data_registro, content_type='multipart/form-data')
    foto_url = reg_response.get_json()['foto_perfil_url']
    
    # Hacer login
    data_login = {
        'email': 'fulldata@test.com',
        'password': 'password123'
    }
    
    response = client.post('/auth/login',
                          data=json.dumps(data_login),
                          content_type='application/json')
    
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['nombre'] == 'Full Data Test'
    assert json_data['email'] == 'fulldata@test.com'
    assert json_data['rol'] == 'propietario'
    assert json_data['foto_perfil_url'] == foto_url
    assert 'id' in json_data


def test_login_case_sensitive_password(client, app):
    """Test que el password es case-sensitive."""
    # Registrar usuario
    data_registro = {
        'nombre': 'Case Test',
        'email': 'case@test.com',
        'password': 'Password123',  # Con mayúscula
        'rol': 'cliente'
    }
    client.post('/auth/register', data=data_registro, content_type='multipart/form-data')
    
    # Intentar login con minúscula
    data_login = {
        'email': 'case@test.com',
        'password': 'password123'  # Todo minúscula
    }
    
    response = client.post('/auth/login',
                          data=json.dumps(data_login),
                          content_type='application/json')
    
    assert response.status_code == 401


def test_login_no_expone_password_hash(client, app):
    """Test que login NO devuelve el password_hash en la respuesta."""
    # Registrar y hacer login
    data_registro = {
        'nombre': 'Security Test',
        'email': 'security@test.com',
        'password': 'password123',
        'rol': 'cliente'
    }
    client.post('/auth/register', data=data_registro, content_type='multipart/form-data')
    
    data_login = {
        'email': 'security@test.com',
        'password': 'password123'
    }
    
    response = client.post('/auth/login',
                          data=json.dumps(data_login),
                          content_type='application/json')
    
    json_data = response.get_json()
    assert 'password_hash' not in json_data
    assert 'password' not in json_data


# ======================================================================
# TESTS DE INTEGRACIÓN (Flujo completo)
# ======================================================================

def test_flujo_completo_registro_y_login(client, app):
    """Test de flujo completo: registro → login → verificación datos."""
    # 1. Registro
    data_registro = {
        'nombre': 'Usuario Completo',
        'email': 'completo@test.com',
        'password': 'MiPassword123',
        'rol': 'cliente',
        'foto_perfil': (BytesIO(b'fake image content'), 'avatar.jpg')
    }
    
    reg_response = client.post('/auth/register', data=data_registro, content_type='multipart/form-data')
    assert reg_response.status_code == 201
    
    reg_data = reg_response.get_json()
    user_id = reg_data['id']
    foto_url = reg_data['foto_perfil_url']
    
    # 2. Login
    data_login = {
        'email': 'completo@test.com',
        'password': 'MiPassword123'
    }
    
    login_response = client.post('/auth/login',
                                data=json.dumps(data_login),
                                content_type='application/json')
    assert login_response.status_code == 200
    
    login_data = login_response.get_json()
    
    # 3. Verificar que los datos coinciden
    assert login_data['id'] == user_id
    assert login_data['nombre'] == 'Usuario Completo'
    assert login_data['email'] == 'completo@test.com'
    assert login_data['rol'] == 'cliente'
    assert login_data['foto_perfil_url'] == foto_url


def test_multiples_usuarios_independientes(client, app):
    """Test que múltiples usuarios pueden registrarse y hacer login independientemente."""
    # Registrar 3 usuarios
    usuarios = [
        {'nombre': 'Usuario 1', 'email': 'user1@test.com', 'password': 'pass1', 'rol': 'cliente'},
        {'nombre': 'Usuario 2', 'email': 'user2@test.com', 'password': 'pass2', 'rol': 'propietario'},
        {'nombre': 'Usuario 3', 'email': 'user3@test.com', 'password': 'pass3', 'rol': 'cliente'}
    ]
    
    ids = []
    for user_data in usuarios:
        response = client.post('/auth/register', data=user_data, content_type='multipart/form-data')
        assert response.status_code == 201
        ids.append(response.get_json()['id'])
    
    # Verificar que todos los IDs son diferentes
    assert len(set(ids)) == 3
    
    # Hacer login con cada usuario
    for user_data in usuarios:
        login_data = {
            'email': user_data['email'],
            'password': user_data['password']
        }
        response = client.post('/auth/login',
                              data=json.dumps(login_data),
                              content_type='application/json')
        assert response.status_code == 200
        assert response.get_json()['nombre'] == user_data['nombre']


def test_registro_auto_login(client, app):
    """Test que el registro devuelve datos completos para auto-login."""
    data = {
        'nombre': 'Auto Login Test',
        'email': 'autologin@test.com',
        'password': 'password123',
        'rol': 'cliente'
    }
    
    response = client.post('/auth/register', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    
    json_data = response.get_json()
    
    # Verificar que devuelve todos los datos necesarios para auto-login
    assert 'id' in json_data
    assert 'nombre' in json_data
    assert 'email' in json_data
    assert 'rol' in json_data
    assert 'foto_perfil_url' in json_data
    assert 'message' in json_data
    
    # NO debe incluir password ni password_hash
    assert 'password' not in json_data
    assert 'password_hash' not in json_data
