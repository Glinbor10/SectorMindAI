# backend/db.py
# filepath: backend/db.py
import os
from flask import g
from dotenv import load_dotenv

load_dotenv()

# 🔧 POSTGRESQL EXCLUSIVAMENTE
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

DATABASE_URL = os.getenv('DATABASE_URL')
DATABASE_POOL_MIN = int(os.getenv('DATABASE_POOL_MIN', '4'))
DATABASE_POOL_MAX = int(os.getenv('DATABASE_POOL_MAX', '80'))

if not DATABASE_URL:
    raise ValueError("❌ ERROR CRÍTICO: DATABASE_URL no está definida en .env")

print(f"🐘 Conectando a PostgreSQL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'BD configurada'}")

_db_pool = ThreadedConnectionPool(
    minconn=DATABASE_POOL_MIN,
    maxconn=DATABASE_POOL_MAX,
    dsn=DATABASE_URL,
    cursor_factory=psycopg2.extras.RealDictCursor,
)


class PostgresConnectionWrapper:
    """Wrapper para que psycopg2 connection se comporte como sqlite3 con .execute()"""
    def __init__(self, conn, from_pool=False):
        self._conn = conn
        self._from_pool = from_pool
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
        if self._conn is None:
            return None
        if self._from_pool:
            _db_pool.putconn(self._conn)
        else:
            self._conn.close()
        self._conn = None
        return None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self.close()


def get_db():
    """Abre una nueva conexión a PostgreSQL en Flask request context."""
    if 'db' not in g:
        raw_conn = _db_pool.getconn()
        raw_conn.autocommit = False
        g.db = PostgresConnectionWrapper(raw_conn, from_pool=True)
    return g.db


def close_db(e=None):
    """Cierra la conexión a la base de datos."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_db_connection():
    """Obtiene una nueva conexión independiente (fuera de Flask request context)."""
    raw_conn = _db_pool.getconn()
    raw_conn.autocommit = False
    return PostgresConnectionWrapper(raw_conn, from_pool=True)


def init_app(app):
    """Registra el cierre automático de conexiones en Flask."""
    app.teardown_appcontext(close_db)