import os
import uuid
import sqlite3
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from ..db import get_db_connection

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# REGISTRO CON FOTO Y AUTO-LOGIN
@auth_bp.route('/register', methods=['POST'])
def register():
    # Al usar FormData, los datos vienen en request.form y request.files
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    password = request.form.get('password')
    rol = request.form.get('rol')
    archivo = request.files.get('foto_perfil') # Campo del archivo

    if not (nombre and email and password and rol):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    hashed_password = generate_password_hash(password)
    foto_url = None

    # Lógica de guardado de imagen
    if archivo and archivo.filename != '':
        if allowed_file(archivo.filename):
            ext = archivo.filename.rsplit('.', 1)[1].lower()
            filename = f"user_{uuid.uuid4().hex[:8]}.{ext}"
            
            # Ruta absoluta a frontend/uploads
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            upload_folder = os.path.join(base_dir, 'frontend', 'uploads')
            
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            filepath = os.path.join(upload_folder, filename)
            archivo.save(filepath)
            
            foto_url = f"/uploads/{filename}"

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO usuarios (nombre, email, password_hash, rol, foto_perfil_url) 
               VALUES (?, ?, ?, ?, ?)''',
            (nombre, email, hashed_password, rol, foto_url)
        )
        conn.commit()
        
        # OBTENER EL ID DEL NUEVO USUARIO PARA EL AUTO-LOGIN
        new_user_id = cursor.lastrowid
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'El email ya está registrado'}), 409
    finally:
        conn.close()

    # Devolvemos TODOS los datos para que el frontend inicie sesión solo
    return jsonify({
        'message': 'Registro exitoso',
        'id': new_user_id,
        'nombre': nombre,
        'email': email,
        'rol': rol,
        'foto_perfil_url': foto_url
    }), 201

# LOGIN (Se mantiene igual, solo asegúrate de que esté)
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not (email and password):
        return jsonify({'error': 'Faltan credenciales'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
    conn.close()

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