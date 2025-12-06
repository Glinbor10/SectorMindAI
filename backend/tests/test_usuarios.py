"""
Tests para backend/routes/usuarios.py
Valida los endpoints de gestión de perfiles de usuario.
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
        
        # Datos de prueba
        conn.execute("INSERT INTO usuarios (id, nombre, email, password_hash, rol, foto_perfil_url) VALUES (1, 'Usuario Test', 'user@test.com', 'scrypt:hash123', 'cliente', '/uploads/foto_antigua.jpg')")
        conn.execute("INSERT INTO usuarios (id, nombre, email, password_hash, rol) VALUES (2, 'Usuario Sin Foto', 'sin_foto@test.com', 'scrypt:hash456', 'cliente')")
        
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


# ======================================================================
# TESTS PARA GET /usuarios/<id> (Obtener usuario)
# ======================================================================

def test_obtener_usuario_existente(client, db_conn):
    """Test GET /usuarios/1 devuelve datos del usuario."""
    response = client.get('/usuarios/1')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == 1
    assert data['nombre'] == 'Usuario Test'
    assert data['email'] == 'user@test.com'
    assert data['rol'] == 'cliente'
    assert data['foto_perfil_url'] == '/uploads/foto_antigua.jpg'


def test_obtener_usuario_no_expone_password(client, db_conn):
    """Test GET /usuarios/1 NO devuelve password_hash."""
    response = client.get('/usuarios/1')
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'password_hash' not in data
    assert 'password' not in data


def test_obtener_usuario_sin_foto(client, db_conn):
    """Test GET /usuarios/2 con usuario sin foto_perfil_url."""
    response = client.get('/usuarios/2')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == 2
    assert data['nombre'] == 'Usuario Sin Foto'
    assert data['foto_perfil_url'] is None or data['foto_perfil_url'] == ''


def test_obtener_usuario_inexistente(client, db_conn):
    """Test GET /usuarios/999 con ID inexistente devuelve 404."""
    response = client.get('/usuarios/999')
    
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert 'no encontrado' in data['error'].lower()


# ======================================================================
# TESTS PARA PUT /usuarios/<id> (Actualizar usuario)
# ======================================================================

def test_actualizar_usuario_solo_nombre(client, app):
    """Test PUT /usuarios/1 actualiza solo el nombre."""
    payload = {
        'nombre': 'Nombre Actualizado'
    }
    
    response = client.put('/usuarios/1',
                         data=payload,
                         content_type='multipart/form-data')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['nombre'] == 'Nombre Actualizado'
    
    # Verificar en BD
    with app.app_context():
        from backend.db import get_db
        conn = get_db()
        usuario = conn.execute('SELECT nombre FROM usuarios WHERE id = 1').fetchone()
        assert usuario['nombre'] == 'Nombre Actualizado'


def test_actualizar_usuario_solo_foto(client, app):
    """Test PUT /usuarios/1 actualiza solo la foto_perfil."""
    fake_file = (BytesIO(b'fake image content'), 'test_foto.jpg')
    
    response = client.put('/usuarios/1',
                         data={'foto_perfil': fake_file},
                         content_type='multipart/form-data')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['foto_perfil_url'] is not None
    assert 'user_1_' in data['foto_perfil_url']  # UUID naming
    assert '.jpg' in data['foto_perfil_url']


def test_actualizar_usuario_nombre_y_foto(client, app):
    """Test PUT /usuarios/1 actualiza nombre y foto juntos."""
    fake_file = (BytesIO(b'fake image content'), 'nueva_foto.png')
    payload = {
        'nombre': 'Nombre y Foto',
        'foto_perfil': fake_file
    }
    
    response = client.put('/usuarios/1',
                         data=payload,
                         content_type='multipart/form-data')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['nombre'] == 'Nombre y Foto'
    assert data['foto_perfil_url'] is not None
    assert '.png' in data['foto_perfil_url']


def test_actualizar_usuario_sin_datos(client, db_conn):
    """Test PUT /usuarios/1 sin datos devuelve 400."""
    response = client.put('/usuarios/1',
                         data={},
                         content_type='multipart/form-data')
    
    assert response.status_code == 400
    assert 'No hay datos para actualizar' in response.get_json()['error']


def test_actualizar_usuario_foto_extension_invalida(client, db_conn):
    """Test PUT /usuarios/1 con extensión inválida devuelve 400."""
    fake_file = (BytesIO(b'fake content'), 'test.exe')
    
    response = client.put('/usuarios/1',
                         data={'foto_perfil': fake_file},
                         content_type='multipart/form-data')
    
    assert response.status_code == 400
    assert 'Tipo de archivo no permitido' in response.get_json()['error']


def test_actualizar_usuario_inexistente(client, db_conn):
    """Test PUT /usuarios/999 con ID inexistente devuelve 404."""
    payload = {
        'nombre': 'Test'
    }
    
    response = client.put('/usuarios/999',
                         data=payload,
                         content_type='multipart/form-data')
    
    assert response.status_code == 404


# ======================================================================
# TESTS DE VALIDACIÓN DE ARCHIVOS
# ======================================================================

def test_upload_foto_extension_png(client, app):
    """Test PUT /usuarios/1 acepta extensión .png."""
    fake_file = (BytesIO(b'fake png content'), 'test.png')
    
    response = client.put('/usuarios/1',
                         data={'foto_perfil': fake_file},
                         content_type='multipart/form-data')
    
    assert response.status_code == 200
    assert '.png' in response.get_json()['foto_perfil_url']


def test_upload_foto_extension_jpg(client, app):
    """Test PUT /usuarios/1 acepta extensión .jpg."""
    fake_file = (BytesIO(b'fake jpg content'), 'test.jpg')
    
    response = client.put('/usuarios/1',
                         data={'foto_perfil': fake_file},
                         content_type='multipart/form-data')
    
    assert response.status_code == 200
    assert '.jpg' in response.get_json()['foto_perfil_url']


def test_upload_foto_extension_jpeg(client, app):
    """Test PUT /usuarios/1 acepta extensión .jpeg."""
    fake_file = (BytesIO(b'fake jpeg content'), 'test.jpeg')
    
    response = client.put('/usuarios/1',
                         data={'foto_perfil': fake_file},
                         content_type='multipart/form-data')
    
    assert response.status_code == 200
    assert '.jpeg' in response.get_json()['foto_perfil_url']


def test_upload_foto_extension_gif(client, app):
    """Test PUT /usuarios/1 acepta extensión .gif."""
    fake_file = (BytesIO(b'fake gif content'), 'test.gif')
    
    response = client.put('/usuarios/1',
                         data={'foto_perfil': fake_file},
                         content_type='multipart/form-data')
    
    assert response.status_code == 200
    assert '.gif' in response.get_json()['foto_perfil_url']


def test_upload_foto_nombre_uuid_correcto(client, app):
    """Test PUT /usuarios/1 genera nombre con formato user_{id}_{uuid}.{ext}."""
    fake_file = (BytesIO(b'fake content'), 'original_name.jpg')
    
    response = client.put('/usuarios/1',
                         data={'foto_perfil': fake_file},
                         content_type='multipart/form-data')
    
    assert response.status_code == 200
    foto_path = response.get_json()['foto_perfil_url']
    
    # Verificar formato: user_1_{uuid}.jpg
    assert 'user_1_' in foto_path
    assert '.jpg' in foto_path
    assert 'original_name' not in foto_path  # No debe usar nombre original


def test_upload_foto_sin_extension(client, db_conn):
    """Test PUT /usuarios/1 con archivo sin extensión devuelve 400."""
    fake_file = (BytesIO(b'fake content'), 'archivo_sin_extension')
    
    response = client.put('/usuarios/1',
                         data={'foto_perfil': fake_file},
                         content_type='multipart/form-data')
    
    assert response.status_code == 400


# ======================================================================
# TESTS DE INTEGRACIÓN
# ======================================================================

def test_flujo_completo_consultar_y_actualizar(client, app):
    """Test de flujo completo: consultar → actualizar → verificar cambios."""
    # 1. Consultar usuario inicial
    response = client.get('/usuarios/1')
    assert response.status_code == 200
    data_inicial = response.get_json()
    assert data_inicial['nombre'] == 'Usuario Test'
    
    # 2. Actualizar nombre y foto
    fake_file = (BytesIO(b'nueva imagen'), 'nueva.png')
    payload = {
        'nombre': 'Nombre Modificado',
        'foto_perfil': fake_file
    }
    response = client.put('/usuarios/1',
                         data=payload,
                         content_type='multipart/form-data')
    assert response.status_code == 200
    
    # 3. Consultar de nuevo y verificar cambios
    response = client.get('/usuarios/1')
    data_final = response.get_json()
    assert data_final['nombre'] == 'Nombre Modificado'
    assert data_final['foto_perfil_url'] != data_inicial['foto_perfil_url']
    assert 'user_1_' in data_final['foto_perfil_url']
    assert '.png' in data_final['foto_perfil_url']


def test_multiples_actualizaciones_foto(client, app):
    """Test que múltiples actualizaciones de foto funcionan correctamente."""
    fotos = [
        (BytesIO(b'foto 1'), 'foto1.jpg'),
        (BytesIO(b'foto 2'), 'foto2.png'),
        (BytesIO(b'foto 3'), 'foto3.jpeg')
    ]
    
    rutas_fotos = []
    for foto in fotos:
        response = client.put('/usuarios/1',
                             data={'foto_perfil': foto},
                             content_type='multipart/form-data')
        assert response.status_code == 200
        rutas_fotos.append(response.get_json()['foto_perfil_url'])
    
    # Verificar que se generaron diferentes UUIDs
    assert len(set(rutas_fotos)) == 3  # Todas diferentes


def test_usuario_sin_foto_puede_agregar_foto(client, app):
    """Test que usuario sin foto_perfil_url puede agregar una."""
    # Usuario 2 no tiene foto_perfil inicial
    response = client.get('/usuarios/2')
    assert response.status_code == 200
    assert response.get_json()['foto_perfil_url'] is None or response.get_json()['foto_perfil_url'] == ''
    
    # Agregar foto
    fake_file = (BytesIO(b'primera foto'), 'primera.jpg')
    response = client.put('/usuarios/2',
                         data={'foto_perfil': fake_file},
                         content_type='multipart/form-data')
    
    assert response.status_code == 200
    assert response.get_json()['foto_perfil_url'] is not None
    
    # Verificar que se guardó
    response = client.get('/usuarios/2')
    assert response.get_json()['foto_perfil_url'] is not None
    assert 'user_2_' in response.get_json()['foto_perfil_url']


