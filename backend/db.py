import sqlite3
import os

# La ruta se calcula desde la ubicación de este archivo (backend/)
DATABASE = os.path.join(os.path.dirname(__file__), '..', 'database', 'tfg_data.db')

def get_db_connection():
    """Establece y devuelve una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # Permite acceder a las columnas por nombre
    return conn

# Este archivo indica que 'backend' es un paquete Python
# (Nota: No es necesario incluir el contenido de __init__.py aquí, 
# pero la refactorización asume que el paquete está configurado.)