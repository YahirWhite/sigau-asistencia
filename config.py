import os
from dotenv import load_dotenv

# Carga las claves del archivo .env
load_dotenv()

class Config:
    # Clave secreta para seguridad de formularios y cookies
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-dev-super-secreta'
    
    # Conexión a Base de Datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de Zona Horaria (Venezuela)
    TIMEZONE = 'America/Caracas'
    
    # Optimización: Pool de conexiones para soportar 1500 usuarios
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,       # 20 conexiones fijas
        'max_overflow': 40,    # 40 extra en picos
        'pool_timeout': 30,    # 30s de espera
        'pool_recycle': 1800   # Reiniciar conexión cada 30min
    }