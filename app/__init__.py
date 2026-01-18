from flask import Flask, redirect, url_for, request
from config import Config
from .models import db, Usuario
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_talisman import Talisman 
from flask_wtf.csrf import CSRFProtect
import os

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'clave_secreta_sigau_pro_2026'

    os.environ['TZ'] = 'America/Caracas'

    db.init_app(app)
    migrate = Migrate(app, db)
    csrf.init_app(app)

    # --- CSP BLINDADO: SE ELIMINA 'unsafe-inline' ---
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            # Sin unsafe-eval
        ],
        'style-src': [
            "'self'",
            # SE ELIMINÓ 'unsafe-inline'. Ahora se usarán NONCES para seguridad.
            "https://cdnjs.cloudflare.com"
        ],
        'img-src': ["'self'", "data:", "blob:"],
        'font-src': ["'self'", "https://cdnjs.cloudflare.com", "data:"],
        'connect-src': "'self'",
        'media-src': ["'self'", "blob:", "data:"],
        'object-src': "'none'",      
        'frame-ancestors': "'none'", 
        'base-uri': "'self'",
        'form-action': "'self'"
    }

    # Aplicamos Talisman con Nonces para Script y Style
    Talisman(app, 
             force_https=True, 
             frame_options='DENY',
             content_security_policy=csp,
             # ESTA LÍNEA ES CLAVE: Habilita nonces para ambos tipos
             content_security_policy_nonce_in=['script-src', 'style-src'], 
             strict_transport_security=True,
             session_cookie_secure=True,
             session_cookie_http_only=True
    )
             
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )

    # --- CABECERAS PARA ELIMINAR BANDERAS DE CACHÉ Y DIVULGACIÓN ---
    @app.after_request
    def add_security_headers(response):
        # Elimina "Directivas de Control de Caché" (Bandera Azul ZAP)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        # Elimina "Divulgación de Información"
        response.headers["Server"] = "SIGAU-PRO"
        return response

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Debes iniciar sesión para ver esta página."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    from .routes.auth_routes import auth_bp
    from .routes.admin_routes import admin_bp
    from .routes.student_routes import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app