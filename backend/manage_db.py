import sqlite3
import os
import requests
import json

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'database', 'tfg_data.db')
SCHEMA_PATH = os.path.join(BASE_DIR, '..', 'database', 'schema.sql')
API_URL = "http://127.0.0.1:5000"

# --- DATOS PROPIETARIO ---
PROPIETARIO_DEMO = {
    "nombre": "Juan Emprendedor",
    "email": "juan@sectormind.com",
    "password": "123",
    "rol": "propietario"
}

# --- DATOS NEGOCIOS ---
# Horarios (reutilizados)
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
        "descripcion": "Especialistas en cambios de imagen radicales y colorimetría avanzada. Usamos productos 100% orgánicos.",
        "foto_url": "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=1200&q=80",
        "horarios": HORARIO_PARTIDO,
        "servicios": [
            {"nombre": "Corte de pelo", "precio": 15.00, "duracion_minutos": 30},
            {"nombre": "Tinte completo", "precio": 45.00, "duracion_minutos": 90}
        ]
    },
    {
        "nombre": "Clínica Dental Sonrisa Perfecta",
        "tipo_negocio": "dentista",
        "direccion": "Calle Salud, 12, Planta 2",
        "descripcion": "Tu salud bucodental en las mejores manos. Ortodoncia invisible e implantes de última generación.",
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
        "descripcion": "Recupérate de tus lesiones con nuestro equipo de expertos en fisioterapia deportiva y osteopatía.",
        "foto_url": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=1200&q=80",
        "horarios": HORARIO_PARTIDO,
        "servicios": [
            {"nombre": "Masaje deportivo", "precio": 40.00, "duracion_minutos": 45},
            {"nombre": "Punción seca", "precio": 45.00, "duracion_minutos": 30}
        ]
    }
]

def init_db():
    print(f"\n1️⃣  RESETEANDO BASE DE DATOS...")
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        conn = sqlite3.connect(DB_PATH)
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.close()
        print("    ✅ Tablas creadas (con soporte para Propietarios).")
        return True
    except Exception as e:
        print(f"    ❌ ERROR CRÍTICO: {e}")
        return False

def populate_api():
    print(f"\n2️⃣  POBLANDO DATOS VÍA API...")
    try:
        requests.get(API_URL)
    except:
        print("    ⚠️  FLASK ESTÁ APAGADO. Enciéndelo primero.")
        return

    # 1. Crear Propietario
    print("    👤 Registrando propietario demo...")
    try:
        res_prop = requests.post(f"{API_URL}/auth/register", json=PROPIETARIO_DEMO)
        if res_prop.status_code == 201:
            # Login para obtener ID (truco rápido: asumimos que es ID 1 porque está vacía)
            # Pero lo correcto es loguearse
            res_login = requests.post(f"{API_URL}/auth/login", json={"email": PROPIETARIO_DEMO['email'], "password": PROPIETARIO_DEMO['password']})
            propietario_id = res_login.json()['id']
            print(f"    [OK] Propietario creado (ID: {propietario_id})")
        else:
            print("    ⚠️  El usuario ya existía o falló. Usando ID=1 por defecto.")
            propietario_id = 1
    except:
        propietario_id = 1

    # 2. Crear Negocios vinculados a ese ID
    for negocio in NEGOCIOS:
        negocio['propietario_id'] = propietario_id # Vinculamos
        try:
            r = requests.post(f"{API_URL}/negocios/", json=negocio)
            if r.status_code == 201:
                print(f"    [OK] Negocio creado: {negocio['nombre']}")
            else:
                print(f"    [ERROR] Falló {negocio['nombre']}: {r.text}")
        except Exception as e:
            print(f"    [FAIL] Error conexión: {e}")

def main():
    if init_db():
        populate_api()

if __name__ == '__main__':
    main()