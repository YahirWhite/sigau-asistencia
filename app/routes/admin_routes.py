from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from app.models import db, Materia, Asistencia, Usuario, CatalogoMaterias, Configuracion, SolicitudClave, obtener_hora_vzla
import secrets
import qrcode
import io
import base64
from datetime import datetime, date
import csv
import pytz

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Zona horaria global para conversiones de salida
VZLA_TZ = pytz.timezone('America/Caracas')

# --- 1. DASHBOARD (Oficina Principal) ---
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol not in ['admin', 'docente']:
        flash('No autorizado', 'danger')
        return redirect(url_for('auth.login'))

    mis_materias = Materia.query.filter_by(docente_id=current_user.id).all()
    pendientes_count = 0
    config = None 

    if current_user.rol == 'admin':
        pendientes_count = Usuario.query.filter_by(rol='docente', aprobado=False).count()
        config = Configuracion.query.get(1)
        
        if not config:
            config = Configuracion(id=1, permitir_edicion=False)
            db.session.add(config)
            db.session.commit()

    return render_template('admin/dashboard.html', 
                           materias=mis_materias, 
                           pendientes_count=pendientes_count,
                           config=config)

# --- 2. INICIAR CLASE (Generar Token) ---
@admin_bp.route('/iniciar_clase/<int:materia_id>')
@login_required
def iniciar_clase(materia_id):
    materia = Materia.query.get_or_404(materia_id)
    
    if materia.docente_id != current_user.id:
        flash('No es tu materia.', 'danger')
        return redirect(url_for('admin.dashboard'))

    token_nuevo = secrets.token_hex(4).upper()
    materia.token_activo = token_nuevo
    db.session.commit()
    
    flash(f'¡Clase iniciada! Token: {token_nuevo}', 'success')
    return redirect(url_for('admin.ver_qr', materia_id=materia.id))

# --- 3. VER QR (Pantalla Grande - Corregido Hora Vzla) ---
@admin_bp.route('/ver_qr/<int:materia_id>')
@login_required
def ver_qr(materia_id):
    materia = Materia.query.get_or_404(materia_id)

    if not materia.token_activo:
        return redirect(url_for('admin.dashboard'))

    # Generar QR
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(materia.token_activo)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()

    # Obtener lista de asistentes usando la fecha actual de Venezuela
    hoy_vzla = obtener_hora_vzla().date()
    asistencias = Asistencia.query.filter(
        Asistencia.materia_id == materia.id,
        db.func.date(Asistencia.fecha) == hoy_vzla
    ).order_by(Asistencia.fecha.desc()).all()

    return render_template('admin/qr_view.html', 
                           materia=materia, 
                           qr_image=img_str,
                           asistencias=asistencias)

# --- 4. ELIMINAR ASISTENCIA ---
@admin_bp.route('/eliminar_asistencia/<int:asistencia_id>')
@login_required
def eliminar_asistencia(asistencia_id):
    asistencia = Asistencia.query.get_or_404(asistencia_id)
    materia = asistencia.materia
    
    if materia.docente_id != current_user.id:
        flash('No tienes permiso.', 'danger')
        return redirect(url_for('admin.dashboard'))

    db.session.delete(asistencia)
    db.session.commit()
    
    flash('Asistencia eliminada manualmente.', 'warning')
    return redirect(url_for('admin.ver_qr', materia_id=materia.id))

