"""
Script para convertir todas las queries SQL de SQLite a PostgreSQL-compatible
Busca y reemplaza ? por %s en queries, añadiendo RETURNING id donde sea necesario
"""
import re
from pathlib import Path

ROUTES_DIR = Path(__file__).parent.parent / 'routes'

def convert_query(query_str):
    """Convierte query de SQLite a compatible con ambas BD."""
    # Reemplazar ? por %s
    return query_str.replace('?', '%s')

def fix_insert_returning(content):
    """Añade RETURNING id a INSERTs que necesitan obtener el ID."""
    # Patrón para INSERTS que necesitan RETURNING
    pattern = r"(INSERT INTO \w+ \([^)]+\) VALUES \([%s, ]+\))"
    
    def add_returning(match):
        query = match.group(1)
        if 'RETURNING' not in query:
            return query + ' RETURNING id'
        return query
    
    return re.sub(pattern, add_returning, content)

if __name__ == '__main__':
    print("🔧 Convirtiendo queries SQL...")
    
    for route_file in ROUTES_DIR.glob('*.py'):
        if route_file.name.startswith('__'):
            continue
        
        print(f"  📝 Procesando {route_file.name}")
        
        content = route_file.read_text(encoding='utf-8')
        
        # Reemplazar ? por %s
        if '?' in content:
            content = content.replace("'?'", "'%s'")  # Proteger strings con '?'
            content = content.replace('?', '%s')
            
            route_file.write_text(content, encoding='utf-8')
            print(f"    ✅ Convertido")
        else:
            print(f"    ⏭️  Ya convertido")
    
    print("\n✨ Conversión completada")
