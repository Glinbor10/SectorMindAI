# backend/manage_db.py
# filepath: backend/manage_db.py
"""
Script maestro para gestión de bases de datos PostgreSQL en Docker.

Ahora existen dos bases de datos independientes:
    - sectormind_db: base de datos principal (desarrollo/producción)
    - sectormind_test_db: base de datos exclusiva para tests

Ambas comparten exactamente la misma estructura y esquema, pero sus datos pueden ser distintos. Esto permite ejecutar tests sin afectar los datos reales.
"""
import psycopg2
import psycopg2.extras
import os
import shutil
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))



# Permite sobreescribir la base de datos por variable de entorno o argumento
import sys
DATABASE_URL = os.getenv('DATABASE_URL')
if len(sys.argv) > 1 and sys.argv[1].startswith('postgresql'):
    DATABASE_URL = sys.argv[1]
if not DATABASE_URL:
    raise ValueError("❌ ERROR: No se ha definido ninguna DATABASE_URL.\n\nPuedes usar:\n  - La variable de entorno DATABASE_URL para la base de datos principal (sectormind_db)\n  - O pasar la URL de la base de datos de tests (sectormind_test_db) como argumento al script.\n\nAmbas bases de datos tienen la misma estructura, pero datos independientes.")

API_URL = os.getenv('API_URL_INTERNAL', 'http://127.0.0.1:5000')




# --- FUNCIONES AUXILIARES ---

def load_sample_photo_base64(filename):
    """Carga una imagen de sample_photos y la devuelve como base64 data URL."""
    import base64
    path = os.path.join(BASE_DIR, 'sample_photos', filename)
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        data = f.read()
        ext = filename.split('.')[-1].lower()
        mime = 'image/png' if ext == 'png' else 'image/jpeg'
        return f"data:{mime};base64," + base64.b64encode(data).decode('utf-8')
PROPIETARIO_DATA = {
    "nombre": "Pedro Propietario",
    "email": "propietario@sectormind.com",
    "password": "p",
    "rol": "propietario",
    "foto_perfil_url": "https://images.unsplash.com/photo-1560250097-0b93528c311a?ixlib=rb-1.2.1&auto=format&fit=crop&w=256&q=80",
    "foto_perfil_base64": load_sample_photo_base64('propietario.jpg')
}


CLIENTE_DATA = {
    "nombre": "Ursula Usuario",
    "email": "cliente@sectormind.com",
    "password": "c",
    "rol": "cliente",
    "foto_perfil_url": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?ixlib=rb-1.2.1&auto=format&fit=crop&w=256&q=80",
    "foto_perfil_base64": load_sample_photo_base64('cliente.png')
}

HORARIO_PARTIDO = []
for dia in range(5):
    HORARIO_PARTIDO.extend([
        {"dia_semana": dia, "hora_apertura": "09:30:00", "hora_cierre": "13:30:00"},
        {"dia_semana": dia, "hora_apertura": "16:30:00", "hora_cierre": "20:00:00"}
    ])



NEGOCIOS = [
    {
        "nombre": "Peluquería Estilo & Glamour",
        "tipo_negocio": "peluqueria",
        "direccion": "Av. de la Moda, 45, Madrid",
        "descripcion": "Especialistas en cambios de imagen radicales.",
        "foto_base64": load_sample_photo_base64('peluqueria.jpeg'),
        "horarios": HORARIO_PARTIDO,
        "servicios": [
            {"nombre": "Corte de Pelo", "precio": 25.00, "duracion_minutos": 30},
            {"nombre": "Tinte", "precio": 60.00, "duracion_minutos": 90}
        ]
    },
    {
        "nombre": "Clínica Dental Smile",
        "tipo_negocio": "dentista",
        "direccion": "Calle de la Salud, 12, Barcelona",
        "descripcion": "Cuidamos tu sonrisa con tecnología moderna.",
        "foto_base64": load_sample_photo_base64('dentista.png'),
        "horarios": HORARIO_PARTIDO,
        "servicios": [
            {"nombre": "Limpieza", "precio": 50.00, "duracion_minutos": 30},
            {"nombre": "Endodoncia", "precio": 200.00, "duracion_minutos": 60}
        ]
    },
    {
        "nombre": "FisioMente Centro",
        "tipo_negocio": "fisioterapia",
        "direccion": "Plaza del Deporte, s/n",
        "descripcion": "Recupérate de tus lesiones con expertos.",
        "foto_base64": load_sample_photo_base64('fisioterapia.jpg'),
        "horarios": HORARIO_PARTIDO,
        "servicios": [
            {"nombre": "Masaje deportivo", "precio": 40.00, "duracion_minutos": 45},
            {"nombre": "Punción seca", "precio": 45.00, "duracion_minutos": 30}
        ]
    }
]





def init_db():
    """🗄️ Reinicializa la BD PostgreSQL."""
    print(f"\n2️⃣  REINICIALIZANDO BASE DE DATOS POSTGRESQL...")
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        cursor = conn.cursor()
        
        # 🚨 PELIGROSO: Elimina todas las tablas (solo en desarrollo)
        print("    ⚠️ Eliminando todas las tablas...")
        cursor.execute("""
            DROP TABLE IF EXISTS citas CASCADE;
            DROP TABLE IF EXISTS servicios CASCADE;
            DROP TABLE IF EXISTS horarios_negocio CASCADE;
            DROP TABLE IF EXISTS negocios CASCADE;
            DROP TABLE IF EXISTS usuarios CASCADE;
        """)
        conn.commit()
        print("    ✅ Tablas eliminadas.")
        
        # Crear schema desde archivo
        schema_path = os.path.join(BASE_DIR, '..', 'database', 'schema_postgres.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        cursor.execute(schema_sql)
        conn.commit()
        print("    ✅ Esquema PostgreSQL aplicado.")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"    ❌ ERROR AL INICIALIZAR BD: {e}")
        return False