# --- 5. HISTORIAL INTELIGENTE (Corregido con Ajuste de Huso Horario) ---
@admin_bp.route('/historial')
@login_required
def historial():
    if current_user.rol not in ['admin', 'docente']:
        flash('No autorizado', 'danger')
        return redirect(url_for('auth.login'))

    materia_id = request.args.get('materia_id')
    fecha_filtro = request.args.get('fecha')
    seccion_filtro = request.args.get('seccion')

    query = Asistencia.query.join(Materia)

    if current_user.rol != 'admin':
        query = query.filter(Materia.docente_id == current_user.id)
    
    if materia_id:
        query = query.filter(Asistencia.materia_id == materia_id)
    
    if fecha_filtro:
        query = query.filter(db.func.date(Asistencia.fecha) == fecha_filtro)
        
    if seccion_filtro:
        query = query.filter(Materia.codigo_seccion == seccion_filtro)

    asistencias = query.order_by(Asistencia.fecha.desc()).all()

    # Ajustamos la hora de cada registro para la visualización en el historial
    for a in asistencias:
        if a.fecha.tzinfo is None:
            a.fecha = VZLA_TZ.localize(a.fecha)
        else:
            a.fecha = a.fecha.astimezone(VZLA_TZ)

    if current_user.rol == 'admin':
        todas_las_materias = Materia.query.all()
        secciones = db.session.query(Materia.codigo_seccion).distinct().all()
    else:
        todas_las_materias = Materia.query.filter_by(docente_id=current_user.id).all()
        secciones = db.session.query(Materia.codigo_seccion)\
                    .filter_by(docente_id=current_user.id).distinct().all()

    lista_secciones = [s[0] for s in secciones if s[0]]

    return render_template('admin/historial.html', 
                           asistencias=asistencias, 
                           materias=todas_las_materias,
                           secciones=lista_secciones)

# --- 6. VER LISTA DE PENDIENTES ---
@admin_bp.route('/aprobaciones')
@login_required
def aprobaciones():
    if current_user.rol != 'admin':
        flash('Acceso denegado. Solo para Administradores.', 'danger')
        return redirect(url_for('admin.dashboard'))

    pendientes = Usuario.query.filter_by(rol='docente', aprobado=False).all()
    return render_template('admin/aprobaciones.html', pendientes=pendientes)

# --- 7. APROBAR DOCENTE ---
@admin_bp.route('/aprobar_docente/<int:user_id>')
@login_required
def aprobar_docente(user_id):
    if current_user.rol != 'admin':
        return redirect(url_for('admin.dashboard'))

    usuario = Usuario.query.get_or_404(user_id)
    usuario.aprobado = True 
    db.session.commit()
    
    flash(f'✅ El docente {usuario.nombre} ha sido aprobado.', 'success')
    return redirect(url_for('admin.aprobaciones'))

# --- 8. RECHAZAR DOCENTE ---
@admin_bp.route('/rechazar_docente/<int:user_id>')
@login_required
def rechazar_docente(user_id):
    if current_user.rol != 'admin':
        return redirect(url_for('admin.dashboard'))

    usuario = Usuario.query.get_or_404(user_id)
    db.session.delete(usuario)
    db.session.commit()
    
    flash(f'🗑️ Solicitud de {usuario.nombre} rechazada y eliminada.', 'warning')
    return redirect(url_for('admin.aprobaciones'))

# --- 9. ASIGNAR CARGA ACADÉMICA ---
@admin_bp.route('/asignar_materia', methods=['GET', 'POST'])
@login_required
def asignar_materia():
    if current_user.rol != 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        docente_id = request.form.get('docente_id')
        catalogo_id = request.form.get('catalogo_id')
        seccion = request.form.get('seccion')

        if not docente_id or not catalogo_id or not seccion:
            flash('Todos los campos son obligatorios.', 'danger')
        else:
            item_catalogo = CatalogoMaterias.query.get(catalogo_id)
            nueva_materia = Materia(
                nombre=item_catalogo.nombre,
                codigo_seccion=seccion,
                docente_id=docente_id
            )
            db.session.add(nueva_materia)
            db.session.commit()
            flash(f'Asignatura "{item_catalogo.nombre} - Sección {seccion}" asignada.', 'success')
            return redirect(url_for('admin.dashboard'))

    docentes = Usuario.query.filter_by(rol='docente', aprobado=True).all()
    catalogo = CatalogoMaterias.query.order_by(CatalogoMaterias.nombre).all()
    return render_template('admin/asignar_materia.html', docentes=docentes, catalogo=catalogo)

