import os
from flask import Flask, send_from_directory
from flask_cors import CORS

# --- IMPORTACIONES DE BLUEPRINTS ---
from .routes.negocios import negocios_bp
from .routes.citas import citas_bp
from .routes.auth import auth_bp
from .routes.usuarios import usuarios_bp
from .db import init_app

def create_app():
    app = Flask(__name__)
    CORS(app) 

    # Inicializar gestión de base de dato
    init_app(app)

    # --- REGISTRO DE BLUEPRINTS ---
    app.register_blueprint(negocios_bp)
    app.register_blueprint(citas_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)   # <--- 2. AÑADE ESTA LÍNEA

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
    app.run(debug=True)