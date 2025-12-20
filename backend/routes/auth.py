# backend/routes/auth.py
# filepath: backend/routes/auth.py
import os
import uuid
from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from ..db import get_db_connection
from ..db_utils import adapt_query

load_dotenv()

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@auth_bp.route('/register', methods=['POST'])
def register():
    """Registro con soporte de foto de perfil (PostgreSQL)."""
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    password = request.form.get('password')
    rol = request.form.get('rol')
    archivo = request.files.get('foto_perfil')

    if not (nombre and email and password and rol):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    hashed_password = generate_password_hash(password)
    foto_url = None

    # Procesamiento de foto
    if archivo and archivo.filename != '':
        if allowed_file(archivo.filename):
            ext = archivo.filename.rsplit('.', 1)[1].lower()
            filename = f"user_{uuid.uuid4().hex[:8]}.{ext}"
            
            upload_folder = current_app.config.get('UPLOAD_FOLDER') or os.getenv('UPLOAD_FOLDER', '/app/uploads')
            os.makedirs(upload_folder, exist_ok=True)
            
            filepath = os.path.join(upload_folder, filename)
            archivo.save(filepath)
            foto_url = f"/uploads/{filename}"

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 🔧 PostgreSQL EXCLUSIVAMENTE
        cursor.execute(
            adapt_query('''
                INSERT INTO usuarios (nombre, email, password_hash, rol, foto_perfil_url) 
                VALUES (%s, %s, %s, %s, %s) 
                RETURNING id
            '''),
            (nombre, email, hashed_password, rol, foto_url)
        )
        new_user_id = cursor.fetchone()['id']
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            return jsonify({'error': 'El email ya está registrado'}), 409
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

    return jsonify({
        'message': 'Registro exitoso',
        'id': new_user_id,
        'nombre': nombre,
        'email': email,
        'rol': rol,
        'foto_perfil_url': foto_url
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login con PostgreSQL."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not (email and password):
        return jsonify({'error': 'Faltan credenciales'}), 400

    conn = get_db_connection()
    try:
        user = conn.execute(
            'SELECT * FROM usuarios WHERE email = %s',
            (email,)
        ).fetchone()
        
        if user is None or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        return jsonify({
            'message': 'Login exitoso',
            'id': user['id'],
            'nombre': user['nombre'],
            'email': user['email'],
            'rol': user['rol'],
            'foto_perfil_url': user['foto_perfil_url']
        }), 200
        
    finally:
        conn.close()