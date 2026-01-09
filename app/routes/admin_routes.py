from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, Materia, Asistencia, Usuario, CatalogoMaterias, Configuracion
import secrets
import qrcode
import io
import base64
from datetime import datetime, date
import csv
from flask import make_response
from app.models import SolicitudClave

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# --- 1. DASHBOARD (Oficina Principal) ---
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol not in ['admin', 'docente']:
        flash('No autorizado', 'danger')
        return redirect(url_for('auth.login'))

    # Obtenemos las materias del usuario (si es docente)
    mis_materias = Materia.query.filter_by(docente_id=current_user.id).all()
    
    pendientes_count = 0
    # Inicializamos config como None por seguridad
    config = None 

    if current_user.rol == 'admin':
        pendientes_count = Usuario.query.filter_by(rol='docente', aprobado=False).count()
        
        # IMPORTANTE: Buscamos el registro único de configuración
        config = Configuracion.query.get(1)
        
        # Si por algún motivo no existe en la DB, lo creamos para evitar errores en el HTML
        if not config:
            config = Configuracion(id=1, permitir_edicion=False)
            db.session.add(config)
            db.session.commit()

    return render_template('admin/dashboard.html', 
                           materias=mis_materias, 
                           pendientes_count=pendientes_count,
                           config=config) # Enviamos el objeto 'config' completo
                           
# --- 2. INICIAR CLASE (Generar Token) ---
@admin_bp.route('/iniciar_clase/<int:materia_id>')
@login_required
def iniciar_clase(materia_id):
    materia = Materia.query.get_or_404(materia_id)
    
    if materia.docente_id != current_user.id:
        flash('No es tu materia.', 'danger')
        return redirect(url_for('admin.dashboard'))

    # Generamos token y guardamos
    token_nuevo = secrets.token_hex(4).upper()
    materia.token_activo = token_nuevo
    db.session.commit()
    
    flash(f'¡Clase iniciada! Token: {token_nuevo}', 'success')
    return redirect(url_for('admin.ver_qr', materia_id=materia.id))

# --- 3. VER QR (Pantalla Grande) ---
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

    # Obtener lista de asistentes de HOY
    hoy = date.today()
    asistencias = Asistencia.query.filter(
        Asistencia.materia_id == materia.id,
        db.func.date(Asistencia.fecha) == hoy
    ).order_by(Asistencia.fecha.desc()).all()

    return render_template('admin/qr_view.html', 
                           materia=materia, 
                           qr_image=img_str,
                           asistencias=asistencias)

# --- 4. ELIMINAR ASISTENCIA (Seguridad en vivo) ---
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

# --- 5. HISTORIAL INTELIGENTE (Docente y Super Admin) ---
@admin_bp.route('/historial')
@login_required
def historial():
    if current_user.rol not in ['admin', 'docente']:
        flash('No autorizado', 'danger')
        return redirect(url_for('auth.login'))

    # Filtros que vienen de la URL
    materia_id = request.args.get('materia_id')
    fecha_filtro = request.args.get('fecha')
    seccion_filtro = request.args.get('seccion') # <--- NUEVO

    # Consulta base
    query = Asistencia.query.join(Materia)

    # REGLA 1: Docente solo ve lo suyo
    if current_user.rol != 'admin':
        query = query.filter(Materia.docente_id == current_user.id)
    
    # REGLA 2: Filtros
    if materia_id:
        query = query.filter(Asistencia.materia_id == materia_id)
    
    if fecha_filtro:
        query = query.filter(db.func.date(Asistencia.fecha) == fecha_filtro)
        
    # --- FILTRO NUEVO: SECCIÓN ---
    if seccion_filtro:
        query = query.filter(Materia.codigo_seccion == seccion_filtro)

    asistencias = query.order_by(Asistencia.fecha.desc()).all()

    # Datos para llenar los selectores (dropdowns)
    if current_user.rol == 'admin':
        todas_las_materias = Materia.query.all()
        # Obtenemos todas las secciones únicas que existen en la BD
        secciones = db.session.query(Materia.codigo_seccion).distinct().all()
    else:
        todas_las_materias = Materia.query.filter_by(docente_id=current_user.id).all()
        # Solo las secciones de este profesor
        secciones = db.session.query(Materia.codigo_seccion)\
                    .filter_by(docente_id=current_user.id).distinct().all()

    # Convertimos la lista de tuplas a lista simple para el HTML
    lista_secciones = [s[0] for s in secciones if s[0]]

    return render_template('admin/historial.html', 
                           asistencias=asistencias, 
                           materias=todas_las_materias,
                           secciones=lista_secciones) # <--- Enviamos esto al HTML

