# backend/routes/citas.py
# filepath: backend/routes/citas.py
from flask import Blueprint, jsonify, request
from datetime import datetime, date, time
from ..db import get_db_connection
from ..logic import obtener_tramos_disponibles, verificar_solapamiento


citas_bp = Blueprint('citas', __name__)


def serialize_row(row):
    """Convierte datetime, date, time a strings para JSON."""
    result = dict(row)
    for key, value in result.items():
        if isinstance(value, (datetime, date, time)):
            result[key] = str(value)
    return result


@citas_bp.route('/citas', methods=['GET'])
def obtener_citas():
    """GET /citas - Lista citas con filtros opcionales (PostgreSQL)."""
    cliente_id = request.args.get('cliente_id')
    negocio_id = request.args.get('negocio_id')

    conn = get_db_connection()
    try:
        query = '''
            SELECT 
                c.id, c.cliente_id, c.fecha_hora_cita, c.estado, c.duracion_minutos,
                c.negocio_id, c.servicio_id,
                n.nombre as negocio_nombre, n.tipo_negocio,
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
        
        # Siempre excluir citas canceladas
        conditions.append("c.estado != 'cancelada'")

        if cliente_id:
            conditions.append("c.cliente_id = %s")
            params.append(cliente_id)
        
        if negocio_id:
            conditions.append("c.negocio_id = %s")
            params.append(negocio_id)
        
        query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY c.fecha_hora_cita DESC"

        citas = conn.execute(query, params).fetchall()
        return jsonify([serialize_row(row) for row in citas])
        
    finally:
        conn.close()


@citas_bp.route('/citas', methods=['POST'])
def crear_cita():
    """POST /citas - Crea nueva cita (PostgreSQL)."""
    data = request.get_json()
    negocio_id = data.get('negocio_id')
    servicio_id = data.get('servicio_id')
    fecha_hora_cita = data.get('fecha_hora_cita')
    cliente_id = data.get('cliente_id', 2)

    if not (negocio_id and servicio_id and fecha_hora_cita):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    conn = get_db_connection()
    try:
        # Validar disponibilidad
        es_valida, mensaje = verificar_solapamiento(negocio_id, servicio_id, fecha_hora_cita, conn)
        
        if not es_valida:
            # Detectar tipos de error: solapamiento, horario cerrado, etc. retornan 409 (conflict)
            # Solo validaciones de formato retornan 400
            if any(keyword in mensaje.lower() for keyword in ['solapa', 'horario', 'cerrado']):
                return jsonify({'error': mensaje}), 409
            else:
                return jsonify({'error': mensaje}), 400

        # Obtener duración del servicio
        servicio = conn.execute(
            'SELECT duracion_minutos FROM servicios WHERE id = %s',
            (servicio_id,)
        ).fetchone()
        
        if not servicio:
            return jsonify({'error': 'Servicio no válido'}), 400
        
        duracion = servicio['duracion_minutos']

        # Crear cita
        cursor = conn.cursor()
        cursor.execute(
            '''
                INSERT INTO citas (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion_minutos, estado) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                RETURNING id
            ''',
            (negocio_id, cliente_id, servicio_id, fecha_hora_cita, duracion, 'confirmada')
        )
        conn.commit()
        new_id = cursor.fetchone()['id']
        
        return jsonify({'id': new_id, 'message': 'Cita creada exitosamente'}), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@citas_bp.route('/disponibilidad', methods=['POST'])
def consultar_disponibilidad():
    """POST /disponibilidad - Consulta tramos disponibles (PostgreSQL)."""
    data = request.get_json()
    negocio_id = data.get('negocio_id')
    servicio_id = data.get('servicio_id')
    fecha_str = data.get('fecha')

    if not (negocio_id and servicio_id and fecha_str):
        return jsonify({'error': 'Faltan datos (negocio_id, servicio_id, fecha)'}), 400

    conn = get_db_connection()
    try:
        resultado = obtener_tramos_disponibles(negocio_id, servicio_id, fecha_str, conn)
        
        if 'error' in resultado:
            return jsonify(resultado), 400
        
        return jsonify({'disponibles': resultado.get('disponibles', [])})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@citas_bp.route('/citas/<int:cita_id>', methods=['PUT'])
def modificar_cita(cita_id):
    """PUT /citas/{id} - Modifica cita existente (PostgreSQL)."""
    data = request.get_json()
    servicio_id = data.get('servicio_id')
    fecha_hora_cita = data.get('fecha_hora_cita')
    
    print(f"📥 PUT /citas/{cita_id} - Data: {data}")
    print(f"   servicio_id: {servicio_id}, fecha_hora_cita: {fecha_hora_cita}")
    
    if not (servicio_id and fecha_hora_cita):
        print(f"❌ Faltan datos obligatorios")
        return jsonify({'error': 'Faltan datos obligatorios'}), 400
    
    conn = get_db_connection()
    
    try:
        # Verificar que cita existe
        cita = conn.execute(
            'SELECT negocio_id FROM citas WHERE id = %s',
            (cita_id,)
        ).fetchone()
        
        if not cita:
            return jsonify({'error': 'Cita no encontrada'}), 404
        
        negocio_id = cita['negocio_id']
        
        # Validar disponibilidad
        es_valida, mensaje = verificar_solapamiento(negocio_id, servicio_id, fecha_hora_cita, conn)
        
        if not es_valida:
            return jsonify({'error': mensaje}), 400

        # Obtener duración
        servicio = conn.execute(
            'SELECT duracion_minutos FROM servicios WHERE id = %s',
            (servicio_id,)
        ).fetchone()
        
        if not servicio:
            return jsonify({'error': 'Servicio no válido'}), 400

        # Actualizar cita
        cursor = conn.cursor()
        cursor.execute(
            '''
                UPDATE citas 
                SET servicio_id = %s, fecha_hora_cita = %s, duracion_minutos = %s 
                WHERE id = %s
            ''',
            (servicio_id, fecha_hora_cita, servicio['duracion_minutos'], cita_id)
        )
        conn.commit()
        
        return jsonify({'message': 'Cita modificada exitosamente'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@citas_bp.route('/citas/<int:cita_id>', methods=['DELETE'])
def cancelar_cita(cita_id):
    """DELETE /citas/{id} - Cancela cita (cambia estado a 'cancelada')."""
    conn = get_db_connection()
    try:
        # Verificar que existe
        cita = conn.execute(
            'SELECT * FROM citas WHERE id = %s',
            (cita_id,)
        ).fetchone()
        
        if not cita:
            return jsonify({'error': 'Cita no encontrada'}), 404
        
        # Cambiar estado a cancelada
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE citas SET estado = %s WHERE id = %s',
            ('cancelada', cita_id)
        )
        conn.commit()
        
        return jsonify({'message': 'Cita cancelada exitosamente'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()