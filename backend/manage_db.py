# backend/manage_db.py
# filepath: backend/manage_db.py
"""
Script maestro para gestión de base de datos PostgreSQL en Docker.
Solo actúa sobre PostgreSQL. SQLite ha sido eliminado.
"""
import psycopg2
import psycopg2.extras
import os
import requests
import shutil
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_PATH = os.path.join(BASE_DIR, '..', 'frontend', 'uploads')

# PostgreSQL EXCLUSIVAMENTE
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("❌ ERROR: DATABASE_URL no definida. Revisa .env")

API_URL = os.getenv('API_URL_INTERNAL', 'http://127.0.0.1:5000')

print("🐘 GESTOR DE BD: PostgreSQL únicamente")

# --- DATOS DE PRUEBA ---
PROPIETARIO_DATA = {
    "nombre": "Pedro Propietario",
    "email": "propietario@sectormind.com",
    "password": "p",
    "rol": "propietario",
    "foto_perfil_url": "https://images.unsplash.com/photo-1560250097-0b93528c311a?ixlib=rb-1.2.1&auto=format&fit=crop&w=256&q=80"
}

CLIENTE_DATA = {
    "nombre": "Ursula Usuario",
    "email": "cliente@sectormind.com",
    "password": "c",
    "rol": "cliente",
    "foto_perfil_url": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?ixlib=rb-1.2.1&auto=format&fit=crop&w=256&q=80"
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
        "foto_url": "https://images.unsplash.com/photo-1560066984-138dadb4c035?ixlib=rb-4.0.3&w=800&q=80",
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
        "foto_url": "https://images.pexels.com/photos/3587352/pexels-photo-3587352.jpeg?w=800",
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
        "foto_url": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800",
        "horarios": HORARIO_PARTIDO,
        "servicios": [
            {"nombre": "Masaje deportivo", "precio": 40.00, "duracion_minutos": 45},
            {"nombre": "Punción seca", "precio": 45.00, "duracion_minutos": 30}
        ]
    }
]


def clean_uploads():
    """🧹 Limpia la carpeta de uploads."""
    print(f"\n1️⃣  LIMPIANDO CARPETA UPLOADS...")
    if os.path.exists(UPLOADS_PATH):
        for filename in os.listdir(UPLOADS_PATH):
            file_path = os.path.join(UPLOADS_PATH, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"    ⚠️ Error borrando {file_path}: {e}")
        print("    ✅ Carpeta 'frontend/uploads' vaciada.")
    else:
        os.makedirs(UPLOADS_PATH, exist_ok=True)
        print("    ✅ Carpeta 'frontend/uploads' creada.")


def init_db():
    """🗄️ Reinicializa la BD PostgreSQL."""
    print(f"\n2️⃣  REINICIALIZANDO BASE DE DATOS POSTGRESQL...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
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


def populate_api():
    """👥 Puebla datos de prueba vía API."""
    print(f"\n3️⃣  POBLANDO DATOS VÍA API...")
    
    # Verificar que Flask está corriendo
    try:
        requests.get(API_URL)
    except:
        print("    ⚠️ FLASK ESTÁ APAGADO. Enciéndelo con: python -m backend.app")
        return

    # --- CREAR PROPIETARIO ---
    print(f"    👤 Registrando Propietario...")
    prop_id = None
    try:
        res = requests.post(f"{API_URL}/auth/register", data=PROPIETARIO_DATA)
        if res.status_code == 201:
            prop_id = res.json()['id']
            print(f"       ✅ {PROPIETARIO_DATA['nombre']} (ID: {prop_id})")
        else:
            print(f"       ❌ {res.text}")
    except Exception as e:
        print(f"       ❌ {e}")

    # --- CREAR CLIENTE ---
    print(f"    👤 Registrando Cliente...")
    try:
        res = requests.post(f"{API_URL}/auth/register", data=CLIENTE_DATA)
        if res.status_code == 201:
            print(f"       ✅ {CLIENTE_DATA['nombre']} (ID: {res.json()['id']})")
        else:
            print(f"       ❌ {res.text}")
    except Exception as e:
        print(f"       ❌ {e}")

    # --- CREAR NEGOCIOS + SERVICIOS + HORARIOS ---
    if not prop_id:
        print("    ⚠️ No hay propietario. Saltando negocios.")
        return
    
    print("    🏢 Creando Negocios...")
    created_negocios = []
    
    for negocio in NEGOCIOS:
        payload = {
            "nombre": negocio["nombre"],
            "tipo_negocio": negocio["tipo_negocio"],
            "direccion": negocio["direccion"],
            "descripcion": negocio.get("descripcion"),
            "foto_url": negocio.get("foto_url"),
            "propietario_id": prop_id
        }
        
        try:
            r = requests.post(f"{API_URL}/negocios/", json=payload)
            if r.status_code == 201:
                new_id = r.json().get('id')
                created_negocios.append({"id": new_id, **negocio})
                print(f"       ✅ {negocio['nombre']} (ID: {new_id})")
            else:
                print(f"       ❌ {r.text}")
        except Exception as e:
            print(f"       ❌ {e}")

    # --- INSERTAR HORARIOS Y SERVICIOS DIRECTAMENTE EN BD ---
    if created_negocios:
        print("    ⏰ Insertando horarios y servicios...")
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            
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
            
            conn.commit()
            print("       ✅ Horarios y servicios insertados.")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"       ❌ ERROR: {e}")


def add_past_citas():
    """📅 Añade citas pasadas al cliente de prueba."""
    print(f"\n4️⃣  AÑADIENDO CITAS PASADAS...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Obtener ID del cliente
        cursor.execute("SELECT id FROM usuarios WHERE nombre = 'Ursula Usuario'")
        result = cursor.fetchone()
        
        if not result:
            print("    ⚠️ Usuario 'Ursula Usuario' no encontrado")
            conn.close()
            return
        
        cliente_id = result[0]
        
        # Obtener primer negocio y 2 servicios
        cursor.execute("SELECT id FROM negocios LIMIT 1")
        result = cursor.fetchone()
        if not result:
            print("    ⚠️ No hay negocios disponibles")
            conn.close()
            return
        
        negocio_id = result[0]
        
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
            (negocio_id, cliente_id, servicios[0][0], fecha_pasada_1, servicios[0][1], 'confirmada')
        )
        
        cursor.execute(
            "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (%s, %s, %s, %s, %s, %s)",
            (negocio_id, cliente_id, servicios[1][0], fecha_pasada_2, servicios[1][1], 'confirmada')
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
    
    clean_uploads()
    if init_db():
        populate_api()
        add_past_citas()
        print("\n✨ ¡SISTEMA RESTAURADO COMPLETAMENTE! ✨")
        print(f"   → Propietario: {PROPIETARIO_DATA['email']}")
        print(f"   → Cliente:     {CLIENTE_DATA['email']}")
    else:
        print("\n❌ No se pudo inicializar la base de datos.")


if __name__ == '__main__':
    main()