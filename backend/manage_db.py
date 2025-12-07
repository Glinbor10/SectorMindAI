import sqlite3
import os
import requests
import json
import shutil
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'database', 'tfg_data.db')
SCHEMA_PATH = os.path.join(BASE_DIR, '..', 'database', 'schema.sql')
UPLOADS_PATH = os.path.join(BASE_DIR, '..', 'frontend', 'uploads')
API_URL = "http://127.0.0.1:5000"

# --- DATOS DE PRUEBA CORREGIDOS ---

# 1. Propietario (Email válido, Password simple: 'p')
PROPIETARIO_DATA = {
    "nombre": "Pedro Propietario",
    "email": "propietario@sectormind.com",  # Email válido
    "password": "p",                        # Contraseña 'p'
    "rol": "propietario",
    "foto_perfil_url": "https://images.unsplash.com/photo-1560250097-0b93528c311a?ixlib=rb-1.2.1&auto=format&fit=crop&w=256&q=80"
}

# 2. Cliente (Email válido, Password simple: 'c')
CLIENTE_DATA = {
    "nombre": "Ursula Usuario",
    "email": "cliente@sectormind.com",      # Email válido
    "password": "c",                        # Contraseña 'c'
    "rol": "cliente",
    "foto_perfil_url": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?ixlib=rb-1.2.1&auto=format&fit=crop&w=256&q=80"
}

# 3. Horarios Genéricos
HORARIO_PARTIDO = []
for dia in range(5): 
    HORARIO_PARTIDO.extend([
        {"dia_semana": dia, "hora_apertura": "09:30:00", "hora_cierre": "13:30:00"},
        {"dia_semana": dia, "hora_apertura": "16:30:00", "hora_cierre": "20:00:00"}
    ])

# 4. Negocios (Se asignarán a Pedro)
NEGOCIOS = [
    {
        "nombre": "Peluquería Estilo & Glamour",
        "tipo_negocio": "peluqueria",
        "direccion": "Av. de la Moda, 45, Madrid",
        "descripcion": "Especialistas en cambios de imagen radicales y colorimetría avanzada.",
        "foto_url": "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=1200&q=80",
        "horarios": HORARIO_PARTIDO,
        "servicios": [
            {"nombre": "Corte de pelo", "precio": 15.00, "duracion_minutos": 30},
            {"nombre": "Tinte completo", "precio": 45.00, "duracion_minutos": 90}
        ]
    },
    {
        "nombre": "Clínica Dental Sonrisa",
        "tipo_negocio": "dentista",
        "direccion": "Calle Salud, 12, Planta 2",
        "descripcion": "Tu salud bucodental en las mejores manos. Ortodoncia invisible.",
        "foto_url": "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=1200&q=80",
        "horarios": HORARIO_PARTIDO,
        "servicios": [
            {"nombre": "Limpieza dental", "precio": 50.00, "duracion_minutos": 45},
            {"nombre": "Empaste simple", "precio": 60.00, "duracion_minutos": 60}
        ]
    },
    {
        "nombre": "FisioMente Centro",
        "tipo_negocio": "fisioterapia",
        "direccion": "Plaza del Deporte, s/n",
        "descripcion": "Recupérate de tus lesiones con nuestro equipo de expertos.",
        "foto_url": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=1200&q=80",
        "horarios": HORARIO_PARTIDO,
        "servicios": [
            {"nombre": "Masaje deportivo", "precio": 40.00, "duracion_minutos": 45},
            {"nombre": "Punción seca", "precio": 45.00, "duracion_minutos": 30}
        ]
    }
]

def clean_uploads():
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
        os.makedirs(UPLOADS_PATH)
        print("    ✅ Carpeta 'frontend/uploads' creada.")

def init_db():
    print(f"\n2️⃣  RESETEANDO BASE DE DATOS...")
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        conn = sqlite3.connect(DB_PATH)
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.close()
        print("    ✅ Tablas creadas desde cero.")
        return True
    except Exception as e:
        print(f"    ❌ ERROR CRÍTICO DB: {e}")
        return False

