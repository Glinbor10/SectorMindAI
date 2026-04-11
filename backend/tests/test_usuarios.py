# backend/tests/test_usuarios.py
# filepath: backend/tests/test_usuarios.py
"""Tests para gestión de usuarios (PostgreSQL)."""
import pytest
import json
import uuid
from io import BytesIO


def test_obtener_usuario_existente(client):
    """Test GET /usuarios/{id} devuelve datos del usuario creado."""
    user_email = f'test_{uuid.uuid4().hex[:8]}@example.com'
    user_nombre = 'Usuario Test Único'
    
    reg_response = client.post('/auth/register', data={
        'nombre': user_nombre,
        'email': user_email,
        'password': 'password123',
        'rol': 'cliente'
    }, content_type='multipart/form-data')
    
    assert reg_response.status_code == 201
    user_id = reg_response.get_json()['id']
    
    response = client.get(f'/usuarios/{user_id}')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == user_id
    assert data['nombre'] == user_nombre
    assert data['email'] == user_email
    assert data['rol'] == 'cliente'
    # Puede tener foto_perfil_base64 o no
    assert 'foto_perfil_base64' in data


def test_buscar_usuarios_filtra_por_rol_cliente(app, db_conn, client):
    """GET /usuarios/buscar devuelve solo clientes y filtra por email (case-insensitive)."""
    cursor = db_conn.cursor()

    # Crear un cliente y un propietario
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Cliente Busqueda', 'cliente_buscar@test.com', 'hash', 'cliente')
    )
    cliente_id = cursor.fetchone()['id']

    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s)",
        ('Prop Busqueda', 'prop_buscar@test.com', 'hash', 'propietario')
    )

    db_conn.commit()
    cursor.close()

    # Buscar por "clien" debe devolver solo el cliente, no el propietario
    response = client.get('/usuarios/buscar?q=clien')
    assert response.status_code == 200
    data = response.get_json()
    assert any(u['id'] == cliente_id for u in data)
    assert all(u['email'] != 'prop_buscar@test.com' for u in data)


def test_obtener_usuario_no_encontrado(client):
    response = client.get('/usuarios/999999')
    assert response.status_code == 404
    assert response.get_json()['error'] == 'Usuario no encontrado'


def test_actualizar_usuario_nombre_exitoso(client):
    email = f'update_name_{uuid.uuid4().hex[:8]}@example.com'
    reg = client.post('/auth/register', data={
        'nombre': 'Nombre Original',
        'email': email,
        'password': 'password123',
        'rol': 'cliente'
    }, content_type='multipart/form-data')

    assert reg.status_code == 201
    user_id = reg.get_json()['id']

    response = client.put(
        f'/usuarios/{user_id}',
        data={'nombre': 'Nombre Nuevo'},
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == user_id
    assert data['nombre'] == 'Nombre Nuevo'


def test_actualizar_usuario_foto_valida_exitoso(client):
    email = f'update_photo_{uuid.uuid4().hex[:8]}@example.com'
    reg = client.post('/auth/register', data={
        'nombre': 'Usuario Foto',
        'email': email,
        'password': 'password123',
        'rol': 'cliente'
    }, content_type='multipart/form-data')

    assert reg.status_code == 201
    user_id = reg.get_json()['id']

    file_data = BytesIO(b'fake-image-content')
    response = client.put(
        f'/usuarios/{user_id}',
        data={'foto_perfil': (file_data, 'avatar.png')},
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == user_id
    assert data['foto_perfil_base64'].startswith('data:image/png;base64,')


def test_actualizar_usuario_rechaza_extension_invalida(client):
    email = f'update_invalid_ext_{uuid.uuid4().hex[:8]}@example.com'
    reg = client.post('/auth/register', data={
        'nombre': 'Usuario Extension',
        'email': email,
        'password': 'password123',
        'rol': 'cliente'
    }, content_type='multipart/form-data')

    assert reg.status_code == 201
    user_id = reg.get_json()['id']

    file_data = BytesIO(b'%PDF-1.4 fake')
    response = client.put(
        f'/usuarios/{user_id}',
        data={'foto_perfil': (file_data, 'archivo.pdf')},
        content_type='multipart/form-data'
    )

    assert response.status_code == 400
    assert 'Tipo de archivo no permitido' in response.get_json()['error']


def test_actualizar_usuario_sin_datos(client):
    email = f'update_empty_{uuid.uuid4().hex[:8]}@example.com'
    reg = client.post('/auth/register', data={
        'nombre': 'Usuario Sin Datos',
        'email': email,
        'password': 'password123',
        'rol': 'cliente'
    }, content_type='multipart/form-data')

    assert reg.status_code == 201
    user_id = reg.get_json()['id']

    response = client.put(f'/usuarios/{user_id}', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert response.get_json()['error'] == 'No hay datos para actualizar'


def test_actualizar_usuario_no_encontrado(client):
    response = client.put(
        '/usuarios/999999',
        data={'nombre': 'No Existe'},
        content_type='multipart/form-data'
    )
    assert response.status_code == 404
    assert response.get_json()['error'] == 'Usuario no encontrado'


def test_buscar_usuarios_query_vacia_o_corta_devuelve_lista_vacia(client):
    response_empty = client.get('/usuarios/buscar')
    assert response_empty.status_code == 200
    assert response_empty.get_json() == []

    response_short = client.get('/usuarios/buscar?q=a')
    assert response_short.status_code == 200
    assert response_short.get_json() == []


def test_buscar_usuarios_maneja_error_db(client, monkeypatch):
    from backend.routes import usuarios as usuarios_module

    class FakeConn:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError('db down')

        def close(self):
            return None

    monkeypatch.setattr(usuarios_module, 'get_db_connection', lambda: FakeConn())

    response = client.get('/usuarios/buscar?q=cliente')
    assert response.status_code == 500
    assert 'db down' in response.get_json()['error']