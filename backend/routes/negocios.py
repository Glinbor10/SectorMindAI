from flask import Blueprint, jsonify, request
import sqlite3
from ..db import get_db_connection 

negocios_bp = Blueprint('negocios', __name__, url_prefix='/negocios')

# LISTAR NEGOCIOS (Con filtro opcional por propietario)
@negocios_bp.route('/', methods=['GET'])
def listar_negocios():
    propietario_id = request.args.get('propietario_id') # Capturamos el filtro de la URL
    
    conn = get_db_connection()
    query = """
        SELECT n.*, u.nombre as propietario_nombre 
        FROM negocios n 
        JOIN usuarios u ON n.propietario_id = u.id
    """
    params = []
    
    # Si viene el parámetro, filtramos
    if propietario_id:
        query += " WHERE n.propietario_id = ?"
        params.append(propietario_id)
        
    negocios = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in negocios])

# CREAR NEGOCIO
@negocios_bp.route('/', methods=['POST'])
def crear_negocio():
    data = request.get_json()
    
    nombre = data.get('nombre')
    tipo_negocio = data.get('tipo_negocio')
    propietario_id = data.get('propietario_id')
    direccion = data.get('direccion', 'Dirección no especificada')
    descripcion = data.get('descripcion', 'Sin descripción.')
    foto_url = data.get('foto_url', '')

    if not (nombre and tipo_negocio and propietario_id):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            '''INSERT INTO negocios (nombre, tipo_negocio, direccion, descripcion, foto_url, propietario_id) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (nombre, tipo_negocio, direccion, descripcion, foto_url, propietario_id)
        )
        negocio_id = cur.lastrowid
        
        # Insertar horarios por defecto (L-V 9-18) para no dejarlo vacío
        for dia in range(5):
            cur.execute('INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (?, ?, ?, ?)',
                        (negocio_id, dia, '09:00:00', '18:00:00'))

        conn.commit()
        return jsonify({'id': negocio_id, 'mensaje': 'Negocio creado'}), 201
    except Exception as e:
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

# AÑADIR SERVICIO (NUEVO)
@negocios_bp.route('/<int:negocio_id>/servicios', methods=['POST'])
def agregar_servicio(negocio_id):
    data = request.get_json()
    nombre = data.get('nombre')
    precio = data.get('precio')
    duracion = data.get('duracion') # en minutos

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