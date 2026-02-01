# backend/tests/conftest.py
# filepath: backend/tests/conftest.py
"""
Fixtures compartidas para todos los tests (PostgreSQL exclusivamente).
"""
import pytest
import os
import tempfile
import shutil
from dotenv import load_dotenv
from backend.app import create_app
from backend.db import get_db_connection

load_dotenv()


@pytest.fixture(scope="function")
def app():
    """Crea aplicación Flask con carpeta de uploads temporal."""
    upload_dir = tempfile.mkdtemp()
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = upload_dir
    
    yield app
    
    # Cleanup
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)


@pytest.fixture(scope="function")
def client(app):
    """Cliente de prueba Flask."""
    return app.test_client()


@pytest.fixture(scope="function")
def db_conn(app):
    """Conexión a PostgreSQL para tests (usa BD de test en Docker)."""
    with app.app_context():
        # Conectar a la BD de tests
        conn = get_db_connection()
        
        # Limpiar tablas antes del test (sin DROP, solo DELETE para preservar schema)
        cursor = conn.cursor()
        try:
            cursor.execute("TRUNCATE TABLE citas, servicios, horarios_negocio, negocios, usuarios CASCADE")
            conn.commit()
        except Exception as e:
            print(f"⚠️ Warning al limpiar tablas: {e}")
            conn.rollback()
        
        yield conn
        
        # Cleanup después del test
        try:
            cursor.execute("TRUNCATE TABLE citas, servicios, horarios_negocio, negocios, usuarios CASCADE")
            conn.commit()
        except Exception as e:
            print(f"⚠️ Warning al limpiar tablas post-test: {e}")
            conn.rollback()
        
        cursor.close()
        conn.close()


@pytest.fixture(scope="function")
def logic_test_data(app, db_conn):
    """Fixture que prepara datos para tests de lógica (negocio, servicios, horarios)."""
    cursor = db_conn.cursor()
    
    # Crear usuario propietario
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Owner Test', 'owner@test.com', 'hash', 'propietario')
    )
    owner_id = cursor.fetchone()['id']
    
    # Crear usuario cliente (para citas de prueba)
    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Cliente Test', 'cliente@test.com', 'hash', 'cliente')
    )
    cliente_id = cursor.fetchone()['id']
    
    # Crear negocio
    cursor.execute(
        "INSERT INTO negocios (nombre, tipo_negocio, propietario_id, direccion) VALUES (%s, %s, %s, %s) RETURNING id",
        ('Test Peluqueria', 'peluqueria', owner_id, 'Calle Test 123')
    )
    negocio_id = cursor.fetchone()['id']
    
    # Crear servicios
    cursor.execute(
        "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s) RETURNING id",
        (negocio_id, 'Corte', 25.00, 30)
    )
    servicio_id_1 = cursor.fetchone()['id']
    
    cursor.execute(
        "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s) RETURNING id",
        (negocio_id, 'Tinte', 60.00, 90)
    )
    servicio_id_2 = cursor.fetchone()['id']
    
    # Crear horarios (Lunes-Viernes)
    for dia in range(5):
        cursor.execute(
            "INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (%s, %s, %s, %s)",
            (negocio_id, dia, '09:00:00', '13:00:00')
        )
        cursor.execute(
            "INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (%s, %s, %s, %s)",
            (negocio_id, dia, '16:00:00', '20:00:00')
        )
    
    db_conn.commit()
    
    return {
        'negocio_id': negocio_id,
        'servicio_id_1': servicio_id_1,
        'servicio_id_2': servicio_id_2,
        'owner_id': owner_id,
        'cliente_id': cliente_id
    }