def populate_db():
    """👥 Puebla datos de prueba directamente en BD."""
    print(f"\n3️⃣  POBLANDO DATOS DIRECTAMENTE EN BD...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        cursor = conn.cursor()
        
        # --- CREAR PROPIETARIO ---
        print(f"    👤 Insertando Propietario...")
        hashed_prop_password = generate_password_hash(PROPIETARIO_DATA['password'])
        cursor.execute(
            "INSERT INTO usuarios (nombre, email, password_hash, rol, foto_perfil_url, foto_perfil_base64) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (PROPIETARIO_DATA['nombre'], PROPIETARIO_DATA['email'], hashed_prop_password, PROPIETARIO_DATA['rol'], PROPIETARIO_DATA['foto_perfil_url'], PROPIETARIO_DATA['foto_perfil_base64'])
        )
        prop_id = cursor.fetchone()['id']
        print(f"       ✅ {PROPIETARIO_DATA['nombre']} (ID: {prop_id})")
        
        # --- CREAR CLIENTE ---
        print(f"    👤 Insertando Cliente...")
        hashed_client_password = generate_password_hash(CLIENTE_DATA['password'])
        cursor.execute(
            "INSERT INTO usuarios (nombre, email, password_hash, rol, foto_perfil_url, foto_perfil_base64) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (CLIENTE_DATA['nombre'], CLIENTE_DATA['email'], hashed_client_password, CLIENTE_DATA['rol'], CLIENTE_DATA['foto_perfil_url'], CLIENTE_DATA['foto_perfil_base64'])
        )
        client_id = cursor.fetchone()['id']
        print(f"       ✅ {CLIENTE_DATA['nombre']} (ID: {client_id})")
        
        # --- CREAR NEGOCIOS ---
        print("    🏢 Insertando Negocios...")
        created_negocios = []
        
        for negocio in NEGOCIOS:
            cursor.execute(
                "INSERT INTO negocios (nombre, tipo_negocio, direccion, descripcion, foto_base64, propietario_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (negocio["nombre"], negocio["tipo_negocio"], negocio["direccion"], negocio.get("descripcion"), negocio.get("foto_base64"), prop_id)
            )
            new_id = cursor.fetchone()['id']
            created_negocios.append({"id": new_id, **negocio})
            print(f"       ✅ {negocio['nombre']} (ID: {new_id})")
        
        # --- INSERTAR HORARIOS Y SERVICIOS ---
        if created_negocios:
            print("    ⏰ Insertando horarios y servicios...")
            for negocio in created_negocios:
                neg_id = negocio["id"]
                
                # Insertar horarios
                for h in negocio.get("horarios", []):
                    cursor.execute(
                        "INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (%s, %s, %s, %s)",
                        (neg_id, h["dia_semana"], h["hora_apertura"], h["hora_cierre"])
                    )
                
                # Insertar servicios
                for s in negocio.get("servicios", []):
                    cursor.execute(
                        "INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s)",
                        (neg_id, s["nombre"], s["precio"], s["duracion_minutos"])
                    )
            
            print("       ✅ Horarios y servicios insertados.")
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"    ❌ ERROR: {e}")


def add_past_citas():
    """📅 Añade citas pasadas al cliente de prueba."""
    print(f"\n4️⃣  AÑADIENDO CITAS PASADAS...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        cursor = conn.cursor()
        
        # Obtener ID del cliente
        cursor.execute("SELECT id FROM usuarios WHERE nombre = 'Ursula Usuario'")
        result = cursor.fetchone()
        
        if not result:
            print("    ⚠️ Usuario 'Ursula Usuario' no encontrado")
            conn.close()
            return
        
        cliente_id = result['id']
        
        # Obtener primer negocio y 2 servicios
        cursor.execute("SELECT id FROM negocios LIMIT 1")
        result = cursor.fetchone()
        if not result:
            print("    ⚠️ No hay negocios disponibles")
            conn.close()
            return
        
        negocio_id = result['id']
        
        cursor.execute("SELECT id, duracion_minutos FROM servicios LIMIT 2")
        servicios = cursor.fetchall()
        
        if len(servicios) < 2:
            print("    ⚠️ Se necesitan al menos 2 servicios")
            conn.close()
            return
        
        # Crear 2 citas pasadas
        fecha_pasada_1 = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d 10:00:00')
        fecha_pasada_2 = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d 14:30:00')
        
        cursor.execute(
            "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (%s, %s, %s, %s, %s, %s)",
            (negocio_id, cliente_id, servicios[0]['id'], fecha_pasada_1, servicios[0]['duracion_minutos'], 'confirmada')
        )
        
        cursor.execute(
            "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (%s, %s, %s, %s, %s, %s)",
            (negocio_id, cliente_id, servicios[1]['id'], fecha_pasada_2, servicios[1]['duracion_minutos'], 'confirmada')
        )
        
        conn.commit()
        print(f"    ✅ 2 citas pasadas añadidas a Úrsula")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"    ❌ ERROR: {e}")


def main():
    """🚀 Ejecuta el pipeline completo."""
    print("=" * 60)
    print("🐘 GESTOR DE BASE DE DATOS - POSTGRESQL EXCLUSIVAMENTE")
    print("=" * 60)
    

    if init_db():
        populate_db()
        add_past_citas()
        print("\n✨ ¡SISTEMA RESTAURADO COMPLETAMENTE! ✨")
        print(f"   → Propietario: {PROPIETARIO_DATA['email']}")
        print(f"   → Cliente:     {CLIENTE_DATA['email']}")
    else:
        print("\n❌ No se pudo inicializar la base de datos.")


if __name__ == '__main__':
    main()