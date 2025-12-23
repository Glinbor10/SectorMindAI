from flask import Blueprint, jsonify, request, current_app
from ..db import get_db_connection
from ..db_utils import adapt_query
import os
import uuid 

negocios_bp = Blueprint('negocios', __name__, url_prefix='/negocios')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        try:
            propietario_id = int(propietario_id)
        except ValueError:
            return jsonify({'error': 'propietario_id inválido'}), 400
        query += " WHERE n.propietario_id = %s"
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
        WHERE n.id = %s
    """
    negocio = conn.execute(query, (negocio_id,)).fetchone()
    conn.close()
    
    if negocio is None:
        return jsonify({'error': 'Negocio no encontrado'}), 404
        
    return jsonify(dict(negocio))

# 3. CREAR NEGOCIO
@negocios_bp.route('/', methods=['POST'])
def crear_negocio():
    print(f"DEBUG: Content-Type recibido: {request.content_type}")
    print(f"DEBUG: Method: {request.method}")
    print(f"DEBUG: Form keys: {list(request.form.keys()) if request.form else 'None'}")
    print(f"DEBUG: Files keys: {list(request.files.keys()) if request.files else 'None'}")

    # Determinar si es FormData o JSON
    is_form_data = request.content_type and (
        'multipart/form-data' in request.content_type or 
        'application/x-www-form-urlencoded' in request.content_type
    )
    
    if is_form_data:
        print("DEBUG: Detectado como FormData")
        # FormData (con posible archivo)
        nombre = request.form.get('nombre')
        tipo_negocio = request.form.get('tipo_negocio', 'general')
        direccion = request.form.get('direccion')
        descripcion = request.form.get('descripcion')
        propietario_id = request.form.get('propietario_id')
        archivo = request.files.get('foto')
        print(f"DEBUG: FormData - nombre: {nombre}, propietario_id: {propietario_id}, archivo: {archivo.filename if archivo else 'None'}")
    else:
        print("DEBUG: Detectado como JSON")
        # JSON (compatibilidad hacia atrás)
        data = request.get_json()
        nombre = data.get('nombre')
        tipo_negocio = data.get('tipo_negocio', 'general')
        direccion = data.get('direccion')
        descripcion = data.get('descripcion')
        foto_url = data.get('foto_url')
        propietario_id = data.get('propietario_id')
        archivo = None
        print(f"DEBUG: JSON - data: {data}")

    if not (nombre and direccion and propietario_id):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    # Convertir propietario_id a int
    try:
        propietario_id = int(propietario_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'propietario_id inválido'}), 400

    foto_url = None

    # Procesar archivo si viene (solo en FormData)
    if archivo and archivo.filename != '':
        if allowed_file(archivo.filename):
            # Generar nombre único para evitar colisiones
            ext = archivo.filename.rsplit('.', 1)[1].lower()
            filename = f"business_{uuid.uuid4().hex[:8]}.{ext}"

            # Usar carpeta de uploads configurada
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            if not upload_folder:
                # Fallback por si no está configurada
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                upload_folder = os.path.join(base_dir, 'frontend', 'uploads')

            # Crear carpeta si no existe
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            # Guardar el archivo físicamente
            filepath = os.path.join(upload_folder, filename)
            archivo.save(filepath)

            # Guardar la URL RELATIVA en la BD
            foto_url = f"/uploads/{filename}"
        else:
            return jsonify({'error': 'Tipo de archivo no permitido (solo jpg, png, gif)'}), 400
    elif not archivo and 'foto_url' in locals() and foto_url:
        # Si viene foto_url en JSON, usarla directamente
        pass  # foto_url ya está asignada

    conn = get_db_connection()
    try:
        # PostgreSQL EXCLUSIVAMENTE
        cursor = conn.execute(
            adapt_query('INSERT INTO negocios (nombre, tipo_negocio, direccion, descripcion, foto_url, propietario_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id'),
            (nombre, tipo_negocio, direccion, descripcion, foto_url, propietario_id)
        )
        new_id = cursor.fetchone()['id']
        conn.commit()
        return jsonify({'id': new_id, 'message': 'Negocio creado exitosamente'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 4. ACTUALIZAR NEGOCIO
@negocios_bp.route('/<int:negocio_id>', methods=['PUT'])
def actualizar_negocio(negocio_id):
    data = request.get_json()
    
    nombre = data.get('nombre')
    descripcion = data.get('descripcion')
    foto_url = data.get('foto_url')
    direccion = data.get('direccion')

    if not any([nombre, descripcion, foto_url, direccion]):
         return jsonify({'error': 'No hay datos para actualizar'}), 400

    conn = get_db_connection()
    try:
        updates = []
        params = []

        if nombre is not None:
            updates.append("nombre = %s")
            params.append(nombre)
        if descripcion is not None:
            updates.append("descripcion = %s")
            params.append(descripcion)
        if foto_url is not None:
            updates.append("foto_url = %s")
            params.append(foto_url)
        if direccion is not None:
            updates.append("direccion = %s")
            params.append(direccion)

        params.append(negocio_id)

        query = f"UPDATE negocios SET {', '.join(updates)} WHERE id = %s"
        
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
        query = "SELECT id, nombre, duracion_minutos, precio FROM servicios WHERE negocio_id = %s"
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
        query = "SELECT dia_semana, hora_apertura, hora_cierre FROM horarios_negocio WHERE negocio_id = %s ORDER BY dia_semana, hora_apertura"
        horarios = conn.execute(query, (negocio_id,)).fetchall()
        # Convertir time objects a strings para PostgreSQL
        result = []
        for row in horarios:
            horario_dict = dict(row)
            if 'hora_apertura' in horario_dict:
                horario_dict['hora_apertura'] = str(horario_dict['hora_apertura'])
            if 'hora_cierre' in horario_dict:
                horario_dict['hora_cierre'] = str(horario_dict['hora_cierre'])
            result.append(horario_dict)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 7. CREAR SERVICIO PARA UN NEGOCIO
@negocios_bp.route('/<int:negocio_id>/servicios', methods=['POST'])
def crear_servicio(negocio_id):
    data = request.get_json()
    nombre = data.get('nombre')
    precio = data.get('precio')
    duracion_minutos = data.get('duracion_minutos')
    propietario_id = data.get('propietario_id')  # Para verificar permisos

    if not (nombre and precio is not None and duracion_minutos):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    try:
        propietario_id = int(propietario_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'propietario_id inválido'}), 400

    conn = get_db_connection()
    try:
        # Verificar que el negocio pertenece al propietario
        negocio = conn.execute("SELECT propietario_id FROM negocios WHERE id = %s", (negocio_id,)).fetchone()
        if not negocio or negocio['propietario_id'] != propietario_id:
            return jsonify({'error': 'No tienes permisos para este negocio'}), 403

        cursor = conn.execute(
            adapt_query('INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s) RETURNING id'),
            (negocio_id, nombre, precio, duracion_minutos)
        )
        new_id = cursor.fetchone()['id']
        conn.commit()
        return jsonify({'id': new_id, 'message': 'Servicio creado exitosamente'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 8. ACTUALIZAR SERVICIO
@negocios_bp.route('/<int:negocio_id>/servicios/<int:servicio_id>', methods=['PUT'])
def actualizar_servicio(negocio_id, servicio_id):
    data = request.get_json()
    nombre = data.get('nombre')
    precio = data.get('precio')
    duracion_minutos = data.get('duracion_minutos')
    propietario_id = data.get('propietario_id')

    if not any([nombre, precio is not None, duracion_minutos]):
        return jsonify({'error': 'No hay datos para actualizar'}), 400

    try:
        propietario_id = int(propietario_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'propietario_id inválido'}), 400

    conn = get_db_connection()
    try:
        # Verificar permisos
        negocio = conn.execute("SELECT propietario_id FROM negocios WHERE id = %s", (negocio_id,)).fetchone()
        if not negocio or negocio['propietario_id'] != propietario_id:
            return jsonify({'error': 'No tienes permisos para este negocio'}), 403

        # Verificar que el servicio pertenece al negocio
        servicio = conn.execute("SELECT id FROM servicios WHERE id = %s AND negocio_id = %s", (servicio_id, negocio_id)).fetchone()
        if not servicio:
            return jsonify({'error': 'Servicio no encontrado'}), 404

        updates = []
        params = []
        if nombre is not None:
            updates.append("nombre = %s")
            params.append(nombre)
        if precio is not None:
            updates.append("precio = %s")
            params.append(precio)
        if duracion_minutos is not None:
            updates.append("duracion_minutos = %s")
            params.append(duracion_minutos)

        params.append(servicio_id)
        query = f"UPDATE servicios SET {', '.join(updates)} WHERE id = %s"
        cursor = conn.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Servicio no encontrado'}), 404

        return jsonify({'message': 'Servicio actualizado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 9. ELIMINAR SERVICIO
@negocios_bp.route('/<int:negocio_id>/servicios/<int:servicio_id>', methods=['DELETE'])
def eliminar_servicio(negocio_id, servicio_id):
    propietario_id = request.args.get('propietario_id')

    if not propietario_id:
        return jsonify({'error': 'Falta propietario_id'}), 400

    try:
        propietario_id = int(propietario_id)
    except ValueError:
        return jsonify({'error': 'propietario_id inválido'}), 400

    conn = get_db_connection()
    try:
        # Verificar permisos
        negocio = conn.execute("SELECT propietario_id FROM negocios WHERE id = %s", (negocio_id,)).fetchone()
        if not negocio or negocio['propietario_id'] != propietario_id:
            return jsonify({'error': 'No tienes permisos para este negocio'}), 403

        # Verificar que el servicio pertenece al negocio
        servicio = conn.execute("SELECT id FROM servicios WHERE id = %s AND negocio_id = %s", (servicio_id, negocio_id)).fetchone()
        if not servicio:
            return jsonify({'error': 'Servicio no encontrado'}), 404

        cursor = conn.execute("DELETE FROM servicios WHERE id = %s", (servicio_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Servicio no encontrado'}), 404

        return jsonify({'message': 'Servicio eliminado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 10. ELIMINAR NEGOCIO
@negocios_bp.route('/<int:negocio_id>', methods=['DELETE'])
def eliminar_negocio(negocio_id):
    propietario_id = request.args.get('propietario_id')

    if not propietario_id:
        return jsonify({'error': 'Falta propietario_id'}), 400

    try:
        propietario_id = int(propietario_id)
    except ValueError:
        return jsonify({'error': 'propietario_id inválido'}), 400

    conn = get_db_connection()
    try:
        # Verificar si el negocio existe
        negocio = conn.execute("SELECT propietario_id, foto_url FROM negocios WHERE id = %s", (negocio_id,)).fetchone()
        if not negocio:
            return jsonify({'error': 'Negocio no encontrado'}), 404
            
        # Verificar permisos
        if negocio['propietario_id'] != propietario_id:
            return jsonify({'error': 'No tienes permisos para este negocio'}), 403

        # Si el negocio tiene una foto, eliminarla del sistema de archivos
        if negocio['foto_url'] and negocio['foto_url'].startswith('/uploads/'):
            filename = negocio['foto_url'].replace('/uploads/', '')
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            if upload_folder:
                filepath = os.path.join(upload_folder, filename)
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    print(f"WARNING: Error al eliminar foto {filepath}: {e}")
                    # No fallar la eliminación del negocio si no se puede eliminar la foto

        # Eliminar el negocio (las tablas relacionadas se eliminarán automáticamente por CASCADE)
        cursor = conn.execute("DELETE FROM negocios WHERE id = %s", (negocio_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Negocio no encontrado'}), 404

        return jsonify({'message': 'Negocio eliminado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()