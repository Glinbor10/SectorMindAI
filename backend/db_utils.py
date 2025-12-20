"""
Utilidades para PostgreSQL exclusivamente.
SQLite ha sido eliminado del proyecto.
"""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def adapt_query(query):
    """
    Adaptador para compatibilidad con PostgreSQL.
    En PostgreSQL, los placeholders son %s (nunca ?).
    """
    # Si por alguna razón viene con ?, reemplazar por %s
    return query.replace('?', '%s')
    return query
