import pytest
import sqlite3
import tempfile
import os
from backend.app import create_app

@pytest.fixture
def app():
    """Crea aplicación Flask con BD temporal para testing."""
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app()
    app.config['TESTING'] = True
    
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
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Cliente de prueba que usa la app con BD temporal."""
    return app.test_client()

def test_home_page(client):
    """Prueba que la página de inicio carga correctamente (código 200)"""
    response = client.get('/')
    assert response.status_code == 200

def test_negocios_endpoint(client):
    """Prueba que el endpoint de negocios devuelve JSON vacío con BD limpia"""
    response = client.get('/negocios/')
    assert response.status_code == 200
    assert response.get_json() == []