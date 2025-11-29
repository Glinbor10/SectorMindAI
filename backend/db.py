import sqlite3
import os
from flask import g

# Ruta absoluta a la base de datos
DATABASE = os.path.join(os.path.dirname(__file__), '..', 'database', 'tfg_data.db')

def get_db():
    """Abre una nueva conexión a la base de datos si no existe una en la petición actual."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row # Permite acceder a columnas por nombre
    return g.db

def close_db(e=None):
    """Cierra la conexión a la base de datos si existe."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Esta función permite a otros archivos seguir usando "get_db_connection" si prefieres no cambiar el nombre,
# pero internamente usa la gestión segura 'get_db'
def get_db_connection():
    return get_db()

# Función para registrar el cierre automático en la app
def init_app(app):
    app.teardown_appcontext(close_db)