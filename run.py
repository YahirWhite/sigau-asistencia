import os
import sys
import time

# --- CONFIGURACIÓN DE HORA VENEZUELA (CRÍTICO PARA RENDER) ---
os.environ['TZ'] = 'America/Caracas'
if sys.platform != "win32":
    time.tzset() # Configura la zona horaria en servidores Linux (como Render)
# -------------------------------------------------------------

# 1. Configuración de codificación para Windows (CRÍTICO)
os.environ["PGMESSAGES"] = "C"
os.environ["PGCLIENTENCODING"] = "utf-8"

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Solo una llamada a run. 
    # host='0.0.0.0' es para que puedas escanear el QR desde tu celular real.
    app.run(debug=True, host='0.0.0.0', port=5000)