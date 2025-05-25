from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from .auth import buscar_usuario_por_documento
from .auth import cerrar_y_render, registrar_asistencia_y_mensaje, obtener_asistencia_abierta, calcular_mensaje_salida, registrar_salida
from .auth import verificar_credencial, obtener_asistencia_sin_salida, obtener_hora_salida_programada, comparar_salida_programada
from .auth import validar_credencial_generico, cerrar_y_render_salida, calcular_mensaje_salida_admin
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from .auth import buscar_usuario_por_documento, Usuario
from flask_login import logout_user, login_required
from app import services
from .services import registrar_entrada_empleado
from datetime import date
from datetime import datetime as dt
from datetime import datetime
from flask import flash
import pytz
from flask import send_from_directory
from .database import get_connection
from .auth import (
    zona_colombia,
    ahora_colombia,
    entrada_ya_registrada,
    validar_credencial,
    obtener_horario,
    es_dia_laboral,
    esta_en_rango_horario,
    calcular_retraso
)

main_bp = Blueprint('main', __name__)

# Mejora del sonar, constantes
TEMPLATE_PANEL_SUPERVISOR = 'panel_supervisor.html'
TEMPLATE_PANEL_EMPLEADO = 'panel_empleado.html'
TEMPLATE_PANEL_ADMIN = 'panel_admin.html'
TEMPLATE_REGISTRO_ENTRADA = 'registro_entrada.html'
TEMPLATE_REGISTRO_SALIDA = 'registro_salida.html'
TEMPLATE_GESTIONAR_ASIGNACIONES = 'gestionar_asignaciones.html'
TEMPLATE_GESTIONAR_HORARIOS = 'gestionar_horarios.html'
TEMPLATE_REPORTE_RETRASOS = 'reporte_retrasos.html'
TEMPLATE_SOLICITAR_TIEMPO_EXTRA = 'solicitar_tiempo_extra.html'
TEMPLATE_REVISAR_TIEMPO_EXTRA = 'revisar_tiempo_extra.html'
TEMPLATE_ENVIAR_AVISOS = 'enviar_avisos.html'
TEMPLATE_VER_AVISOS = 'ver_avisos.html'
TEMPLATE_VER_AVISOS_ADMIN = 'ver_avisos_admin.html'
TEMPLATE_MI_QR = 'mi_qr.html'
TEMPLATE_LOGIN = 'login.html'
TEMPLATE_MIS_EMPLEADOS = 'mis_empleados.html'
TEMPLATE_VER_SOLICITUDES_EXTRA = 'ver_mis_solicitudes_extra.html'
SQL_SELECT_ID_EMPLEADO_POR_DOCUMENTO = "SELECT id_empleado FROM empleado WHERE documento = %s"
SQL_SELECT_DATOS_SUPERVISOR = "SELECT id_supervisor, nombre, apellido FROM supervisor"
SQL_SELECT_ID_SUPERVISOR = "SELECT id_supervisor FROM supervisor WHERE documento = %s"
LOGIN_ROUTE = 'main.login'
PIN_O_TARJETA_MESSAGE_INCORRECTA = "PIN o tarjeta incorrecta"
ZONA_HORARIA_CO = 'America/Bogota'
MENSAJE_PIN_INCORRECTO = "PIN o tarjeta incorrecta."
MENSAJE_NO_ENTRADA_HOY = "No hay entrada registrada hoy o ya registraste la salida."
MENSAJE_SALIDA_REGISTRADA = "Salida registrada con éxito."


@main_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        documento = request.form['documento']
        rol, usuario = buscar_usuario_por_documento(documento)

        if usuario:
            user = Usuario(
                documento=documento,
                role=rol,
                nombre=usuario['nombre']
            )
            login_user(user)

            if rol == 'empleado':
                return redirect(url_for('main.empleado_panel'))
            elif rol == 'supervisor':
                return redirect(url_for('main.supervisor_panel'))
            elif rol == 'administrador':
                return redirect(url_for('main.admin_panel'))

        return render_template(TEMPLATE_LOGIN, error='Documento no registrado.')

    return render_template(TEMPLATE_LOGIN)


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for(LOGIN_ROUTE))


@main_bp.route('/panel/empleado')
@login_required
def empleado_panel():
    if current_user.role != 'empleado':
        return redirect(url_for(LOGIN_ROUTE))
    return render_template(TEMPLATE_PANEL_EMPLEADO)


