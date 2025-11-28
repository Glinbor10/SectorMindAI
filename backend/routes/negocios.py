from flask import Blueprint, jsonify, request
import sqlite3
from ..db import get_db_connection 

negocios_bp = Blueprint('negocios', __name__, url_prefix='/negocios')

# LISTAR NEGOCIOS (Incluyendo nombre del propietario)
@negocios_bp.route('/', methods=['GET'])
def listar_negocios():
    conn = get_db_connection()
    # Hacemos JOIN para sacar el nombre del dueño
    query = """
        SELECT n.*, u.nombre as propietario_nombre 
        FROM negocios n 
        JOIN usuarios u ON n.propietario_id = u.id
    """
    negocios = conn.execute(query).fetchall()
    conn.close()
    return jsonify([dict(row) for row in negocios])

# CREAR NEGOCIO (Con descripción, foto y propietario)
@negocios_bp.route('/', methods=['POST'])
def crear_negocio():
    data = request.get_json()
    
    # Datos básicos
    nombre = data.get('nombre')
    tipo_negocio = data.get('tipo_negocio')
    propietario_id = data.get('propietario_id') # <--- OBLIGATORIO AHORA
    
    # Datos opcionales (Nuevos)
    direccion = data.get('direccion', 'Dirección no especificada')
    descripcion = data.get('descripcion', 'Sin descripción disponible.')
    foto_url = data.get('foto_url', '') # Si viene vacío, usaremos una por defecto en el front

    servicios = data.get('servicios', [])
    horarios = data.get('horarios', [])

    if not (nombre and tipo_negocio and propietario_id):
        return jsonify({'error': 'Faltan datos obligatorios (nombre, tipo, propietario_id)'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Insertar Negocio con los nuevos campos
        cur.execute(
            '''INSERT INTO negocios (nombre, tipo_negocio, direccion, descripcion, foto_url, propietario_id) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (nombre, tipo_negocio, direccion, descripcion, foto_url, propietario_id)
        )
        negocio_id = cur.lastrowid
        
        # Insertar Servicios
        for s in servicios:
            cur.execute(
                'INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (?, ?, ?, ?)',
                (negocio_id, s['nombre'], s['precio'], s['duracion_minutos'])
            )
            
        # Insertar Horarios
        for h in horarios:
            cur.execute(
                'INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (?, ?, ?, ?)',
                (negocio_id, h['dia_semana'], h['hora_apertura'], h['hora_cierre'])
            )

        conn.commit()
        return jsonify({'id': negocio_id, 'mensaje': 'Negocio creado con éxito'}), 201
        
    except sqlite3.IntegrityError as e:
        return jsonify({'error': f'Error de base de datos: {str(e)}'}), 400
    finally:
        conn.close()

# LISTAR SERVICIOS (Igual que antes)
@negocios_bp.route('/<int:negocio_id>/servicios', methods=['GET'])
def listar_servicios(negocio_id):
    conn = get_db_connection()
    servicios = conn.execute('SELECT * FROM servicios WHERE negocio_id = ?', (negocio_id,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in servicios])