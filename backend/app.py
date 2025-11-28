import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from .routes.negocios import negocios_bp
from .routes.citas import citas_bp
from .routes.auth import auth_bp 

def create_app():
    app = Flask(__name__)
    CORS(app) 

    # Registrar Blueprints
    app.register_blueprint(negocios_bp)
    app.register_blueprint(citas_bp)
    app.register_blueprint(auth_bp)

    # Configuración de carpetas
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, '..', 'frontend')

    # Ruta Home
    @app.route('/')
    def serve_frontend():
        return send_from_directory(frontend_dir, 'index.html')

    # --- NUEVA RUTA: DETALLE DEL NEGOCIO ---
    @app.route('/negocio')
    def serve_negocio_page():
        return send_from_directory(frontend_dir, 'negocio.html')

    # Archivos estáticos
    @app.route('/<path:path>')
    def serve_static_files(path):
        return send_from_directory(frontend_dir, path)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)