# backend/routes/citas.py
from flask import Blueprint, jsonify, request
import sqlite3
# Importamos la conexión y la lógica desde el paquete padre
from ..db import get_db_connection 
from ..logic import obtener_tramos_disponibles, verificar_solapamiento 

# Definimos el Blueprint. Aquí no usamos url_prefix para que las rutas sean /citas y /disponibilidad
citas_bp = Blueprint('citas', __name__)

# --- ENDPOINT DE DISPONIBILIDAD (CRÍTICO PARA RASA) ---

# Endpoint: Obtener Disponibilidad (POST /disponibilidad)
@citas_bp.route('/disponibilidad', methods=['POST'])
def obtener_disponibilidad():
    data = request.get_json()
    negocio_id = data.get('negocio_id')
    servicio_id = data.get('servicio_id')
    fecha = data.get('fecha') # Formato esperado: YYYY-MM-DD

    if not (negocio_id and servicio_id and fecha):
        return jsonify({'error': 'Faltan negocio_id, servicio_id o fecha'}), 400

    conn = get_db_connection()
    # Llamamos a la función de lógica
    resultado = obtener_tramos_disponibles(negocio_id, servicio_id, fecha, conn)
    conn.close()
    
    if 'error' in resultado:
        return jsonify(resultado), 400
        
    return jsonify(resultado), 200

# --- ENDPOINTS DE CITAS ---

# Endpoint: Listar citas (GET /citas)
@citas_bp.route('/citas', methods=['GET'])
def listar_citas():
    conn = get_db_connection()
    citas = conn.execute('SELECT * FROM citas').fetchall()
    conn.close()
    return jsonify([dict(row) for row in citas])

# Endpoint: Crear cita (POST /citas)
@citas_bp.route('/citas', methods=['POST'])
def crear_cita():
    data = request.get_json()
    negocio_id = data.get('negocio_id')
    servicio_id = data.get('servicio_id')
    fecha_hora_cita = data.get('fecha_hora_cita') # Esperado: 'YYYY-MM-DD HH:MM:SS'
    
    if not (negocio_id and servicio_id and fecha_hora_cita):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    conn = get_db_connection()
    
    # VALIDACIÓN DE DISPONIBILIDAD FINAL
    es_valida, mensaje = verificar_solapamiento(negocio_id, servicio_id, fecha_hora_cita, conn)
    
    if not es_valida:
        conn.close()
        return jsonify({'error': f'No se puede crear la cita: {mensaje}'}), 409 # 409 Conflict

    # Si es válida, procedemos con la inserción
    cur = conn.cursor()
    try:
        cur.execute(
            'INSERT INTO citas (negocio_id, servicio_id, fecha_hora_cita) VALUES (?, ?, ?)',
            (negocio_id, servicio_id, fecha_hora_cita)
        )
        conn.commit()
        cita_id = cur.lastrowid
        return jsonify({'id': cita_id, 'mensaje': 'Cita creada y validada correctamente'}), 201
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({'error': f'Error al insertar en la base de datos: {e}'}), 500
    finally:
        conn.close()