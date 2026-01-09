from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

db = SQLAlchemy()

# Función auxiliar para hora de Venezuela
def obtener_hora_vzla():
    tz = pytz.timezone('America/Caracas')
    return datetime.now(tz)

# --- TABLA 1: USUARIOS (Estudiantes, Docentes, Admin) ---
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(20), nullable=False) # 'admin', 'docente', 'estudiante'
    telefono = db.Column(db.String(20), nullable=True) 
    aprobado = db.Column(db.Boolean, default=True)   
    ciudad = db.Column(db.String(50), nullable=True)
    semestre = db.Column(db.String(10), nullable=True) # "CAIU", "1", "2"...
    seccion_estudiante = db.Column(db.String(5), nullable=True) # "1", "24"..  

    # NOTA: Las relaciones (materias, asistencias, etc.) se definen automáticamente 
    # con los 'backref' en las otras tablas para evitar duplicados.

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- TABLA 2: SOLICITUDES DE RECUPERACIÓN ---
class SolicitudRecuperacion(db.Model):
    __tablename__ = 'solicitudes_recuperacion'
    
    id = db.Column(db.Integer, primary_key=True)
    # Corrección: Apunta a 'usuarios.id' (plural)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    fecha_solicitud = db.Column(db.DateTime, default=obtener_hora_vzla)
    nueva_clave_deseada = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(20), default='pendiente') # 'pendiente', 'aprobada'

    # Relación para saber de quién es la solicitud
    usuario = db.relationship('Usuario', backref='solicitudes')

# --- TABLA 3: MATERIAS ---
class Materia(db.Model):
    __tablename__ = 'materias'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    codigo_seccion = db.Column(db.String(50), nullable=False) 
    
    # Corrección: Apunta a 'usuarios.id'
    docente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    # Control de Asistencia y Tokens
    token_activo = db.Column(db.String(10), nullable=True)
    clase_iniciada = db.Column(db.Boolean, default=False)
    
    # Relación: Permite usar materia.docente
    docente = db.relationship('Usuario', backref='materias_asignadas')

# --- TABLA 4: INSCRIPCIONES ---
class Inscripcion(db.Model):
    __tablename__ = 'inscripciones'
    
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    materia_id = db.Column(db.Integer, db.ForeignKey('materias.id'), nullable=False)
    
    # Relaciones opcionales
    estudiante = db.relationship('Usuario', backref='inscripciones')
    materia = db.relationship('Materia', backref='inscritos')

# --- TABLA 5: ASISTENCIAS (CORREGIDA) ---
class Asistencia(db.Model):
    __tablename__ = 'asistencias'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=obtener_hora_vzla)
    # Guarda solo la fecha (año-mes-dia) para reportes rápidos
    fecha_solo_dia = db.Column(db.Date, default=lambda: obtener_hora_vzla().date())
    
    # Claves Foráneas (CORREGIDAS a plural)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    materia_id = db.Column(db.Integer, db.ForeignKey('materias.id'), nullable=False)
    
    estado = db.Column(db.String(20), nullable=False, default='presente') # 'presente', 'retraso'
    metodo = db.Column(db.String(20), default='qr') # 'qr', 'manual'

    # Relaciones: Permite usar asistencia.estudiante.nombre y asistencia.materia.nombre
    estudiante = db.relationship('Usuario', backref='asistencias')
    materia = db.relationship('Materia', backref='asistencias_registradas')

    # Optimización de búsqueda
    __table_args__ = (
        db.Index('idx_asistencia_busqueda', 'estudiante_id', 'materia_id'),
    )

class CatalogoMaterias(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

class Configuracion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    permitir_edicion = db.Column(db.Boolean, default=False) # False = Cerrado por defecto

class SolicitudClave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nueva_clave_hash = db.Column(db.String(200), nullable=False) # Guardamos la clave ya encriptada por seguridad
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación para saber quién pide el cambio
    usuario = db.relationship('Usuario', backref='solicitudes_clave')