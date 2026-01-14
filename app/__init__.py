from flask import Flask, redirect, url_for
from config import Config
from .models import db, Usuario
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_talisman import Talisman 
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Configuración de zona horaria
    os.environ['TZ'] = 'America/Caracas'

    # Inicializar extensiones
    db.init_app(app)
    migrate = Migrate(app, db)

    # --- CONFIGURACIÓN DE SEGURIDAD (TALISMAN) ---
    # Se ajustó el CSP para permitir la ejecución de Tailwind y hardware de cámara
    Talisman(app, 
             force_https=True, 
             frame_options='DENY',
             content_security_policy={
                 'default-src': "'self'",
                 'script-src': [
                     "'self'",
                     "'unsafe-inline'", # Para tailwind.config y Dark Mode
                     "'unsafe-eval'"    # Para el procesador de video del QR
                 ],
                 'style-src': [
                     "'self'",
                     "'unsafe-inline'"  # Para tus animaciones y estilos internos
                 ],
                 'img-src': ["'self'", "data:", "blob:"],
                 'font-src': "'self'",  # YA NO NECESITA 'https://' EXTERNOS
                 'connect-src': "'self'",
                 'media-src': ["'self'", "blob:"] # Para la cámara
             })
             
    # --- CONFIGURACIÓN DE COOKIES SEGURAS ---
    app.config.update(
        SESSION_COOKIE_SECURE=False,   # True solo en Render
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )

    # Configuración de Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Debes iniciar sesión para ver esta página."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # --- REGISTRO DE BLUEPRINTS ---
    from .routes.auth_routes import auth_bp
    from .routes.admin_routes import admin_bp
    from .routes.student_routes import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)

    # --- RUTA RAÍZ ---
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app # <--- IMPORTANTE: Alineado con el inicio de la función