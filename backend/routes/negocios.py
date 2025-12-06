from flask import Blueprint, jsonify, request
import sqlite3
from ..db import get_db_connection 

negocios_bp = Blueprint('negocios', __name__, url_prefix='/negocios')

# 1. LISTAR NEGOCIOS
@negocios_bp.route('/', methods=['GET'])
def listar_negocios():
    propietario_id = request.args.get('propietario_id')
    
    conn = get_db_connection()
    query = """
        SELECT n.*, u.nombre as propietario_nombre 
        FROM negocios n 
        JOIN usuarios u ON n.propietario_id = u.id
    """
    params = []
    
    if propietario_id:
        query += " WHERE n.propietario_id = ?"
        params.append(propietario_id)
        
    negocios = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in negocios])

# 2. OBTENER UN SOLO NEGOCIO
@negocios_bp.route('/<int:negocio_id>', methods=['GET'])
def obtener_negocio(negocio_id):
    conn = get_db_connection()
    query = """
        SELECT n.*, u.nombre as propietario_nombre 
        FROM negocios n 
        JOIN usuarios u ON n.propietario_id = u.id
        WHERE n.id = ?
    """
    negocio = conn.execute(query, (negocio_id,)).fetchone()
    conn.close()
    
    if negocio is None:
        return jsonify({'error': 'Negocio no encontrado'}), 404
        
    return jsonify(dict(negocio))

# 3. CREAR NEGOCIO
@negocios_bp.route('/', methods=['POST'])
def crear_negocio():
    data = request.get_json()
    nombre = data.get('nombre')
    tipo_negocio = data.get('tipo_negocio', 'general')  # Valor por defecto si no se envía
    direccion = data.get('direccion')
    propietario_id = data.get('propietario_id') # En producción, esto vendría del token de sesión

    if not (nombre and direccion and propietario_id):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO negocios (nombre, tipo_negocio, direccion, propietario_id) VALUES (?, ?, ?, ?)',
            (nombre, tipo_negocio, direccion, propietario_id)
        )
        conn.commit()
        new_id = cur.lastrowid
        return jsonify({'id': new_id, 'message': 'Negocio creado exitosamente'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 4. ACTUALIZAR NEGOCIO
@negocios_bp.route('/<int:negocio_id>', methods=['PUT'])
def actualizar_negocio(negocio_id):
    data = request.get_json()
    
    descripcion = data.get('descripcion')
    foto_url = data.get('foto_url')
    direccion = data.get('direccion')

    if not any([descripcion, foto_url, direccion]):
         return jsonify({'error': 'No hay datos para actualizar'}), 400

    conn = get_db_connection()
    try:
        updates = []
        params = []

        if descripcion is not None:
            updates.append("descripcion = ?")
            params.append(descripcion)
        if foto_url is not None:
            updates.append("foto_url = ?")
            params.append(foto_url)
        if direccion is not None:
            updates.append("direccion = ?")
            params.append(direccion)

        params.append(negocio_id)

        query = f"UPDATE negocios SET {', '.join(updates)} WHERE id = ?"
        
        cursor = conn.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Negocio no encontrado'}), 404
            
        return jsonify({'message': 'Negocio actualizado'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 5. OBTENER SERVICIOS DE UN NEGOCIO (ESTO ES LO NUEVO)
@negocios_bp.route('/<int:negocio_id>/servicios', methods=['GET'])
def obtener_servicios_negocio(negocio_id):
    conn = get_db_connection()
    try:
        # Obtenemos nombre e id de los servicios
        query = "SELECT id, nombre, duracion_minutos, precio FROM servicios WHERE negocio_id = ?"
        servicios = conn.execute(query, (negocio_id,)).fetchall()
        return jsonify([dict(row) for row in servicios])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 6. OBTENER HORARIOS DE UN NEGOCIO
@negocios_bp.route('/<int:negocio_id>/horarios', methods=['GET'])
def obtener_horarios_negocio(negocio_id):
    conn = get_db_connection()
    try:
        query = "SELECT dia_semana, hora_apertura, hora_cierre FROM horarios_negocio WHERE negocio_id = ? ORDER BY dia_semana, hora_apertura"
        horarios = conn.execute(query, (negocio_id,)).fetchall()
        return jsonify([dict(row) for row in horarios])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()