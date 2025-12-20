"""
Script de migración de datos de SQLite a PostgreSQL
Migra todos los datos existentes preservando IDs y relaciones
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

SQLITE_DB = Path(__file__).parent.parent.parent / 'database' / 'tfg_data.db'
POSTGRES_URL = os.getenv('DATABASE_URL')

def migrate_data():
    """Migra todos los datos de SQLite a PostgreSQL."""
    
    if not SQLITE_DB.exists():
        print(f"❌ Base de datos SQLite no encontrada: {SQLITE_DB}")
        return
    
    if not POSTGRES_URL:
        print("❌ DATABASE_URL no configurada en .env")
        return
    
    print("\n🔄 MIGRACIÓN DE DATOS: SQLite → PostgreSQL")
    print("=" * 60)
    
    # Conectar a ambas bases de datos
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    
    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Orden de migración (respetando foreign keys)
        tables = [
            'usuarios',
            'negocios',
            'servicios',
            'horarios_negocio',
            'citas'
        ]
        
        for table in tables:
            print(f"\n📋 Migrando tabla: {table}")
            
            # Leer datos de SQLite
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute(f"SELECT * FROM {table}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"  ⚠️  Tabla {table} vacía, omitiendo...")
                continue
            
            print(f"  📊 {len(rows)} registros encontrados")
            
            # Obtener nombres de columnas
            columns = [description[0] for description in sqlite_cursor.description]
            
            # Preparar INSERT para PostgreSQL
            placeholders = ', '.join(['%s'] * len(columns))
            columns_str = ', '.join(columns)
            
            insert_sql = f"""
                INSERT INTO {table} ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            
            # Insertar cada fila
            migrated = 0
            for row in rows:
                try:
                    pg_cursor.execute(insert_sql, tuple(row))
                    migrated += 1
                except Exception as e:
                    print(f"  ⚠️  Error en registro {dict(row)}: {e}")
            
            pg_conn.commit()
            print(f"  ✅ {migrated} registros migrados")
            
            # Actualizar secuencias de PostgreSQL
            pg_cursor.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 1),
                    true
                )
            """)
            pg_conn.commit()
        
        print("\n✨ ¡Migración completada exitosamente!")
        print("\n📊 RESUMEN:")
        
        for table in tables:
            pg_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = pg_cursor.fetchone()['count']
            print(f"  • {table}: {count} registros")
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    print("\n⚠️  ADVERTENCIA: Esta operación copiará todos los datos a PostgreSQL")
    response = input("¿Continuar? (s/N): ")
    
    if response.lower() == 's':
        migrate_data()
    else:
        print("❌ Migración cancelada")
