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