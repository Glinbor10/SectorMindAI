from flask import Blueprint, jsonify, request
import sqlite3
from ..db import get_db_connection 
# IMPORTANTE: Importamos ambas funciones de lógica
from ..logic import obtener_tramos_disponibles, verificar_solapamiento 

# Definimos el Blueprint
citas_bp = Blueprint('citas', __name__)

# 1. OBTENER CITAS (GET /citas)
@citas_bp.route('/citas', methods=['GET'])
def obtener_citas():
    cliente_id = request.args.get('cliente_id')
    negocio_id = request.args.get('negocio_id')

    conn = get_db_connection()
    
    # Preparamos una consulta que une tablas para dar información útil
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
        
    query += " ORDER BY c.fecha_hora_cita DESC"

    citas = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in citas])

# 2. CREAR CITA (POST /citas)
@citas_bp.route('/citas', methods=['POST'])
def crear_cita():
    data = request.get_json()
    negocio_id = data.get('negocio_id')
    servicio_id = data.get('servicio_id')
    fecha_hora_cita = data.get('fecha_hora_cita') # Esperado: 'YYYY-MM-DD HH:MM:SS'
    
    # En un caso real, el cliente_id vendría del token de sesión.
    # Aquí simulamos que es el usuario 2 (un cliente de prueba) si no se envía.
    cliente_id = data.get('cliente_id', 2) 

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
        # Obtenemos duración para guardarla en la cita (histórico)
        duracion = conn.execute('SELECT duracion_minutos FROM servicios WHERE id = ?', (servicio_id,)).fetchone()['duracion_minutos']

        cur.execute(
            'INSERT INTO citas (negocio_id, servicio_id, cliente_id, fecha_hora_cita, duracion_minutos, estado) VALUES (?, ?, ?, ?, ?, ?)',
            (negocio_id, servicio_id, cliente_id, fecha_hora_cita, duracion, 'confirmado')
        )
        conn.commit()
        new_id = cur.lastrowid
        return jsonify({'id': new_id, 'message': 'Cita creada exitosamente'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 3. CONSULTAR DISPONIBILIDAD (POST /disponibilidad) - ¡ESTA ES LA NUEVA!
@citas_bp.route('/disponibilidad', methods=['POST'])
def consultar_disponibilidad():
    data = request.get_json()
    negocio_id = data.get('negocio_id')
    servicio_id = data.get('servicio_id')  # Ahora requerimos servicio_id
    fecha_str = data.get('fecha') # Esperamos 'YYYY-MM-DD'

    if not (negocio_id and servicio_id and fecha_str):
        return jsonify({'error': 'Faltan datos (negocio_id, servicio_id, fecha)'}), 400

    conn = get_db_connection()
    try:
        # Usamos tu lógica existente en logic.py (actualizada para recibir servicio_id)
        resultado = obtener_tramos_disponibles(negocio_id, servicio_id, fecha_str, conn)
        
        if 'error' in resultado:
            return jsonify(resultado), 400
        
        return jsonify({'disponibles': resultado.get('disponibles', [])})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 4. ELIMINAR/CANCELAR CITA (DELETE /citas/<id>)
@citas_bp.route('/citas/<int:cita_id>', methods=['DELETE'])
def cancelar_cita(cita_id):
    conn = get_db_connection()
    try:
        # Verificar que la cita existe
        cita = conn.execute('SELECT * FROM citas WHERE id = ?', (cita_id,)).fetchone()
        
        if not cita:
            return jsonify({'error': 'Cita no encontrada'}), 404
        
        # Cambiar estado a "cancelado" en lugar de eliminar
        conn.execute('UPDATE citas SET estado = ? WHERE id = ?', ('cancelado', cita_id))
        conn.commit()
        
        return jsonify({'message': 'Cita cancelada exitosamente'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()