@main_bp.route('/panel/supervisor')
@login_required
def supervisor_panel():
    if current_user.role != 'supervisor':
        return redirect(url_for(LOGIN_ROUTE))
    return render_template(TEMPLATE_PANEL_SUPERVISOR)


@main_bp.route('/panel/admin')
@login_required
def admin_panel():
    if current_user.role != 'administrador':
        return redirect(url_for(LOGIN_ROUTE))
    return render_template(TEMPLATE_PANEL_ADMIN)


@main_bp.route('/empleado/entrada', methods=['GET', 'POST'])
@login_required
def vista_registro_entrada():
    if current_user.role != 'empleado':
        return redirect(url_for(LOGIN_ROUTE))

    if request.method == 'POST':
        documento = current_user.documento
        metodo = request.form['metodo']
        valor = request.form['valor']
        mensaje = services.registrar_entrada_empleado(documento, metodo, valor)
        return render_template(TEMPLATE_REGISTRO_ENTRADA, mensaje=mensaje)

    return render_template(TEMPLATE_REGISTRO_ENTRADA)


@main_bp.route('/supervisor/entrada', methods=['GET', 'POST'])
@login_required
def vista_registro_entrada_supervisor():
    if current_user.role != 'supervisor':
        return redirect(url_for(LOGIN_ROUTE))

    if request.method == 'POST':
        documento = current_user.documento
        metodo = request.form['metodo']
        valor = request.form['valor']

        zona_colombia = pytz.timezone(ZONA_HORARIA_CO)
        ahora = datetime.now(zona_colombia)
        hora_local = ahora.time().replace(microsecond=0)
        hoy = ahora.date()

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM asistencia 
            WHERE documento_empleado = %s AND fecha = %s
        """, (documento, hoy))
        ya_registrado = cur.fetchone()

        if ya_registrado:
            cur.close()
            conn.close()
            return render_template(TEMPLATE_REGISTRO_ENTRADA, error="Ya registraste tu entrada hoy supervisor.")

        campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
        cur.execute(f"""
            SELECT * FROM supervisor 
            WHERE documento = %s AND {campo} = %s
        """, (documento, valor))
        supervisor = cur.fetchone()

        if not supervisor:
            cur.close()
            conn.close()
            return render_template(TEMPLATE_REGISTRO_ENTRADA, error=PIN_O_TARJETA_MESSAGE_INCORRECTA)

        try:
            cur.execute("""
                INSERT INTO asistencia (documento_empleado, metodo, hora_entrada, fecha)
                VALUES (%s, %s, %s, %s)
            """, (documento, metodo, hora_local, hoy))
            conn.commit()
            mensaje = "Entrada registrada con éxito."
        except Exception as e:
            conn.rollback()
            mensaje = f"Ocurrió un error al registrar la entrada: {str(e).splitlines()[0]}"

        cur.close()
        conn.close()

        return render_template(TEMPLATE_REGISTRO_ENTRADA, mensaje=mensaje)

    return render_template(TEMPLATE_REGISTRO_ENTRADA)   


@main_bp.route('/admin/entrada', methods=['GET', 'POST'])
@login_required
def vista_registro_entrada_admin():
    if current_user.role != 'administrador':
        return redirect(url_for(LOGIN_ROUTE))

    if request.method == 'POST':
        documento = current_user.documento
        metodo = request.form['metodo']
        valor = request.form['valor']
        mensaje = services.registrar_entrada_admin(documento, metodo, valor)
        return render_template(TEMPLATE_REGISTRO_ENTRADA, mensaje=mensaje)

    return render_template(TEMPLATE_REGISTRO_ENTRADA)


@main_bp.route('/empleado/salida', methods=['GET', 'POST'])
@login_required
def vista_registro_salida():
    if current_user.role != 'empleado':
        return redirect(url_for(LOGIN_ROUTE))

    documento = current_user.documento

    if request.method == 'POST':
        metodo = request.form['metodo']
        valor = request.form['valor']

        conn = get_connection()
        cur = conn.cursor()

        if not validar_credencial(cur, documento, metodo, valor):
            return cerrar_y_render(cur, conn, MENSAJE_PIN_INCORRECTO)

        asistencia_id = obtener_asistencia_abierta(cur, documento)
        if not asistencia_id:
            return cerrar_y_render(cur, conn, MENSAJE_NO_ENTRADA_HOY)

        mensaje = calcular_mensaje_salida(cur, documento)
        registrar_salida(cur, asistencia_id)

        conn.commit()
        cur.close()
        conn.close()

        return render_template(TEMPLATE_REGISTRO_SALIDA, mensaje=mensaje)

    return render_template(TEMPLATE_REGISTRO_SALIDA)


@main_bp.route('/supervisor/salida', methods=['GET', 'POST'])
@login_required
def vista_registro_salida_supervisor():
    if current_user.role != 'supervisor':
        return redirect(url_for(LOGIN_ROUTE))

    documento = current_user.documento

    if request.method == 'POST':
        metodo = request.form['metodo']
        valor = request.form['valor']

        zona = pytz.timezone(ZONA_HORARIA_CO)
        ahora = datetime.now(zona)
        hora_local = ahora.time().replace(microsecond=0)
        hoy = ahora.date()

        conn = get_connection()
        cur = conn.cursor()

        supervisor = verificar_credencial(cur, documento, metodo, valor, 'supervisor')
        if not supervisor:
            return cerrar_y_render(cur, conn, PIN_O_TARJETA_MESSAGE_INCORRECTA)

        asistencia = obtener_asistencia_sin_salida(cur, documento, hoy)
        if not asistencia:
            return cerrar_y_render(cur, conn, "No hay entrada registrada hoy o ya registraste la salida.")

        asistencia_id = asistencia[0]
        mensaje = "Salida registrada con éxito."

        try:
            hora_prog = obtener_hora_salida_programada(cur, documento, 'id_supervisor', 'supervisor')
            if hora_prog:
                mensaje += comparar_salida_programada(hora_prog, hora_local, hoy)
        except Exception:
            conn.rollback()

        cur.execute("UPDATE asistencia SET hora_salida = %s WHERE id = %s", (hora_local, asistencia_id))
        conn.commit()

        cur.close()
        conn.close()

        return render_template(TEMPLATE_REGISTRO_SALIDA, mensaje=mensaje)

    return render_template(TEMPLATE_REGISTRO_SALIDA)


@main_bp.route('/admin/salida', methods=['GET', 'POST'])
@login_required
def vista_registro_salida_admin():
    if current_user.role != 'administrador':
        return redirect(url_for(LOGIN_ROUTE))

    documento = current_user.documento

    if request.method != 'POST':
        return render_template(TEMPLATE_REGISTRO_SALIDA)

    metodo = request.form['metodo']
    valor = request.form['valor']

    conn = get_connection()
    cur = conn.cursor()

    if not validar_credencial_generico(cur, documento, metodo, valor, 'administrador'):
        return cerrar_y_render_salida(cur, conn, MENSAJE_PIN_INCORRECTO)

    asistencia_id = obtener_asistencia_abierta(cur, documento)
    if not asistencia_id:
        return cerrar_y_render_salida(cur, conn, MENSAJE_NO_ENTRADA_HOY)

    mensaje = calcular_mensaje_salida_admin(cur, documento)

    registrar_salida(cur, asistencia_id)
    conn.commit()
    cur.close()
    conn.close()

    return render_template(TEMPLATE_REGISTRO_SALIDA, mensaje=mensaje)


@main_bp.route('/admin/asignar-y-gestionar', methods=['GET', 'POST'])
@login_required
def asignar_y_gestionar():
    from .database import get_connection

    if current_user.role != 'administrador':
        return redirect(url_for(LOGIN_ROUTE))

    conn = get_connection()
    cur = conn.cursor()

    mensaje = None
    error = None

    if request.method == 'POST':
        # Si viene del formulario de asignación
        if 'supervisor_id' in request.form and 'empleado_ids' in request.form:
            supervisor_id = request.form['supervisor_id']
            empleados_seleccionados = request.form.getlist('empleado_ids')

            if not empleados_seleccionados:
                error = "Selecciona al menos un empleado."
            else:
                for empleado_id in empleados_seleccionados:
                    cur.execute("""
                        INSERT INTO empleado_supervisor (id_empleado, id_supervisor)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (empleado_id, supervisor_id))
                conn.commit()
                mensaje = "Asignación realizada con éxito."

        # Si viene del formulario de eliminación de asignación
        elif 'empleado_id' in request.form and 'supervisor_id_eliminar' in request.form:
            empleado_id = request.form['empleado_id']
            supervisor_id = request.form['supervisor_id_eliminar']

            cur.execute("""
                DELETE FROM empleado_supervisor
                WHERE id_empleado = %s AND id_supervisor = %s
            """, (empleado_id, supervisor_id))
            conn.commit()
            mensaje = "Asignación eliminada con éxito."

    cur.execute(SQL_SELECT_DATOS_SUPERVISOR)
    supervisores = cur.fetchall()

    cur.execute("""
        SELECT id_empleado, nombre, apellido FROM empleado
        WHERE id_empleado NOT IN (
            SELECT id_empleado FROM empleado_supervisor
        )
    """)
    empleados_no_asignados = cur.fetchall()

    cur.execute("""
        SELECT 
            s.id_supervisor,
            s.nombre AS nombre_supervisor,
            s.apellido AS apellido_supervisor,
            e.id_empleado,
            e.nombre AS nombre_empleado,
            e.apellido AS apellido_empleado
        FROM empleado_supervisor es
        JOIN supervisor s ON es.id_supervisor = s.id_supervisor
        JOIN empleado e ON es.id_empleado = e.id_empleado
        ORDER BY s.id_supervisor, e.apellido
    """)
    registros = cur.fetchall()

    cur.close()
    conn.close()

    asignaciones = {}
    for row in registros:
        id_supervisor = row[0]
        supervisor_nombre = f"{row[1]} {row[2]}"
        empleado_id = row[3]
        empleado_nombre = f"{row[4]} {row[5]}"

        if supervisor_nombre not in asignaciones:
            asignaciones[supervisor_nombre] = []

        asignaciones[supervisor_nombre].append({
            'empleado_id': empleado_id,
            'empleado_nombre': empleado_nombre,
            'supervisor_id': id_supervisor
        })

    return render_template(
        TEMPLATE_GESTIONAR_ASIGNACIONES,  # Nuevo template combinado
        supervisores=supervisores,
        empleados=empleados_no_asignados,
        asignaciones=asignaciones,
        mensaje=mensaje,
        error=error
    )


