# backend/routes/citas.py
from flask import Blueprint, jsonify, request
import sqlite3
from ..db import get_db_connection 
from ..logic import obtener_tramos_disponibles, verificar_solapamiento 

# Definimos el Blueprint. Aquí no usamos url_prefix para que las rutas sean /citas y /disponibilidad
citas_bp = Blueprint('citas', __name__)


# Endpoint: Obtener Citas (GET /citas)
# AHORA ADMITE FILTROS: ?cliente_id=1  O  ?negocio_id=2
@citas_bp.route('/citas', methods=['GET'])
def obtener_citas():
    cliente_id = request.args.get('cliente_id')
    negocio_id = request.args.get('negocio_id')

    conn = get_db_connection()
    
    # Preparamos una consulta que une tablas para dar información útil (nombres en vez de solo IDs)
    query = '''
        SELECT 
            c.id, c.fecha_hora_cita, c.estado, c.duracion_minutos,
            n.nombre as negocio_nombre, 
            s.nombre as servicio_nombre, 
            s.precio,
            u.nombre as cliente_nombre
        FROM citas c
        JOIN negocios n ON c.negocio_id = n.id
        JOIN servicios s ON c.servicio_id = s.id
        JOIN usuarios u ON c.cliente_id = u.id
    '''
    
    params = []
    conditions = []

    if cliente_id:
        conditions.append("c.cliente_id = ?")
        params.append(cliente_id)
    
    if negocio_id:
        conditions.append("c.negocio_id = ?")
        params.append(negocio_id)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    # Ordenar por fecha más reciente
    query += " ORDER BY c.fecha_hora_cita DESC"

    citas = conn.execute(query, params).fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in citas])

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