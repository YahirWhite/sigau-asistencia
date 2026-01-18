from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, Usuario, SolicitudClave
from werkzeug.security import generate_password_hash 

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# --- 1. LOGIN (Protegido por CSRF) ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si el usuario ya está dentro, lo mandamos a donde le toca
    if current_user.is_authenticated:
        return redirigir_por_rol(current_user.rol)

    if request.method == 'POST':
        cedula = request.form.get('cedula')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(cedula=cedula).first()
        
        # Validación: Comprobar existencia y contraseña usando el método del modelo
        if usuario and usuario.check_password(password):
            # Verificar aprobación (Docentes necesitan visto bueno del Admin)
            if not usuario.aprobado:
                flash('🔒 Tu cuenta está pendiente de aprobación por el Administrador.', 'warning')
                return render_template('auth/login.html')
            
            login_user(usuario)
            return redirigir_por_rol(usuario.rol)
        else:
            # Mensaje genérico para evitar enumeración de usuarios
            flash('Cédula o contraseña incorrecta', 'danger')
            
    return render_template('auth/login.html')

# --- 2. REGISTRO (Con validaciones de integridad) ---
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirigir_por_rol(current_user.rol)

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        cedula = request.form.get('cedula')
        telefono = request.form.get('telefono')
        ciudad = request.form.get('ciudad')
        password = request.form.get('password')
        rol = request.form.get('rol')
        
        # Datos específicos para estudiantes
        semestre = request.form.get('semestre') if rol == 'estudiante' else None
        seccion_est = request.form.get('seccion_estudiante') if rol == 'estudiante' else None

        # --- VALIDACIONES DE CIBERSEGURIDAD ---
        if not cedula or len(cedula) < 6 or len(cedula) > 9:
            flash('La cédula debe tener entre 6 y 9 dígitos.', 'danger')
            return redirect(url_for('auth.register'))
        
        if not telefono or len(telefono) != 11:
            flash('El teléfono debe tener exactamente 11 dígitos.', 'danger')
            return redirect(url_for('auth.register'))

        if Usuario.query.filter_by(cedula=cedula).first():
            flash('Esa cédula ya está registrada en el sistema.', 'danger')
            return redirect(url_for('auth.register'))

        # Lógica de aprobación: Estudiantes entran directo, docentes esperan
        esta_aprobado = True if rol == 'estudiante' else False
        
        nuevo_usuario = Usuario(
            nombre=nombre, 
            cedula=cedula, 
            telefono=telefono,
            ciudad=ciudad, 
            rol=rol, 
            aprobado=esta_aprobado,
            semestre=semestre, 
            seccion_estudiante=seccion_est
        )
        nuevo_usuario.set_password(password)
        
        db.session.add(nuevo_usuario)
        db.session.commit()

        if rol == 'docente':
            flash('✅ Registro exitoso. Espera a que el Administrador apruebe tu acceso.', 'info')
        else:
            flash('¡Cuenta creada con éxito! Ya puedes iniciar sesión.', 'success')
            
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

# --- 3. LOGOUT ---
@auth_bp.route('/logout')
@login_required 
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))

# --- 4. RECUPERAR CONTRASEÑA ---
@auth_bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        cedula = request.form.get('cedula')
        nueva_clave = request.form.get('nueva_clave')
        
        usuario = Usuario.query.filter_by(cedula=cedula).first()
        
        if not usuario:
            flash('No existe ningún usuario con esa cédula.', 'danger')
        else:
            # Evitar duplicidad de solicitudes
            pendiente = SolicitudClave.query.filter_by(usuario_id=usuario.id).first()
            if pendiente:
                flash('Ya tienes una solicitud de clave en espera de aprobación.', 'warning')
            else:
                hashed_pw = generate_password_hash(nueva_clave)
                nueva_solicitud = SolicitudClave(
                    usuario_id=usuario.id, 
                    nueva_clave_hash=hashed_pw
                )
                
                db.session.add(nueva_solicitud)
                db.session.commit()
                flash('✅ Solicitud enviada al Administrador con éxito.', 'success')
                return redirect(url_for('auth.login'))
                
    return render_template('auth/recuperar.html')

# --- 5. REDIRECCIÓN POR ROL (Utilidad Interna) ---
def redirigir_por_rol(rol):
    if rol in ['admin', 'docente']:
        return redirect(url_for('admin.dashboard'))
    elif rol == 'estudiante':
        return redirect(url_for('student.escaner'))
    return redirect(url_for('auth.login'))