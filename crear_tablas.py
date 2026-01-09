import sys
import io

# Forzamos a que la salida de la consola sea UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
os.environ["PGCLIENTENCODING"] = "utf-8"

from app import create_app, db
# ... el resto de tus imports y el código de app.app_context() ...
# Importamos los modelos
from app.models import Usuario, Materia, Asistencia, Configuracion, SolicitudClave

app = create_app()

with app.app_context():
    print("--- Conectando a PostgreSQL ---")
    print(f"Usando base de datos: {app.config['SQLALCHEMY_DATABASE_URI']}") # Para verificar que lea el .env
    
    try:
        # Crea las tablas vacias
        db.create_all()
        print("--- EXITO: Tablas creadas correctamente ---")
        print("NOTA: La base de datos esta vacia.")
        print("PASO SIGUIENTE: Registrate en la web y modifica tu rol manualmente en pgAdmin.")
        
    except Exception as e:
        print("\n❌ ERROR REAL DE CONEXIÓN:")
        print(e)
        print("\nSi dice 'password authentication failed', verifica tu clave en pgAdmin de nuevo.")