def populate_api():
    print(f"\n3️⃣  POBLANDO DATOS VÍA API...")
    try:
        requests.get(API_URL)
    except:
        print("    ⚠️  FLASK ESTÁ APAGADO. Enciéndelo en otra terminal con: python -m backend.app")
        return

    # --- A. CREAR PROPIETARIO ---
    print(f"    👤 Registrando Propietario...")
    prop_id = None
    try:
        res = requests.post(f"{API_URL}/auth/register", data=PROPIETARIO_DATA)
        if res.status_code == 201:
            prop_id = res.json()['id']
            print(f"       [OK] {PROPIETARIO_DATA['nombre']} (ID: {prop_id})")
        else:
            print(f"       [ERROR] {res.text}")
    except Exception as e:
        print(f"       [FAIL] {e}")

    # --- B. CREAR CLIENTE ---
    print(f"    👤 Registrando Cliente...")
    try:
        res = requests.post(f"{API_URL}/auth/register", data=CLIENTE_DATA)
        if res.status_code == 201:
            print(f"       [OK] {CLIENTE_DATA['nombre']} (ID: {res.json()['id']})")
        else:
            print(f"       [ERROR] {res.text}")
    except Exception as e:
        print(f"       [FAIL] {e}")

    # --- C. CREAR NEGOCIOS ---
    if prop_id:
        print("    🏢 Creando Negocios...")
        for negocio in NEGOCIOS:
            negocio['propietario_id'] = prop_id
            try:
                r = requests.post(f"{API_URL}/negocios/", json=negocio)
                if r.status_code == 201:
                    print(f"       [OK] {negocio['nombre']}")
                else:
                    print(f"       [ERROR] {r.text}")
            except Exception as e:
                print(f"       [FAIL] {e}")
    else:
        print("    ⚠️ Saltando creación de negocios porque falló el registro del propietario.")

def add_past_citas():
    """Añade citas pasadas completadas al cliente Úrsula."""
    print(f"\n4️⃣  AÑADIENDO CITAS PASADAS...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Obtener ID de Úrsula
        cursor.execute("SELECT id FROM usuarios WHERE nombre = 'Ursula Usuario'")
        result = cursor.fetchone()
        
        if not result:
            print("    ⚠️ Usuario 'Ursula Usuario' no encontrado")
            conn.close()
            return
        
        ursula_id = result[0]
        
        # Obtener un negocio y servicios
        cursor.execute("SELECT id FROM negocios LIMIT 1")
        negocio_result = cursor.fetchone()
        
        if not negocio_result:
            print("    ⚠️ No hay negocios disponibles")
            conn.close()
            return
        
        negocio_id = negocio_result[0]
        
        cursor.execute("SELECT id, duracion_minutos FROM servicios LIMIT 2")
        servicios = cursor.fetchall()
        
        if len(servicios) < 2:
            print("    ⚠️ Se necesitan al menos 2 servicios disponibles")
            conn.close()
            return
        
        # Crear dos citas pasadas (hace 5 y 3 días)
        fecha_pasada_1 = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d 10:00:00')
        fecha_pasada_2 = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d 14:30:00')
        
        servicio_1_id, duracion_1 = servicios[0]
        servicio_2_id, duracion_2 = servicios[1]
        
        cursor.execute(
            "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (?, ?, ?, ?, ?, ?)",
            (negocio_id, ursula_id, servicio_1_id, fecha_pasada_1, duracion_1, 'confirmada')
        )
        
        cursor.execute(
            "INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) VALUES (?, ?, ?, ?, ?, ?)",
            (negocio_id, ursula_id, servicio_2_id, fecha_pasada_2, duracion_2, 'confirmada')
        )
        
        conn.commit()
        print(f"    ✅ 2 citas pasadas añadidas a Úrsula:")
        print(f"       - Cita 1: {fecha_pasada_1}")
        print(f"       - Cita 2: {fecha_pasada_2}")
        
        conn.close()
    except Exception as e:
        print(f"    ❌ ERROR: {e}")

def main():
    clean_uploads()
    if init_db():
        populate_api()
        add_past_citas()
        print("\n✨ ¡SISTEMA RESTAURADO COMPLETAMENTE! ✨")
        print(f"   -> Login Propietario: {PROPIETARIO_DATA['email']} / {PROPIETARIO_DATA['password']}")
        print(f"   -> Login Cliente:     {CLIENTE_DATA['email']} / {CLIENTE_DATA['password']}")

if __name__ == '__main__':
    main()