# --- 10. EXPORTAR A EXCEL (CSV Corregido con Hora Vzla) ---
@admin_bp.route('/descargar_reporte')
@login_required
def descargar_reporte():
    si = io.StringIO()
    si.write('\ufeff') 
    cw = csv.writer(si, delimiter=';')
    
    cw.writerow(['Fecha', 'Hora', 'Asignatura', 'Sección (Clase)', 'Docente', 'Estudiante', 'Cédula', 'Sección (Alumno)', 'Estado'])
    
    materia_id = request.args.get('materia_id')
    fecha_filtro = request.args.get('fecha')
    seccion_filtro = request.args.get('seccion')

    query = Asistencia.query.join(Materia)

    if current_user.rol == 'docente':
        query = query.filter(Materia.docente_id == current_user.id)

    if materia_id:
        query = query.filter(Asistencia.materia_id == materia_id)
    
    if fecha_filtro:
        query = query.filter(db.func.date(Asistencia.fecha) == fecha_filtro)
        
    if seccion_filtro:
        query = query.filter(Materia.codigo_seccion == seccion_filtro)

    registros = query.order_by(Asistencia.fecha.desc()).all()

    for reg in registros:
        # Conversión explícita a hora de Venezuela para el archivo CSV
        f_vzla = reg.fecha.astimezone(VZLA_TZ) if reg.fecha.tzinfo else VZLA_TZ.localize(reg.fecha)
        
        cw.writerow([
            f_vzla.strftime('%d/%m/%Y'),
            f_vzla.strftime('%H:%M'),
            reg.materia.nombre,
            reg.materia.codigo_seccion,
            reg.materia.docente.nombre,
            reg.estudiante.nombre,
            reg.estudiante.cedula,
            getattr(reg.estudiante, 'seccion_estudiante', 'S/D'),
            reg.estado
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=reporte_asistencia.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    return output

# --- 11. GESTIONAR CATÁLOGO ---
@admin_bp.route('/catalogo', methods=['GET', 'POST'])
@login_required
def gestionar_catalogo():
    if current_user.rol != 'admin':
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        nombre_materia = request.form.get('nombre_materia')
        if nombre_materia:
            existe = CatalogoMaterias.query.filter_by(nombre=nombre_materia).first()
            if not existe:
                nuevo = CatalogoMaterias(nombre=nombre_materia)
                db.session.add(nuevo)
                db.session.commit()
                flash('Materia agregada al catálogo.', 'success')
            else:
                flash('Esa materia ya existe.', 'warning')
    
    materias = CatalogoMaterias.query.order_by(CatalogoMaterias.nombre).all()
    return render_template('admin/gestionar_catalogo.html', materias=materias)

# --- 12. ELIMINAR DEL CATÁLOGO ---
@admin_bp.route('/eliminar_catalogo/<int:id>')
@login_required
def eliminar_catalogo(id):
    if current_user.rol != 'admin': return redirect(url_for('admin.dashboard'))
    item = CatalogoMaterias.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Materia eliminada del catálogo.', 'info')
    return redirect(url_for('admin.gestionar_catalogo'))  

# --- 13. INTERRUPTOR MAESTRO ---
@admin_bp.route('/toggle_edicion')
@login_required
def toggle_edicion():
    if current_user.rol != 'admin':
        return redirect(url_for('auth.login'))

    config = Configuracion.query.get(1)
    if not config:
        config = Configuracion(id=1, permitir_edicion=False)
        db.session.add(config)
    
    config.permitir_edicion = not config.permitir_edicion
    db.session.add(config)
    db.session.commit()
    
    estado = "ABIERTAS" if config.permitir_edicion else "CERRADAS"
    flash(f'Inscripciones {estado} con éxito', 'success')
    return redirect(url_for('admin.dashboard', _external=True, _t=datetime.now().timestamp()))

# --- 14. CERRAR CLASE ---
@admin_bp.route('/cerrar_clase/<int:materia_id>')
@login_required
def cerrar_clase(materia_id):
    materia = Materia.query.get_or_404(materia_id)
    if materia.docente_id != current_user.id:
        flash('No tienes permiso.', 'danger')
        return redirect(url_for('admin.dashboard'))

    materia.token_activo = None
    db.session.commit()
    flash('Clase cerrada correctamente.', 'info')
    return redirect(url_for('admin.dashboard'))   

# --- 15. VER SOLICITUDES DE CLAVE ---
@admin_bp.route('/solicitudes_clave')
@login_required
def solicitudes_clave():
    if current_user.rol != 'admin':
        return redirect(url_for('admin.dashboard'))
    solicitudes = SolicitudClave.query.order_by(SolicitudClave.fecha_solicitud.desc()).all()
    
    # Ajuste de hora para visualización de solicitudes
    for s in solicitudes:
        if s.fecha_solicitud.tzinfo is None:
            s.fecha_solicitud = VZLA_TZ.localize(s.fecha_solicitud)
        else:
            s.fecha_solicitud = s.fecha_solicitud.astimezone(VZLA_TZ)
            
    return render_template('admin/solicitudes_clave.html', solicitudes=solicitudes)

# --- 16. APROBAR/RECHAZAR CLAVE ---
@admin_bp.route('/aprobar_clave/<int:id>')
@login_required
def aprobar_clave(id):
    if current_user.rol != 'admin': return redirect(url_for('admin.dashboard'))
    solicitud = SolicitudClave.query.get_or_404(id)
    usuario = solicitud.usuario
    usuario.password_hash = solicitud.nueva_clave_hash  
    db.session.delete(solicitud)
    db.session.commit()
    flash(f'Contraseña actualizada para {usuario.nombre}', 'success')
    return redirect(url_for('admin.solicitudes_clave'))

@admin_bp.route('/rechazar_clave/<int:id>')
@login_required
def rechazar_clave(id):
    if current_user.rol != 'admin': return redirect(url_for('admin.dashboard'))
    solicitud = SolicitudClave.query.get_or_404(id)
    db.session.delete(solicitud)
    db.session.commit()
    flash('Solicitud rechazada.', 'warning')
    return redirect(url_for('admin.solicitudes_clave'))    

# --- 17. EXPORTAR INASISTENCIAS (Corregido con Calendario Vzla) ---
@admin_bp.route('/exportar_inasistencias/<int:materia_id>')
@login_required
def exportar_inasistencias(materia_id):
    materia = Materia.query.get_or_404(materia_id)
    if current_user.rol != 'admin' and materia.docente_id != current_user.id:
        flash('No autorizado', 'danger')
        return redirect(url_for('admin.dashboard'))

    estudiantes_seccion = Usuario.query.filter_by(
        rol='estudiante', 
        seccion_estudiante=materia.codigo_seccion
    ).all()
    
    if not estudiantes_seccion:
        flash(f'No hay estudiantes registrados en la Sección {materia.codigo_seccion}.', 'warning')
        return redirect(url_for('admin.dashboard'))

    # Usamos la fecha real de Venezuela para calcular faltas
    hoy_vzla = obtener_hora_vzla().date()
    asistencias_hoy = Asistencia.query.filter(
        Asistencia.materia_id == materia.id,
        db.func.date(Asistencia.fecha) == hoy_vzla
    ).all()
    
    ids_presentes = {a.estudiante_id for a in asistencias_hoy}
    inasistentes = [e for e in estudiantes_seccion if e.id not in ids_presentes]

    si = io.StringIO()
    cw = csv.writer(si, delimiter=';')
    cw.writerow(['CEDULA', 'FECHA_FALTA', 'CODIGO_MATERIA', 'SECCION'])
    
    for alumno in inasistentes:
        cw.writerow([
            alumno.cedula,
            hoy_vzla.strftime('%Y-%m-%d'),
            materia.nombre,
            materia.codigo_seccion
        ])

    nombre_archivo = f"TEPUY_Inasistencias_{materia.nombre}_{hoy_vzla}.csv"
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={nombre_archivo}"
    output.headers["Content-type"] = "text/csv"
    return output