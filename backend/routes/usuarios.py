import os
import uuid
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename
from ..db import get_db_connection

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')

# EXTENSIONES PERMITIDAS
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 1. OBTENER DATOS (GET) - Se mantiene igual
@usuarios_bp.route('/<int:user_id>', methods=['GET'])
def obtener_usuario(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT id, nombre, email, rol, foto_perfil_base64 FROM usuarios WHERE id = %s', (user_id,)).fetchone()
    conn.close()
    if user is None:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify(dict(user))

# 2. ACTUALIZAR PERFIL CON SUBIDA DE ARCHIVO (PUT)
@usuarios_bp.route('/<int:user_id>', methods=['PUT'])
def actualizar_usuario(user_id):
    # NOTA: Al usar FormData en el frontend, los datos de texto vienen en request.form
    # y los archivos en request.files
    
    nombre = request.form.get('nombre')
    archivo = request.files.get('foto_perfil') # El nombre del campo en el HTML
    import base64

    conn = get_db_connection()
    try:
        updates = []
        params = []

        # 1. Actualizar Nombre si viene
        if nombre:
            updates.append('nombre = %s')
            params.append(nombre)

        # 2. Procesar Archivo si viene
        if archivo and archivo.filename != '':
            if allowed_file(archivo.filename):
                ext = archivo.filename.rsplit('.', 1)[1].lower()
                file_bytes = archivo.read()
                foto_base64 = f"data:image/{ext};base64," + base64.b64encode(file_bytes).decode('utf-8')
                updates.append('foto_perfil_base64 = %s')
                params.append(foto_base64)
            else:
                return jsonify({'error': 'Tipo de archivo no permitido (solo jpg, png, gif)'}), 400

        if not updates:
            return jsonify({'error': 'No hay datos para actualizar'}), 400

        params.append(user_id)
        
        query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = %s"
        result = conn.execute(query, params)
        conn.commit()
        
        # Verificar que el usuario existe
        if result.rowcount == 0:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Devolver usuario actualizado
        updated_user = conn.execute('SELECT id, nombre, email, rol, foto_perfil_base64 FROM usuarios WHERE id = %s', (user_id,)).fetchone()
        return jsonify(dict(updated_user)), 200

    except Exception as e:
        print(f"ERROR: {e}") # Para ver el error en la terminal
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        conn.close()