@main_bp.route('/supervisor/mis-empleados')
@login_required
def ver_empleados_asignados():
    from .database import get_connection

    if current_user.role != 'supervisor':
        return redirect(url_for(LOGIN_ROUTE))

    documento = current_user.documento

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id_supervisor FROM supervisor WHERE documento = %s
    """, (documento,))
    result = cur.fetchone()

    if not result:
        cur.close()
        conn.close()
        return render_template(TEMPLATE_PANEL_SUPERVISOR, error="No se pudo encontrar el supervisor.")

    id_supervisor = result[0]

    cur.execute("""
        SELECT e.nombre, e.apellido
        FROM empleado_supervisor es
        JOIN empleado e ON es.id_empleado = e.id_empleado
        WHERE es.id_supervisor = %s
        ORDER BY e.apellido
    """, (id_supervisor,))
    empleados = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(TEMPLATE_MIS_EMPLEADOS, empleados=empleados)


@main_bp.route('/mi-qr')
@login_required
def ver_mi_qr():
    import qrcode
    import io
    import base64

    documento = current_user.documento
    mensaje = None

    if request.args.get('scan') == 'true':
        # Aquí llamamos tu función avanzada
        mensaje = registrar_entrada_empleado(documento, metodo='qr', valor=None)

    # Generar el QR
    url = f"https://cae-grupo3.onrender.com/mi-qr?scan=true"
    qr = qrcode.make(url)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return render_template(TEMPLATE_MI_QR, qr_base64=qr_base64, documento=documento, mensaje=mensaje)


@main_bp.route('/admin/asignar-y-gestionar-horarios', methods=['GET', 'POST'])
@login_required
def asignar_y_gestionar_horarios():
    from .database import get_connection

    if current_user.role != 'administrador':
        return redirect(url_for(LOGIN_ROUTE))

    conn = get_connection()
    cur = conn.cursor()

    mensaje = None

    if request.method == 'POST':
        id_empleado = request.form['empleado_id']
        hora_entrada = request.form['hora_entrada']
        hora_salida = request.form['hora_salida']
        dias = request.form.getlist('dias_laborales')

        if not dias:
            cur.close()
            conn.close()
            return render_template(
                TEMPLATE_GESTIONAR_HORARIOS,
                empleados_no_asignados=[],
                horarios=[],
                mensaje="Debe seleccionar al menos un día."
            )

        dias_string = ''.join(dias)

        # Detectar si es asignación nueva (sin horario previo)
        if request.form.get('accion') == 'asignar':
            cur.execute("""
                INSERT INTO horarios (id_empleado, dias_laborales, hora_entrada, hora_salida)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id_empleado) DO UPDATE
                SET dias_laborales = EXCLUDED.dias_laborales,
                    hora_entrada = EXCLUDED.hora_entrada,
                    hora_salida = EXCLUDED.hora_salida
            """, (id_empleado, dias_string, hora_entrada, hora_salida))
            mensaje = "Horario asignado correctamente."
        else:
            # Es edición/gestión
            cur.execute("""
                UPDATE horarios
                SET hora_entrada = %s,
                    hora_salida = %s,
                    dias_laborales = %s
                WHERE id_empleado = %s
            """, (hora_entrada, hora_salida, dias_string, id_empleado))
            mensaje = "Horario actualizado correctamente."

        conn.commit()

    # Empleados sin horario
    cur.execute("""
        SELECT id_empleado, nombre, apellido
        FROM empleado
        WHERE id_empleado NOT IN (
            SELECT id_empleado FROM horarios
        )
    """)
    empleados_no_asignados = cur.fetchall()

    cur.execute("""
        SELECT e.id_empleado, e.nombre, e.apellido, h.hora_entrada, h.hora_salida, h.dias_laborales
        FROM horarios h
        JOIN empleado e ON h.id_empleado = e.id_empleado
        ORDER BY e.apellido
    """)
    horarios = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        TEMPLATE_GESTIONAR_HORARIOS,
        empleados_no_asignados=empleados_no_asignados,
        horarios=horarios,
        mensaje=mensaje
    )


def esta_en_horario(documento):
    from .database import get_connection
    from datetime import datetime
    import pytz

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(SQL_SELECT_ID_EMPLEADO_POR_DOCUMENTO, (documento,))
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        return False, "Empleado no encontrado"

    id_empleado = result[0]

    cur.execute("""
        SELECT dias_laborales, hora_entrada, hora_salida
        FROM horarios
        WHERE id_empleado = %s
    """, (id_empleado,))
    horario = cur.fetchone()

    if not horario:
        cur.close()
        conn.close()
        return False, "No tienes horario asignado"

    dias_str, hora_entrada, hora_salida = horario

    zona_colombia = pytz.timezone(ZONA_HORARIA_CO)
    ahora = datetime.now(zona_colombia)
    dia_actual = ahora.strftime('%a').lower()[0]
    hora_actual = ahora.time()

    cur.close()
    conn.close()

    if dia_actual not in dias_str:
        return False, "Hoy no es uno de tus días laborales"

    if not (hora_entrada <= hora_actual <= hora_salida):
        return False, f"Solo puedes registrar entre {hora_entrada} y {hora_salida}"

    return True, "Horario válido"


@main_bp.route('/supervisor/retrasos')
@login_required
def ver_retrasos():
    from .database import get_connection

    if current_user.role != 'supervisor':
        return redirect(url_for(LOGIN_ROUTE))

    documento = current_user.documento

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(SQL_SELECT_ID_SUPERVISOR, (documento,))
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        return render_template(TEMPLATE_PANEL_SUPERVISOR, error="No se encontró el supervisor.")

    id_supervisor = result[0]

    cur.execute("""
        SELECT e.nombre, e.apellido,
               COUNT(a.minutos_retraso) AS veces_tarde,
               SUM(a.minutos_retraso) AS total_retraso
        FROM empleado_supervisor es
        JOIN empleado e ON es.id_empleado = e.id_empleado
        JOIN asistencia a ON e.documento = a.documento_empleado
        WHERE es.id_supervisor = %s AND a.minutos_retraso > 0
        GROUP BY e.id_empleado, e.nombre, e.apellido
        ORDER BY total_retraso DESC
    """, (id_supervisor,))
    retrasos = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(TEMPLATE_REPORTE_RETRASOS, retrasos=retrasos)


@main_bp.route('/supervisor/retrasos/exportar')
@login_required
def exportar_retrasos():
    import pandas as pd
    from io import BytesIO
    from flask import send_file
    from .database import get_connection

    if current_user.role != 'supervisor':
        return redirect(url_for(LOGIN_ROUTE))

    documento = current_user.documento
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(SQL_SELECT_ID_SUPERVISOR, (documento,))
    id_supervisor = cur.fetchone()[0]

    cur.execute("""
        SELECT e.nombre, e.apellido,
               COUNT(a.minutos_retraso) AS veces_tarde,
               SUM(a.minutos_retraso) AS total_retraso
        FROM empleado_supervisor es
        JOIN empleado e ON es.id_empleado = e.id_empleado
        JOIN asistencia a ON e.documento = a.documento_empleado
        WHERE es.id_supervisor = %s AND a.minutos_retraso > 0
        GROUP BY e.id_empleado, e.nombre, e.apellido
        ORDER BY total_retraso DESC
    """, (id_supervisor,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    df = pd.DataFrame(rows, columns=['Nombre', 'Apellido', 'Veces tarde', 'Minutos de retraso'])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Retrasos')

    output.seek(0)

    return send_file(output, download_name="reporte_retrasos.xlsx", as_attachment=True)


@main_bp.route('/empleado/tiempo-extra', methods=['GET', 'POST'])
@login_required
def solicitar_tiempo_extra():
    from .database import get_connection
    from flask import current_app
    from datetime import date
    import os
    from werkzeug.utils import secure_filename

    def archivo_valido(nombre):
        return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in {
            'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'
        }

    if current_user.role != 'empleado':
        return redirect(url_for(LOGIN_ROUTE))

    documento = current_user.documento

    if request.method == 'POST':
        fecha = request.form['fecha']
        hora_inicio = request.form['hora_inicio']
        hora_fin = request.form['hora_fin']
        motivo = request.form['motivo']
        archivo = request.files.get('archivo')
        nombre_archivo = None

        if archivo and archivo.filename and archivo_valido(archivo.filename):
            nombre_archivo = f"{documento}_{fecha}_{secure_filename(archivo.filename)}"
            ruta_guardado = os.path.join(current_app.root_path, 'uploads', 'tiempo_extra', nombre_archivo)
            os.makedirs(os.path.dirname(ruta_guardado), exist_ok=True)
            archivo.save(ruta_guardado)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tiempo_extra (
                documento_empleado, fecha, hora_inicio, hora_fin, motivo, archivo_justificacion
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (documento, fecha, hora_inicio, hora_fin, motivo, nombre_archivo))

        conn.commit()
        cur.close()
        conn.close()

        return render_template(TEMPLATE_SOLICITAR_TIEMPO_EXTRA, mensaje="Solicitud enviada correctamente.")

    return render_template(TEMPLATE_SOLICITAR_TIEMPO_EXTRA)


@main_bp.route('/supervisor/tiempo-extra', methods=['GET', 'POST'])
@login_required
def revisar_tiempo_extra():
    from .database import get_connection

    if current_user.role != 'supervisor':
        return redirect(url_for(LOGIN_ROUTE))

    documento = current_user.documento
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        id_solicitud = request.form.get('id_solicitud')
        accion = request.form.get('accion')

        if id_solicitud and accion in ['aprobar', 'rechazar']:
            nuevo_estado = 'Aprobado' if accion == 'aprobar' else 'Rechazado'
            cur.execute("""
                UPDATE tiempo_extra
                SET estado = %s
                WHERE id = %s
            """, (nuevo_estado, id_solicitud))
            conn.commit()
            flash('Solicitud actualizada exitosamente.', 'success')

        return redirect(url_for('main.revisar_tiempo_extra'))

    cur.execute("""
        SELECT te.id, e.nombre, e.apellido, te.fecha, te.hora_inicio, te.hora_fin,
               te.motivo, te.archivo_justificacion, te.estado
        FROM tiempo_extra te
        JOIN empleado e ON te.documento_empleado = e.documento
        JOIN empleado_supervisor es ON e.id_empleado = es.id_empleado
        JOIN supervisor s ON s.id_supervisor = es.id_supervisor
        WHERE s.documento = %s
        ORDER BY te.fecha DESC
    """, (documento,))

    solicitudes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(TEMPLATE_REVISAR_TIEMPO_EXTRA, solicitudes=solicitudes)


@main_bp.route('/descargar/justificativo/<filename>')
@login_required
def descargar_justificativo(filename):
    import os
    from flask import current_app
    ruta = os.path.join(current_app.root_path, 'uploads', 'tiempo_extra')
    return send_from_directory(ruta, filename, as_attachment=True)


@main_bp.route('/empleado/mis_solicitudes_tiempo-extra', methods=['GET'])
@login_required
def ver_tiempo_extra_empleado():
    from .database import get_connection

    if current_user.role != 'empleado':
        return redirect(url_for(LOGIN_ROUTE))

    documento = current_user.documento
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, fecha, hora_inicio, hora_fin, motivo, archivo_justificacion, estado
        FROM tiempo_extra
        WHERE documento_empleado = %s
        ORDER BY fecha DESC
    """, (documento,))

    solicitudes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(TEMPLATE_VER_SOLICITUDES_EXTRA, solicitudes=solicitudes)


