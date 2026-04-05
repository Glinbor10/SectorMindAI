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
                COALESCE(s.nombre, 'Servicio no válido para este negocio') as servicio_nombre,
                s.precio,
                u.nombre as cliente_nombre,
                u.email as cliente_email
            FROM citas c
            JOIN negocios n ON c.negocio_id = n.id
            LEFT JOIN servicios s ON c.servicio_id = s.id AND s.negocio_id = c.negocio_id
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
    
    # Aceptar usuario_id o cliente_id (retrocompatibilidad)
    cliente_id = data.get('usuario_id') or data.get('cliente_id')

    if not (negocio_id and servicio_id and fecha_hora_cita and cliente_id):
        return jsonify({'error': 'Faltan datos obligatorios (negocio_id, servicio_id, fecha_hora_cita, usuario_id)'}), 400

    conn = get_db_connection()
    try:
        # Validar que el servicio pertenezca al negocio
        servicio = conn.execute(
            'SELECT duracion_minutos FROM servicios WHERE id = %s AND negocio_id = %s',
            (servicio_id, negocio_id)
        ).fetchone()
        if not servicio:
            return jsonify({'error': 'Servicio no válido para este negocio'}), 400

        # Validar disponibilidad
        es_valida, mensaje = verificar_solapamiento(negocio_id, servicio_id, fecha_hora_cita, conn)
        
        if not es_valida:
            # Detectar tipos de error: solapamiento, horario cerrado, etc. retornan 409 (conflict)
            # Solo validaciones de formato retornan 400
            if any(keyword in mensaje.lower() for keyword in ['solapa', 'horario', 'cerrado']):
                return jsonify({'error': mensaje}), 409
            else:
                return jsonify({'error': mensaje}), 400

        # Duración obtenida de la validación anterior
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
    cita_id_excluir = data.get('cita_id_excluir')  # Opcional: para excluir al editar

    if not (negocio_id and servicio_id and fecha_str):
        return jsonify({'error': 'Faltan datos (negocio_id, servicio_id, fecha)'}), 400

    conn = get_db_connection()
    try:
        resultado = obtener_tramos_disponibles(negocio_id, servicio_id, fecha_str, conn, cita_id_excluir)
        
        if 'error' in resultado:
            return jsonify(resultado), 400
        
        return jsonify({'disponibles': resultado.get('disponibles', []), 'mensaje': resultado.get('mensaje', '')})
        
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
    usuario_id = data.get('usuario_id')  # Nuevo: permite cambiar el cliente
    
    print(f"📥 PUT /citas/{cita_id} - Data: {data}")
    print(f"   servicio_id: {servicio_id}, fecha_hora_cita: {fecha_hora_cita}, usuario_id: {usuario_id}")
    
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
        
        # Validar disponibilidad (excluir la cita actual de la verificación)
        es_valida, mensaje = verificar_solapamiento(negocio_id, servicio_id, fecha_hora_cita, conn, cita_id_excluir=cita_id)
        
        if not es_valida:
            return jsonify({'error': mensaje}), 400

        # Obtener duración validando que el servicio pertenezca al negocio de la cita
        servicio = conn.execute(
            'SELECT duracion_minutos FROM servicios WHERE id = %s AND negocio_id = %s',
            (servicio_id, negocio_id)
        ).fetchone()
        
        if not servicio:
            return jsonify({'error': 'Servicio no válido para este negocio'}), 400

        # Actualizar cita (incluir cliente_id si viene)
        cursor = conn.cursor()
        if usuario_id:
            cursor.execute(
                '''
                    UPDATE citas 
                    SET servicio_id = %s, fecha_hora_cita = %s, duracion_minutos = %s, cliente_id = %s 
                    WHERE id = %s
                ''',
                (servicio_id, fecha_hora_cita, servicio['duracion_minutos'], usuario_id, cita_id)
            )
        else:
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