# --- 6. VER LISTA DE PENDIENTES ---
@admin_bp.route('/aprobaciones')
@login_required
def aprobaciones():
    # SEGURIDAD: Solo el Admin Supremo entra aquí
    if current_user.rol != 'admin':
        flash('Acceso denegado. Solo para Administradores.', 'danger')
        return redirect(url_for('admin.dashboard'))

    # Buscamos usuarios con rol 'docente' que NO estén aprobados
    pendientes = Usuario.query.filter_by(rol='docente', aprobado=False).all()
    
    return render_template('admin/aprobaciones.html', pendientes=pendientes)

# --- 7. APROBAR DOCENTE ---
@admin_bp.route('/aprobar_docente/<int:user_id>')
@login_required
def aprobar_docente(user_id):
    if current_user.rol != 'admin':
        return redirect(url_for('admin.dashboard'))

    usuario = Usuario.query.get_or_404(user_id)
    usuario.aprobado = True # ¡Aquí ocurre la magia!
    db.session.commit()
    
    flash(f'✅ El docente {usuario.nombre} ha sido aprobado.', 'success')
    return redirect(url_for('admin.aprobaciones'))

# --- 8. RECHAZAR (ELIMINAR) DOCENTE ---
@admin_bp.route('/rechazar_docente/<int:user_id>')
@login_required
def rechazar_docente(user_id):
    if current_user.rol != 'admin':
        return redirect(url_for('admin.dashboard'))

    usuario = Usuario.query.get_or_404(user_id)
    db.session.delete(usuario) # Lo borramos de la base de datos
    db.session.commit()
    
    flash(f'🗑️ Solicitud de {usuario.nombre} rechazada y eliminada.', 'warning')
    return redirect(url_for('admin.aprobaciones'))

# --- 9. ASIGNAR CARGA ACADÉMICA (ACTUALIZADO: CON SELECTS) ---
@admin_bp.route('/asignar_materia', methods=['GET', 'POST'])
@login_required
def asignar_materia():
    if current_user.rol != 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        docente_id = request.form.get('docente_id')
        catalogo_id = request.form.get('catalogo_id') # ID del nombre de la materia
        seccion = request.form.get('seccion')

        if not docente_id or not catalogo_id or not seccion:
            flash('Todos los campos son obligatorios.', 'danger')
        else:
            # Buscamos el nombre real de la materia en el catálogo
            item_catalogo = CatalogoMaterias.query.get(catalogo_id)
            
            # Crear la relación Materia -> Docente
            nueva_materia = Materia(
                nombre=item_catalogo.nombre, # Usamos el nombre oficial
                codigo_seccion=seccion,      # Sección seleccionada
                docente_id=docente_id
            )
            db.session.add(nueva_materia)
            db.session.commit()
            flash(f'Asignatura "{item_catalogo.nombre} - Sección {seccion}" asignada correctamente.', 'success')
            return redirect(url_for('admin.dashboard'))

    # GET: Enviamos docentes y el catálogo de materias disponibles
    docentes = Usuario.query.filter_by(rol='docente', aprobado=True).all()
    catalogo = CatalogoMaterias.query.order_by(CatalogoMaterias.nombre).all()
    
    return render_template('admin/asignar_materia.html', docentes=docentes, catalogo=catalogo)

