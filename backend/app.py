import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- IMPORTACIONES DE BLUEPRINTS ---
from .routes.negocios import negocios_bp
from .routes.citas import citas_bp
from .routes.auth import auth_bp
from .routes.usuarios import usuarios_bp
from .db import init_app

def create_app():
    app = Flask(__name__)
    CORS(app) 

    # Configurar carpeta de uploads desde variable de entorno
    upload_folder = os.getenv('UPLOAD_FOLDER', os.path.join(
        os.path.dirname(__file__), 'frontend', 'uploads'
    ))
    app.config['UPLOAD_FOLDER'] = upload_folder
    
    # Crear carpeta si no existe
    os.makedirs(upload_folder, exist_ok=True)

    # Inicializar gestión de base de dato
    init_app(app)

    # --- REGISTRO DE BLUEPRINTS ---
    app.register_blueprint(negocios_bp)
    app.register_blueprint(citas_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp) 

    # Configuración de carpetas
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, '..', 'frontend')

    # Ruta Home
    @app.route('/')
    def serve_frontend():
        return send_from_directory(frontend_dir, 'index.html')

    # Ruta Detalle Negocio
    @app.route('/negocio')
    def serve_negocio_page():
        return send_from_directory(frontend_dir, 'negocio.html')
    
    # Ruta Perfil (Asegúrate de tener esta si quieres entrar directo a /perfil)
    @app.route('/perfil')
    def serve_perfil_page():
        return send_from_directory(frontend_dir, 'perfil.html')

    # Archivos estáticos
    @app.route('/<path:path>')
    def serve_static_files(path):
        return send_from_directory(frontend_dir, path)

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)