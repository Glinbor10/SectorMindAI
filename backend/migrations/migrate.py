"""
Sistema de migraciones para SectorMindAI - PostgreSQL EXCLUSIVAMENTE
SQLite ha sido eliminado del proyecto.
"""
import os
import sys
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def get_applied_migrations(conn):
    """Obtiene lista de migraciones ya aplicadas (PostgreSQL)."""
    cursor = conn.cursor()
    
    # Crear tabla de control si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            version VARCHAR(255) UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
    rows = cursor.fetchall()
    return [row['version'] for row in rows]

def apply_migration(conn, version, sql):
    """Aplica una migración y registra su aplicación."""
    cursor = conn.cursor()
    
    print(f"  ⏳ Aplicando migración {version}...")
    
    # Ejecutar SQL de migración, filtrando statements vacíos y comentarios
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
    for statement in statements:
        cursor.execute(statement)
    
    # Registrar migración aplicada (PostgreSQL EXCLUSIVAMENTE)
    cursor.execute(
        "INSERT INTO schema_migrations (version) VALUES (%s)",
        (version,)
    )
    
    conn.commit()
    print(f"  ✅ Migración {version} aplicada correctamente")

def run_migrations():
    """Ejecuta todas las migraciones pendientes (PostgreSQL)."""
    migrations_dir = Path(__file__).parent
    conn = get_db_connection()
    
    print(f"\n🔄 Sistema de migraciones - PostgreSQL")
    print("=" * 60)
    
    try:
        # Obtener migraciones aplicadas
        applied = get_applied_migrations(conn)
        print(f"📋 Migraciones aplicadas: {len(applied)}")
        
        # Buscar archivos de migración
        migration_files = sorted([
            f for f in migrations_dir.glob('*.sql')
            if f.name != '__init__.py'
        ])
        
        pending = [f for f in migration_files if f.stem not in applied]
        
        if not pending:
            print("✅ No hay migraciones pendientes")
            return
        
        print(f"🆕 Migraciones pendientes: {len(pending)}\n")
        
        # Aplicar cada migración pendiente
        for migration_file in pending:
            version = migration_file.stem
            sql = migration_file.read_text(encoding='utf-8')
            
            apply_migration(conn, version, sql)
        
        print(f"\n✨ ¡Migraciones completadas exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error durante migración: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    run_migrations()
