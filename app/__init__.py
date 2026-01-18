from flask import Flask, redirect, url_for
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

    # --- CONFIGURACIÓN CSP PARA ELIMINAR BANDERAS NARANJAS ---
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            # Sin unsafe-eval: Ahora usamos jsQR localmente
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'", # Necesario para Tailwind y animaciones dinámicas
            "https://cdnjs.cloudflare.com" # Si usas FontAwesome externo
        ],
        'img-src': ["'self'", "data:", "blob:"],
        'font-src': ["'self'", "https://cdnjs.cloudflare.com", "data:"],
        'connect-src': "'self'",
        'media-src': ["'self'", "blob:", "data:"],
        # DIRECTIVAS CRÍTICAS PARA ZAP:
        'object-src': "'none'",      # Bloquea inyección de plugins (Flash, etc.)
        'frame-ancestors': "'none'"  # Evita ataques de Clickjacking (Iframe)
    }

    # Aplicamos Talisman con HSTS activado
    Talisman(app, 
             force_https=True, 
             frame_options='DENY',
             content_security_policy=csp,
             content_security_policy_nonce_in=['script-src'],
             strict_transport_security=True # Indica al navegador que use siempre HTTPS
    )
             
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )

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