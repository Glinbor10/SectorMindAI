# backend/db.py
# filepath: backend/db.py
import os
from flask import g
from dotenv import load_dotenv

load_dotenv()

# 🔧 POSTGRESQL EXCLUSIVAMENTE
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("❌ ERROR CRÍTICO: DATABASE_URL no está definida en .env")

print(f"🐘 Conectando a PostgreSQL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'BD configurada'}")


class PostgresConnectionWrapper:
    """Wrapper para que psycopg2 connection se comporte como sqlite3 con .execute()"""
    def __init__(self, conn):
        self._conn = conn
        self._cursor = None
    
    def execute(self, query, params=None):
        """Ejecuta query y devuelve cursor compatible"""
        self._cursor = self._conn.cursor()
        if params:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)
        return self._cursor
    
    def cursor(self):
        return self._conn.cursor()
    
    def commit(self):
        return self._conn.commit()
    
    def rollback(self):
        return self._conn.rollback()
    
    def close(self):
        return self._conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self._conn.close()


def get_db():
    """Abre una nueva conexión a PostgreSQL en Flask request context."""
    if 'db' not in g:
        raw_conn = psycopg2.connect(
            DATABASE_URL, 
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        raw_conn.autocommit = False
        g.db = PostgresConnectionWrapper(raw_conn)
    return g.db


def close_db(e=None):
    """Cierra la conexión a la base de datos."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_db_connection():
    """Obtiene una nueva conexión independiente (fuera de Flask request context)."""
    raw_conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    return PostgresConnectionWrapper(raw_conn)


def init_app(app):
    """Registra el cierre automático de conexiones en Flask."""
    app.teardown_appcontext(close_db)