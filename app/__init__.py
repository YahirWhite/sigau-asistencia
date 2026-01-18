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

    # --- CONFIGURACIÓN DE SEGURIDAD MÁXIMA (SIN BLOQUEOS) ---
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-eval'"  # Requerido por la lógica del escáner QR (html5-qrcode)
        ],
        'style-src': [
            "'self'"         # ELIMINADO 'unsafe-inline'. Ahora solo confía en tus archivos locales.
        ],
        'img-src': ["'self'", "data:", "blob:"],
        'font-src': "'self'",
        'connect-src': "'self'",
        'media-src': ["'self'", "blob:"]
    }

    Talisman(app, 
             force_https=True, 
             frame_options='DENY',
             content_security_policy=csp,
             # Autoriza los scripts con nonce (tema oscuro, alertas flash, etc.)
             content_security_policy_nonce_in=['script-src']
    )
             
    # --- CONFIGURACIÓN DE COOKIES SEGURAS ---
    app.config.update(
        SESSION_COOKIE_SECURE=True,
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

    return app