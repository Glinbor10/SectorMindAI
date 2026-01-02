# backend/tests/test_basic.py
# filepath: backend/tests/test_basic.py
"""Tests básicos de endpoints (PostgreSQL)."""
import pytest


def test_home_page(client):
    """Prueba que la página de inicio carga correctamente."""
    response = client.get('/')
    assert response.status_code == 200


def test_negocios_endpoint(client):
    """Prueba que el endpoint de negocios devuelve JSON."""
    response = client.get('/negocios/')
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)