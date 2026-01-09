from flask import Flask, redirect, url_for # <--- 1. AGREGAMOS ESTO
from config import Config
from .models import db, Usuario
from flask_login import LoginManager
from flask_migrate import Migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    import os
    os.environ['TZ'] = 'America/Caracas'

    # Inicializar extensiones
    db.init_app(app)
    migrate = Migrate(app, db)
    
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

    # --- RUTA RAÍZ (LA SOLUCIÓN AL 404) ---
    @app.route('/') # <--- 2. ESTA ES LA MAGIA
    def index():
        return redirect(url_for('auth.login')) # Te manda directo al login

  

    return app