@main_bp.route('/supervisor/avisos', methods=['GET', 'POST'])
@login_required
def enviar_aviso():
    from .database import get_connection
    import os
    from werkzeug.utils import secure_filename
    from flask import current_app

    if current_user.role != 'supervisor':
        return redirect(url_for(LOGIN_ROUTE))

    documento_supervisor = current_user.documento
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        id_empleado = request.form.get('id_empleado')
        archivo = request.files.get('archivo')

        if id_empleado and archivo:
            filename = secure_filename(archivo.filename)
            ruta_guardado = os.path.join(current_app.root_path, 'uploads', 'avisos')
            os.makedirs(ruta_guardado, exist_ok=True)
            archivo.save(os.path.join(ruta_guardado, filename))

            cur.execute(SQL_SELECT_ID_SUPERVISOR, (documento_supervisor,))
            supervisor = cur.fetchone()

            if supervisor:
                id_supervisor = supervisor[0]
                cur.execute("""
                    INSERT INTO avisos (id_empleado, id_supervisor, archivo_justificativo)
                    VALUES (%s, %s, %s)
                """, (id_empleado, id_supervisor, filename))
                conn.commit()
                flash('Aviso enviado exitosamente.', 'success')
                return redirect(url_for('main.enviar_aviso'))
            else:
                flash('Supervisor no encontrado.', 'danger')

    cur.execute("""
        SELECT e.id_empleado, e.nombre, e.apellido
        FROM empleado e
        JOIN empleado_supervisor es ON e.id_empleado = es.id_empleado
        JOIN supervisor s ON es.id_supervisor = s.id_supervisor
        WHERE s.documento = %s
    """, (documento_supervisor,))
    empleados = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(TEMPLATE_ENVIAR_AVISOS, empleados=empleados)