# --- 10. EXPORTAR A EXCEL (CSV) ---
@admin_bp.route('/descargar_reporte')
@login_required
def descargar_reporte():
    # 1. Preparar CSV
    si = io.StringIO()
    si.write('\ufeff') # UTF-8 BOM para Excel
    cw = csv.writer(si, delimiter=';')
    
    cw.writerow(['Fecha', 'Hora', 'Asignatura', 'Sección (Clase)', 'Docente', 'Estudiante', 'Cédula', 'Sección (Alumno)', 'Estado'])
    
    # 2. Obtener los mismos filtros que usamos en Historial
    materia_id = request.args.get('materia_id')
    fecha_filtro = request.args.get('fecha')
    seccion_filtro = request.args.get('seccion')

    # 3. Construir la consulta BASE (Importante el join con Materia para filtrar)
    query = Asistencia.query.join(Materia)

    # REGLA 1: Si es docente, limitar a sus materias
    if current_user.rol == 'docente':
        query = query.filter(Materia.docente_id == current_user.id)

    # REGLA 2: Aplicar los filtros si existen
    if materia_id:
        query = query.filter(Asistencia.materia_id == materia_id)
    
    if fecha_filtro:
        query = query.filter(db.func.date(Asistencia.fecha) == fecha_filtro)
        
    if seccion_filtro:
        query = query.filter(Materia.codigo_seccion == seccion_filtro)

    # 4. Obtener resultados
    registros = query.order_by(Asistencia.fecha.desc()).all()

    # 5. Escribir filas
    for reg in registros:
        cw.writerow([
            reg.fecha.strftime('%d/%m/%Y'),
            reg.fecha.strftime('%H:%M'),
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

# --- 11. GESTIONAR CATÁLOGO (NUEVO) ---
@admin_bp.route('/catalogo', methods=['GET', 'POST'])
@login_required
def gestionar_catalogo():
    if current_user.rol != 'admin':
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        # Agregar nueva materia al catálogo
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

# --- 13. INTERRUPTOR MAESTRO (Permitir/Bloquear Cambios) ---
@admin_bp.route('/toggle_edicion')
@login_required
def toggle_edicion():
    if current_user.rol != 'admin':
        return redirect(url_for('auth.login'))

    config = Configuracion.query.get(1)
    if not config:
        # Si por alguna razón no existe, la creamos
        config = Configuracion(id=1, permitir_edicion=False)
        db.session.add(config)
    
    # Cambiamos el estado
    config.permitir_edicion = not config.permitir_edicion
    
    # FORZAMOS EL GUARDADO INMEDIATO
    db.session.add(config)
    db.session.commit()
    
    # Mensaje dinámico según el nuevo estado
    estado = "ABIERTAS" if config.permitir_edicion else "CERRADAS"
    flash(f'Inscripciones {estado} con éxito', 'success')
    
    # Redirigir asegurando que no se use caché
    return redirect(url_for('admin.dashboard', _external=True, _t=datetime.now().timestamp()))

# --- NUEVO: CERRAR CLASE (MATA EL QR) ---
@admin_bp.route('/cerrar_clase/<int:materia_id>')
@login_required
def cerrar_clase(materia_id):
    materia = Materia.query.get_or_404(materia_id)
    
    # Verificamos que sea el dueño de la materia
    if materia.docente_id != current_user.id:
        flash('No tienes permiso.', 'danger')
        return redirect(url_for('admin.dashboard'))

    # AQUÍ ESTÁ EL TRUCO:
    # Simplemente borramos el token. 
    # Sin token, el QR deja de existir y nadie más puede registrarse.
    materia.token_activo = None
    db.session.commit()
    
    flash('Clase cerrada correctamente. Ya nadie puede registrar asistencia.', 'info')
    
    # Lo mandamos de vuelta al dashboard o a donde prefieras
    return redirect(url_for('admin.dashboard'))   

# --- VER SOLICITUDES DE CLAVE ---
@admin_bp.route('/solicitudes_clave')
@login_required
def solicitudes_clave():
    if current_user.rol != 'admin':
        return redirect(url_for('admin.dashboard'))
        
    solicitudes = SolicitudClave.query.order_by(SolicitudClave.fecha_solicitud.desc()).all()
    return render_template('admin/solicitudes_clave.html', solicitudes=solicitudes)

# --- APROBAR CAMBIO ---
@admin_bp.route('/aprobar_clave/<int:id>')
@login_required
def aprobar_clave(id):
    if current_user.rol != 'admin': return redirect(url_for('admin.dashboard'))
    
    solicitud = SolicitudClave.query.get_or_404(id)
    usuario = solicitud.usuario
    
    # APLICAMOS EL CAMBIO
    usuario.password_hash = solicitud.nueva_clave_hash  
    
    # Borramos la solicitud porque ya se cumplió
    db.session.delete(solicitud)
    db.session.commit()
    
    flash(f'Contraseña actualizada para {usuario.nombre}', 'success')
    return redirect(url_for('admin.solicitudes_clave'))

# --- RECHAZAR CAMBIO ---
@admin_bp.route('/rechazar_clave/<int:id>')
@login_required
def rechazar_clave(id):
    if current_user.rol != 'admin': return redirect(url_for('admin.dashboard'))
    
    solicitud = SolicitudClave.query.get_or_404(id)
    db.session.delete(solicitud)
    db.session.commit()
    
    flash('Solicitud rechazada y eliminada.', 'warning')
    return redirect(url_for('admin.solicitudes_clave'))    

# --- NUEVO: EXPORTAR INASISTENCIAS (Tepuy Link) ---
@admin_bp.route('/exportar_inasistencias/<int:materia_id>')
@login_required
def exportar_inasistencias(materia_id):
    # Solo admin o el docente dueño
    materia = Materia.query.get_or_404(materia_id)
    if current_user.rol != 'admin' and materia.docente_id != current_user.id:
        flash('No autorizado', 'danger')
        return redirect(url_for('admin.dashboard'))

    # 1. Definir el Universo: Estudiantes de esa sección
    # (Asumiendo que el estudiante pertenece a la sección globalmente)
    estudiantes_seccion = Usuario.query.filter_by(
        rol='estudiante', 
        seccion_estudiante=materia.codigo_seccion
    ).all()
    
    # Si no hay estudiantes en esa sección, no hay nada que calcular
    if not estudiantes_seccion:
        flash(f'No hay estudiantes registrados en la Sección {materia.codigo_seccion}.', 'warning')
        return redirect(url_for('admin.dashboard'))

    # 2. Definir los Presentes: Quiénes marcaron hoy
    hoy = date.today()
    asistencias_hoy = Asistencia.query.filter(
        Asistencia.materia_id == materia.id,
        db.func.date(Asistencia.fecha) == hoy
    ).all()
    
    # Sacamos los IDs de los que vinieron
    ids_presentes = {a.estudiante_id for a in asistencias_hoy}

    # 3. Calcular la Diferencia (Los Inasistentes)
    inasistentes = []
    for estudiante in estudiantes_seccion:
        if estudiante.id not in ids_presentes:
            inasistentes.append(estudiante)

    # 4. Generar el Archivo (Formato Compatible con Base de Datos)
    si = io.StringIO()
    # Escribimos encabezados o solo datos (depende de lo que pida Tepuy). 
    # Aquí ponemos formato estándar: CEDULA, FECHA, MATERIA
    cw = csv.writer(si, delimiter=';') # Punto y coma es mejor para Excel/Latam
    cw.writerow(['CEDULA', 'FECHA_FALTA', 'CODIGO_MATERIA', 'SECCION'])
    
    for alumno in inasistentes:
        cw.writerow([
            alumno.cedula,
            hoy.strftime('%Y-%m-%d'),  # Formato ISO para base de datos (YYYY-MM-DD)
            materia.nombre,
            materia.codigo_seccion
        ])

    # 5. Descargar
    nombre_archivo = f"TEPUY_Inasistencias_{materia.nombre}_{hoy}.csv"
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={nombre_archivo}"
    output.headers["Content-type"] = "text/csv"
    return output     