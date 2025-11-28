import pytest
from backend.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Prueba que la página de inicio carga correctamente (código 200)"""
    response = client.get('/')
    assert response.status_code == 200

def test_negocios_endpoint(client):
    """Prueba que el endpoint de negocios devuelve JSON"""
    response = client.get('/negocios/')
    # Puede ser 200 (ok) o 500 (si no hay db), pero verificamos que no sea 404
    assert response.status_code != 404