@main_bp.route('/empleado/avisos', methods=['GET'])
@login_required
def ver_avisos_empleado():
    from .database import get_connection

    if current_user.role != 'empleado':
        return redirect(url_for(LOGIN_ROUTE))

    conn = get_connection()
    cur = conn.cursor()

    documento_empleado = current_user.documento
    cur.execute(SQL_SELECT_ID_EMPLEADO_POR_DOCUMENTO, (documento_empleado,))
    empleado = cur.fetchone()

    if empleado:
        id_empleado = empleado[0]
        cur.execute("""
            SELECT fecha, archivo_justificativo
            FROM avisos
            WHERE id_empleado = %s
            ORDER BY fecha DESC
        """, (id_empleado,))
        avisos = cur.fetchall()
    else:
        avisos = []

    cur.close()
    conn.close()

    return render_template(TEMPLATE_VER_AVISOS, avisos=avisos)


@main_bp.route('/uploads/avisos/<path:filename>')
@login_required
def descargar_aviso(filename):
    import os
    from flask import current_app, send_from_directory

    ruta = os.path.join(current_app.root_path, 'uploads', 'avisos')
    return send_from_directory(ruta, filename)


@main_bp.route('/admin/avisos', methods=['GET'])
@login_required
def ver_avisos_admin():
    from .database import get_connection

    if current_user.role != 'administrador':
        return redirect(url_for(LOGIN_ROUTE))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT a.fecha, e.nombre || ' ' || e.apellido AS empleado,
               s.nombre || ' ' || s.apellido AS supervisor,
               a.archivo_justificativo
        FROM avisos a
        JOIN empleado e ON a.id_empleado = e.id_empleado
        JOIN supervisor s ON a.id_supervisor = s.id_supervisor
        ORDER BY a.fecha DESC
    """)

    avisos = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(TEMPLATE_VER_AVISOS_ADMIN, avisos=avisos)