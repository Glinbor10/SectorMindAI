from flask import Blueprint, jsonify, request
import sqlite3
from ..db import get_db_connection 

negocios_bp = Blueprint('negocios', __name__, url_prefix='/negocios')

# LISTAR NEGOCIOS (Con filtro opcional por propietario)
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

# OBTENER UN SOLO NEGOCIO POR ID (GET /negocios/1)
@negocios_bp.route('/<int:negocio_id>', methods=['GET'])
def obtener_negocio(negocio_id):
    conn = get_db_connection()
    # Hacemos JOIN para saber el nombre del dueño también
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

# CREAR NEGOCIO (CORREGIDO: Ahora guarda servicios y horarios)
@negocios_bp.route('/', methods=['POST'])
def crear_negocio():
    data = request.get_json()
    
    # Datos del Negocio
    nombre = data.get('nombre')
    tipo_negocio = data.get('tipo_negocio')
    propietario_id = data.get('propietario_id')
    direccion = data.get('direccion', 'Dirección no especificada')
    descripcion = data.get('descripcion', 'Sin descripción.')
    foto_url = data.get('foto_url', '')
    
    # Datos de Listas (Lo que faltaba)
    servicios = data.get('servicios', [])
    horarios = data.get('horarios', [])

    if not (nombre and tipo_negocio and propietario_id):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # 1. Insertar el Negocio
        cur.execute(
            '''INSERT INTO negocios (nombre, tipo_negocio, direccion, descripcion, foto_url, propietario_id) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (nombre, tipo_negocio, direccion, descripcion, foto_url, propietario_id)
        )
        negocio_id = cur.lastrowid
        
        # 2. Insertar Servicios (RECUPERADO)
        for s in servicios:
            cur.execute(
                'INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (?, ?, ?, ?)',
                (negocio_id, s['nombre'], s['precio'], s['duracion_minutos'])
            )

        # 3. Insertar Horarios (RECUPERADO)
        if horarios:
            for h in horarios:
                cur.execute(
                    'INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (?, ?, ?, ?)',
                    (negocio_id, h['dia_semana'], h['hora_apertura'], h['hora_cierre'])
                )
        else:
            # Si no envían horarios, ponemos uno por defecto (L-V 9-18)
            for dia in range(5):
                cur.execute('INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (?, ?, ?, ?)',
                            (negocio_id, dia, '09:00:00', '18:00:00'))

        conn.commit()
        return jsonify({'id': negocio_id, 'mensaje': 'Negocio creado con servicios y horarios'}), 201
    except Exception as e:
        conn.rollback() # Deshacer si falla algo a medias
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# LISTAR SERVICIOS
@negocios_bp.route('/<int:negocio_id>/servicios', methods=['GET'])
def listar_servicios(negocio_id):
    conn = get_db_connection()
    servicios = conn.execute('SELECT * FROM servicios WHERE negocio_id = ?', (negocio_id,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in servicios])

# AÑADIR SERVICIO MANUALMENTE
@negocios_bp.route('/<int:negocio_id>/servicios', methods=['POST'])
def agregar_servicio(negocio_id):
    data = request.get_json()
    nombre = data.get('nombre')
    precio = data.get('precio')
    duracion = data.get('duracion')

    if not (nombre and precio and duracion):
        return jsonify({'error': 'Faltan datos del servicio'}), 400

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (?, ?, ?, ?)',
                     (negocio_id, nombre, precio, duracion))
        conn.commit()
        return jsonify({'mensaje': 'Servicio añadido correctamente'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# AÑADIR AL FINAL: ACTUALIZAR NEGOCIO (PUT)
@negocios_bp.route('/<int:negocio_id>', methods=['PUT'])
def actualizar_negocio(negocio_id):
    data = request.get_json()
    
    # Campos permitidos para actualizar
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
            
        return jsonify({'message': 'Negocio actualizado correctamente'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()