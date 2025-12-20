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