from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, Asistencia, Materia, Configuracion
from datetime import datetime

student_bp = Blueprint('student', __name__, url_prefix='/student')

# --- 1. ESCÁNER (Vista Principal) ---
@student_bp.route('/escaner')
@login_required
def escaner():
    if current_user.rol != 'estudiante':
        return redirect(url_for('admin.dashboard'))
    
    # Verificamos si hay inscripciones abiertas para mostrar una alerta visual
    config = Configuracion.query.first()
    inscripciones_abiertas = config.permitir_edicion if config else False

    return render_template('student/escaner.html', inscripciones_abiertas=inscripciones_abiertas)

# --- 2. PROCESAR QR (BLINDADO) ---
@student_bp.route('/procesar_qr', methods=['POST'])
@login_required
def procesar_qr():
    token = request.form.get('token')
    
    # --- 0. SEGURIDAD CRÍTICA ---
    # Verificar que el token no venga vacío o nulo
    if not token:
        flash('❌ Error: No se leyó ningún código. Intenta escanear de nuevo.', 'danger')
        return redirect(url_for('student.escaner'))

    # 1. Buscar materia con ese token activo
    # NOTA: Cuando el profesor cierra la clase, pone el token en NULL.
    # Por lo tanto, si el alumno usa un token viejo, esta búsqueda dará "None"
    # y entrará en el 'if not materia' de abajo, bloqueando el paso.
    materia = Materia.query.filter_by(token_activo=token).first()
    
    if not materia:
        # AQUÍ ES DONDE REBOTA AL TRAMPOSO
        flash('⛔ El código QR ya expiró o la clase ha sido cerrada por el profesor.', 'danger')
        return redirect(url_for('student.escaner'))

    # --- VALIDACIÓN DE SEGURIDAD DE SECCIÓN ---
    
    # A. Verificar si el estudiante configuró su perfil
    if not current_user.seccion_estudiante:
        flash('⚠️ Debes configurar tu Sección en el Perfil antes de marcar asistencia.', 'warning')
        return redirect(url_for('student.escaner'))

    # B. Comparar Sección del Alumno vs Sección de la Materia
    sec_alumno = str(current_user.seccion_estudiante).strip().upper()
    sec_materia = str(materia.codigo_seccion).strip().upper()

    if sec_alumno != sec_materia:
        flash(f'⛔ ACCESO DENEGADO: Tú eres de la Sección "{sec_alumno}" y esta clase es de la Sección "{sec_materia}".', 'danger')
        return redirect(url_for('student.escaner'))

    # ------------------------------------------

    # 2. Verificar si ya marcó hoy
    hoy = datetime.now().date()
    existe = Asistencia.query.filter(
        Asistencia.estudiante_id == current_user.id,
        Asistencia.materia_id == materia.id,
        db.func.date(Asistencia.fecha) == hoy
    ).first()

    if existe:
        flash(f'⚠️ Ya marcaste asistencia en {materia.nombre} hoy.', 'warning')
    else:
        nueva_asistencia = Asistencia(
            estudiante_id=current_user.id,
            materia_id=materia.id,
            estado='Presente'
        )
        db.session.add(nueva_asistencia)
        db.session.commit()
        # Mensaje de éxito
        flash(f'✅ ¡Éxito! Asistencia registrada en {materia.nombre} (Sección {sec_materia})', 'success')

    return redirect(url_for('student.escaner'))

# --- 3. PERFIL Y ACTUALIZACIÓN DE DATOS ---
@student_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if current_user.rol != 'estudiante':
        return redirect(url_for('admin.dashboard'))

    # Verificar si el Admin permitió la edición
    config = Configuracion.query.first()
    permitir = config.permitir_edicion if config else False

    if request.method == 'POST':
        if not permitir:
            flash('Las inscripciones están cerradas. No puedes modificar datos.', 'danger')
            return redirect(url_for('student.perfil'))

        nuevo_semestre = request.form.get('semestre')
        nueva_seccion = request.form.get('seccion_estudiante')

        # --- VALIDACIÓN: NO RETROCEDER SEMESTRE ---
        niveles = {'CAIU': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8}
        
        nivel_actual = niveles.get(current_user.semestre, 0)
        nivel_nuevo = niveles.get(nuevo_semestre, 0)

        if nivel_nuevo < nivel_actual:
            flash('Error: No puedes retroceder de semestre.', 'danger')
        else:
            current_user.semestre = nuevo_semestre
            current_user.seccion_estudiante = nueva_seccion
            db.session.commit()
            flash('✅ Datos académicos actualizados correctamente.', 'success')

    return render_template('student/perfil.html', permitir=permitir)