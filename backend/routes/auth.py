from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from ..db import get_db_connection
import sqlite3

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# REGISTRO
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    nombre = data.get('nombre')
    email = data.get('email')
    password = data.get('password')
    rol = data.get('rol') # 'cliente' o 'propietario'

    if not (nombre and email and password and rol):
        return jsonify({'error': 'Faltan datos'}), 400

    # Encriptamos la contraseña
    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)',
            (nombre, email, hashed_password, rol)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': 'El email ya está registrado'}), 409
    finally:
        conn.close()

    return jsonify({'message': 'Usuario registrado correctamente'}), 201

# LOGIN
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

    if user is None:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    # Verificar contraseña encriptada
    if not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Contraseña incorrecta'}), 401

    # Login exitoso: Devolvemos los datos del usuario (sin el password)
    return jsonify({
        'id': user['id'],
        'nombre': user['nombre'],
        'email': user['email'],
        'rol': user['rol']
    }), 200