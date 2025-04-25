from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from .auth import buscar_usuario_por_documento
from datetime import date
from datetime import datetime
import pytz
from flask import send_from_directory
from .database import get_connection

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        documento = request.form['documento']
        rol, usuario = buscar_usuario_por_documento(documento)

        if usuario:
            session['documento'] = documento
            session['rol'] = rol

            if rol == 'empleado':
                return redirect(url_for('main.empleado_panel'))
            elif rol == 'supervisor':
                return redirect(url_for('main.supervisor_panel'))
            elif rol == 'administrador':
                return redirect(url_for('main.admin_panel'))

        return render_template('login.html', error='Documento no registrado.')

    return render_template('login.html')


@main_bp.route('/panel/empleado')
def empleado_panel():
    return render_template('panel_empleado.html')


@main_bp.route('/panel/supervisor')
def supervisor_panel():
    return render_template('panel_supervisor.html')


@main_bp.route('/panel/admin')
def admin_panel():
    return render_template('panel_admin.html')

@main_bp.route('/empleado/entrada', methods=['GET', 'POST'])
def vista_registro_entrada():
    from .database import get_connection
    from datetime import datetime as dt
    import pytz

    if 'documento' not in session or session.get('rol') != 'empleado':
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        documento = session['documento']
        metodo = request.form['metodo']
        valor = request.form['valor']

        zona_colombia = pytz.timezone('America/Bogota')
        ahora = dt.now(zona_colombia)
        hora_local = ahora.time().replace(microsecond=0)
        hoy = ahora.date()

        conn = get_connection()
        cur = conn.cursor()

        # Verificar si ya hay registro hoy
        cur.execute("""
            SELECT * FROM asistencia 
            WHERE documento_empleado = %s AND fecha = %s
        """, (documento, hoy))
        ya_registrado = cur.fetchone()

        if ya_registrado:
            cur.close()
            conn.close()
            return render_template('registro_entrada.html', error="Ya registraste tu entrada hoy.")

        # Verificar PIN o tarjeta
        campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
        cur.execute(f"""
            SELECT * FROM empleado 
            WHERE documento = %s AND {campo} = %s
        """, (documento, valor))
        empleado = cur.fetchone()

        if not empleado:
            cur.close()
            conn.close()
            return render_template('registro_entrada.html', error="PIN o tarjeta incorrecta.")

        # Obtener id_empleado
        cur.execute("SELECT id_empleado FROM empleado WHERE documento = %s", (documento,))
        id_empleado = cur.fetchone()[0]

        # Obtener horario asignado
        cur.execute("""
            SELECT dias_laborales, hora_entrada, hora_salida
            FROM horarios
            WHERE id_empleado = %s
        """, (id_empleado,))
        horario = cur.fetchone()

        if not horario:
            cur.close()
            conn.close()
            return render_template('registro_entrada.html', error="No tienes un horario asignado.")

        dias_laborales, hora_entrada, hora_salida = horario

        # Validar día laboral
        dias_codigos = {0: 'l', 1: 'm', 2: 'w', 3: 'j', 4: 'v', 5: 's', 6: 'd'}
        dia_actual = dias_codigos[ahora.weekday()]
        if dia_actual not in dias_laborales:
            cur.close()
            conn.close()
            return render_template('registro_entrada.html', error="Hoy no es uno de tus días laborales.")

        # Validar si está dentro del rango de hora (considerando cruce de medianoche)
        if hora_entrada <= hora_salida:
            dentro_de_horario = hora_entrada <= hora_local <= hora_salida
        else:
            dentro_de_horario = hora_local >= hora_entrada or hora_local <= hora_salida

        if not dentro_de_horario:
            cur.close()
            conn.close()
            return render_template(
                'registro_entrada.html',
                error=f"Solo puedes registrar entrada entre {hora_entrada.strftime('%H:%M')} y {hora_salida.strftime('%H:%M')}."
            )

        # Calcular minutos de retraso
        entrada_dt = dt.strptime(str(hora_local), "%H:%M:%S")
        entrada_prog_dt = dt.strptime(str(hora_entrada), "%H:%M:%S")
        minutos_retraso = 0
        if entrada_dt > entrada_prog_dt:
            delta = entrada_dt - entrada_prog_dt
            minutos_retraso = delta.seconds // 60

        # Insertar asistencia
        try:
            cur.execute("""
                INSERT INTO asistencia (documento_empleado, metodo, hora_entrada, fecha, minutos_retraso)
                VALUES (%s, %s, %s, %s, %s)
            """, (documento, metodo, hora_local, hoy, minutos_retraso))
            conn.commit()
            mensaje = (
                f"Entrada registrada con éxito. Llegaste con {minutos_retraso} minutos de retraso."
                if minutos_retraso > 0 else "Entrada registrada a tiempo. ¡Buen trabajo!"
            )
        except Exception as e:
            conn.rollback()
            mensaje = f"Ocurrió un error al registrar la entrada: {str(e).splitlines()[0]}"

        cur.close()
        conn.close()
        return render_template('registro_entrada.html', mensaje=mensaje)

    return render_template('registro_entrada.html')


@main_bp.route('/supervisor/entrada', methods=['GET', 'POST'])
def vista_registro_entrada_supervisor():
    from .database import get_connection
    from datetime import datetime
    import pytz

    if 'documento' not in session or session.get('rol') != 'supervisor':
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        documento = session['documento']
        metodo = request.form['metodo']
        valor = request.form['valor']

        # Obtener hora y fecha local sin microsegundos
        zona_colombia = pytz.timezone('America/Bogota')
        ahora = datetime.now(zona_colombia)
        hora_local = ahora.time().replace(microsecond=0)
        hoy = ahora.date()

        conn = get_connection()
        cur = conn.cursor()

        # Verificar si ya hay registro hoy
        cur.execute("""
            SELECT * FROM asistencia 
            WHERE documento_empleado = %s AND fecha = %s
        """, (documento, hoy))
        ya_registrado = cur.fetchone()

        if ya_registrado:
            cur.close()
            conn.close()
            return render_template('registro_entrada.html', error="Ya registraste tu entrada hoy.")

        # Verificar PIN o tarjeta
        campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
        cur.execute(f"""
            SELECT * FROM supervisor 
            WHERE documento = %s AND {campo} = %s
        """, (documento, valor))
        supervisor = cur.fetchone()

        if not supervisor:
            cur.close()
            conn.close()
            return render_template('registro_entrada.html', error="PIN o tarjeta incorrecta.")

        try:
            # Insertar asistencia
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

        return render_template('registro_entrada.html', mensaje=mensaje)

    return render_template('registro_entrada.html')


@main_bp.route('/admin/entrada', methods=['GET', 'POST'])
def vista_registro_entrada_admin():
    from .database import get_connection
    from datetime import datetime
    import pytz

    if 'documento' not in session or session.get('rol') != 'administrador':
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        documento = session['documento']
        metodo = request.form['metodo']
        valor = request.form['valor']

        zona_colombia = pytz.timezone('America/Bogota')
        ahora = datetime.now(zona_colombia)
        hora_local = ahora.time().replace(microsecond=0)  # ✅ sin microsegundos
        hoy = ahora.date()

        conn = get_connection()
        cur = conn.cursor()

        # Verificar si ya hay registro hoy
        cur.execute("""
            SELECT * FROM asistencia 
            WHERE documento_empleado = %s AND fecha = %s
        """, (documento, hoy))
        ya_registrado = cur.fetchone()

        if ya_registrado:
            cur.close()
            conn.close()
            return render_template('registro_entrada.html', error="Ya registraste tu entrada hoy.")

        # Verificar PIN o tarjeta
        campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
        cur.execute(f"""
            SELECT * FROM administrador 
            WHERE documento = %s AND {campo} = %s
        """, (documento, valor))
        admin = cur.fetchone()

        if not admin:
            cur.close()
            conn.close()
            return render_template('registro_entrada.html', error="PIN o tarjeta incorrecta.")

        try:
            # Insertar asistencia con fecha local
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

        return render_template('registro_entrada.html', mensaje=mensaje)

    return render_template('registro_entrada.html')


@main_bp.route('/empleado/salida', methods=['GET', 'POST'])
def vista_registro_salida():
    from .database import get_connection
    from datetime import datetime
    import pytz

    if 'documento' not in session or session.get('rol') != 'empleado':
        return redirect(url_for('main.login'))

    documento = session['documento']

    if request.method == 'POST':
        metodo = request.form['metodo']
        valor = request.form['valor']

        zona_colombia = pytz.timezone('America/Bogota')
        ahora = datetime.now(zona_colombia)
        hora_local = ahora.time().replace(microsecond=0)
        hoy = ahora.date()

        conn = get_connection()
        cur = conn.cursor()

        # Verificar identidad
        campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
        cur.execute(f"""
            SELECT * FROM empleado 
            WHERE documento = %s AND {campo} = %s
        """, (documento, valor))
        empleado = cur.fetchone()

        if not empleado:
            cur.close()
            conn.close()
            return render_template('registro_salida.html', error="PIN o tarjeta incorrecta.")

        # Verificar asistencia del día sin salida
        cur.execute("""
            SELECT id FROM asistencia 
            WHERE documento_empleado = %s AND fecha = %s AND hora_salida IS NULL
        """, (documento, hoy))
        asistencia = cur.fetchone()

        if not asistencia:
            cur.close()
            conn.close()
            return render_template('registro_salida.html', error="No hay entrada registrada hoy o ya registraste la salida.")

        asistencia_id = asistencia[0]

        # Obtener hora de salida programada
        cur.execute("""
            SELECT h.hora_salida
            FROM horarios h
            JOIN empleado e ON h.id_empleado = e.id_empleado
            WHERE e.documento = %s
        """, (documento,))
        resultado = cur.fetchone()

        mensaje = "Salida registrada con éxito."
        if resultado:
            hora_salida_prog = resultado[0]

            from datetime import datetime as dt

            salida_real = dt.strptime(str(hora_local), "%H:%M:%S")
            salida_prog = dt.strptime(str(hora_salida_prog), "%H:%M:%S")

            # Validar si horario cruza medianoche
            if hora_salida_prog >= hora_local:
                diferencia = (salida_real - salida_prog).total_seconds()
            else:
                # caso cruzando medianoche, ajustar con timedelta
                salida_prog_completa = dt.combine(ahora.date(), hora_salida_prog)
                if hora_local < hora_salida_prog:
                    salida_real_completa = dt.combine(ahora.date(), hora_local)
                else:
                    salida_real_completa = dt.combine(ahora.date(), hora_local)
                diferencia = (salida_real_completa - salida_prog_completa).total_seconds()

            if abs(diferencia) <= 600:
                mensaje += " Saliste a tiempo."
            elif diferencia < -600:
                mensaje += " Saliste antes de tiempo."
            else:
                mensaje += " Saliste después de tu hora."

        # Registrar hora de salida
        cur.execute("""
            UPDATE asistencia 
            SET hora_salida = %s
            WHERE id = %s
        """, (hora_local, asistencia_id))

        conn.commit()
        cur.close()
        conn.close()

        return render_template('registro_salida.html', mensaje=mensaje)

    return render_template('registro_salida.html')


@main_bp.route('/supervisor/salida', methods=['GET', 'POST'])
def vista_registro_salida_supervisor():
    from .database import get_connection
    from datetime import datetime
    import pytz

    if 'documento' not in session or session.get('rol') != 'supervisor':
        return redirect(url_for('main.login'))

    documento = session['documento']

    if request.method == 'POST':
        metodo = request.form['metodo']
        valor = request.form['valor']

        zona_colombia = pytz.timezone('America/Bogota')
        ahora = datetime.now(zona_colombia)
        hora_local = ahora.time().replace(microsecond=0)
        hoy = ahora.date()

        conn = get_connection()
        cur = conn.cursor()

        # Verificar PIN o tarjeta
        campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
        cur.execute(f"""
            SELECT * FROM supervisor 
            WHERE documento = %s AND {campo} = %s
        """, (documento, valor))
        supervisor = cur.fetchone()

        if not supervisor:
            cur.close()
            conn.close()
            return render_template('registro_salida.html', error="PIN o tarjeta incorrecta.")

        # Verificar asistencia del día sin salida
        cur.execute("""
            SELECT id FROM asistencia 
            WHERE documento_empleado = %s AND fecha = %s AND hora_salida IS NULL
        """, (documento, hoy))
        asistencia = cur.fetchone()

        if not asistencia:
            cur.close()
            conn.close()
            return render_template('registro_salida.html', error="No hay entrada registrada hoy o ya registraste la salida.")

        asistencia_id = asistencia[0]

        mensaje = "Salida registrada con éxito."

        try:
            # Intentar obtener hora de salida programada
            cur.execute("""
                SELECT h.hora_salida
                FROM horarios h
                JOIN supervisor s ON h.id_empleado = s.id_supervisor
                WHERE s.documento = %s
            """, (documento,))
            resultado = cur.fetchone()

            if resultado:
                hora_salida_prog = resultado[0]
                from datetime import datetime as dt
                salida_real = dt.strptime(str(hora_local), "%H:%M:%S")
                salida_prog = dt.strptime(str(hora_salida_prog), "%H:%M:%S")

                diferencia = (salida_real - salida_prog).total_seconds()

                if abs(diferencia) <= 600:
                    mensaje += " Saliste a tiempo."
                elif diferencia < -600:
                    mensaje += " Saliste antes de tiempo."
                else:
                    mensaje += " Saliste después de tu hora."
            else:
                mensaje += ""

        except Exception as e:
            conn.rollback()
            mensaje += ""

        # Registrar la salida
        cur.execute("""
            UPDATE asistencia 
            SET hora_salida = %s
            WHERE id = %s
        """, (hora_local, asistencia_id))

        conn.commit()
        cur.close()
        conn.close()

        return render_template('registro_salida.html', mensaje=mensaje)

    return render_template('registro_salida.html')


@main_bp.route('/admin/salida', methods=['GET', 'POST'])
def vista_registro_salida_admin():
    from .database import get_connection
    from datetime import datetime
    import pytz

    if 'documento' not in session or session.get('rol') != 'administrador':
        return redirect(url_for('main.login'))

    documento = session['documento']

    if request.method == 'POST':
        metodo = request.form['metodo']
        valor = request.form['valor']

        zona_colombia = pytz.timezone('America/Bogota')
        ahora = datetime.now(zona_colombia)
        hora_local = ahora.time().replace(microsecond=0)
        hoy = ahora.date()

        conn = get_connection()
        cur = conn.cursor()

        # Verificar PIN o tarjeta
        campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
        cur.execute(f"""
            SELECT * FROM administrador 
            WHERE documento = %s AND {campo} = %s
        """, (documento, valor))
        admin = cur.fetchone()

        if not admin:
            cur.close()
            conn.close()
            return render_template('registro_salida.html', error="PIN o tarjeta incorrecta.")

        # Verificar asistencia del día sin salida
        cur.execute("""
            SELECT id FROM asistencia 
            WHERE documento_empleado = %s AND fecha = %s AND hora_salida IS NULL
        """, (documento, hoy))
        asistencia = cur.fetchone()

        if not asistencia:
            cur.close()
            conn.close()
            return render_template('registro_salida.html', error="No hay entrada registrada hoy o ya registraste la salida.")

        asistencia_id = asistencia[0]

        mensaje = "Salida registrada con éxito."

        try:
            # Intentar obtener hora de salida programada
            cur.execute("""
                SELECT h.hora_salida
                FROM horarios h
                JOIN administrador a ON h.id_empleado = a.id_administrador
                WHERE a.documento = %s
            """, (documento,))
            resultado = cur.fetchone()

            if resultado:
                hora_salida_prog = resultado[0]
                from datetime import datetime as dt
                salida_real = dt.strptime(str(hora_local), "%H:%M:%S")
                salida_prog = dt.strptime(str(hora_salida_prog), "%H:%M:%S")

                diferencia = (salida_real - salida_prog).total_seconds()

                if abs(diferencia) <= 600:
                    mensaje += " Saliste a tiempo."
                elif diferencia < -600:
                    mensaje += " Saliste antes de tiempo."
                else:
                    mensaje += " Saliste después de tu hora."
            else:
                mensaje += ""

        except Exception as e:
            conn.rollback()
            mensaje += " "

        # Registrar la salida
        cur.execute("""
            UPDATE asistencia 
            SET hora_salida = %s
            WHERE id = %s
        """, (hora_local, asistencia_id))

        conn.commit()
        cur.close()
        conn.close()

        return render_template('registro_salida.html', mensaje=mensaje)

    return render_template('registro_salida.html')


@main_bp.route('/admin/asignar-empleados', methods=['GET', 'POST'])
def asignar_empleados():
    from .database import get_connection

    if 'documento' not in session or session.get('rol') != 'administrador':
        return redirect(url_for('main.login'))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        supervisor_id = request.form['supervisor_id']
        empleados_seleccionados = request.form.getlist('empleado_ids')

        if not empleados_seleccionados:
            # Volvemos a cargar supervisores y empleados NO asignados
            cur.execute("SELECT id_supervisor, nombre, apellido FROM supervisor")
            supervisores = cur.fetchall()
            cur.execute("""
                SELECT id_empleado, nombre, apellido FROM empleado
                WHERE id_empleado NOT IN (
                    SELECT id_empleado FROM empleado_supervisor
                )
            """)
            empleados = cur.fetchall()

            cur.close()
            conn.close()
            return render_template(
                'asignar_empleados.html',
                error="Selecciona al menos un empleado.",
                supervisores=supervisores,
                empleados=empleados
            )

        # Insertar asignaciones sin duplicados
        for empleado_id in empleados_seleccionados:
            cur.execute("""
                INSERT INTO empleado_supervisor (id_empleado, id_supervisor)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (empleado_id, supervisor_id))

        conn.commit()

        # Volvemos a cargar supervisores y empleados restantes
        cur.execute("SELECT id_supervisor, nombre, apellido FROM supervisor")
        supervisores = cur.fetchall()
        cur.execute("""
            SELECT id_empleado, nombre, apellido FROM empleado
            WHERE id_empleado NOT IN (
                SELECT id_empleado FROM empleado_supervisor
            )
        """)
        empleados = cur.fetchall()

        cur.close()
        conn.close()

        return render_template(
            'asignar_empleados.html',
            mensaje="Asignación realizada con éxito.",
            supervisores=supervisores,
            empleados=empleados
        )

    # GET: mostrar lista de supervisores y empleados no asignados
    cur.execute("SELECT id_supervisor, nombre, apellido FROM supervisor")
    supervisores = cur.fetchall()
    cur.execute("""
        SELECT id_empleado, nombre, apellido FROM empleado
        WHERE id_empleado NOT IN (
            SELECT id_empleado FROM empleado_supervisor
        )
    """)
    empleados = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('asignar_empleados.html', supervisores=supervisores, empleados=empleados)


@main_bp.route('/admin/gestionar-asignaciones', methods=['GET', 'POST'])
def gestionar_asignaciones():
    from .database import get_connection

    if 'documento' not in session or session.get('rol') != 'administrador':
        return redirect(url_for('main.login'))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        empleado_id = request.form['empleado_id']
        supervisor_id = request.form['supervisor_id']

        cur.execute("""
            DELETE FROM empleado_supervisor
            WHERE id_empleado = %s AND id_supervisor = %s
        """, (empleado_id, supervisor_id))

        conn.commit()

    # Consultar todas las asignaciones actuales
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

    # Agrupar para mostrar
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

    return render_template('gestionar_asignaciones.html', asignaciones=asignaciones)


@main_bp.route('/supervisor/mis-empleados')
def ver_empleados_asignados():
    from .database import get_connection

    if 'documento' not in session or session.get('rol') != 'supervisor':
        return redirect(url_for('main.login'))

    documento = session['documento']

    conn = get_connection()
    cur = conn.cursor()

    # Obtener el ID del supervisor desde su documento
    cur.execute("""
        SELECT id_supervisor FROM supervisor WHERE documento = %s
    """, (documento,))
    result = cur.fetchone()

    if not result:
        cur.close()
        conn.close()
        return render_template('panel_supervisor.html', error="No se pudo encontrar el supervisor.")

    id_supervisor = result[0]

    # Obtener empleados asignados
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

    return render_template('mis_empleados.html', empleados=empleados)


@main_bp.route('/mi-qr')
def ver_mi_qr():
    import qrcode
    import io
    import base64

    if 'documento' not in session:
        return redirect(url_for('main.login'))

    documento = session['documento']
    url = f"http://localhost:5000/registro-qr?doc={documento}"

    # Generar QR en memoria
    qr = qrcode.make(url)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return render_template('mi_qr.html', qr_base64=qr_base64, documento=documento)


@main_bp.route('/admin/asignar-horario', methods=['GET', 'POST'])
def asignar_horario():
    from .database import get_connection

    if 'documento' not in session or session.get('rol') != 'administrador':
        return redirect(url_for('main.login'))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        empleado_id = request.form['empleado_id']
        hora_entrada = request.form['hora_entrada']
        hora_salida = request.form['hora_salida']
        dias = request.form.getlist('dias_laborales')

        if not dias:
            cur.close()
            conn.close()
            return render_template('asignar_horario.html', empleados=[], mensaje="Debe seleccionar al menos un día.")

        dias_string = ''.join(dias)  # Ej: "lmvj"

        # Insertar o actualizar
        cur.execute("""
            INSERT INTO horarios (id_empleado, dias_laborales, hora_entrada, hora_salida)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id_empleado) DO UPDATE
            SET dias_laborales = EXCLUDED.dias_laborales,
                hora_entrada = EXCLUDED.hora_entrada,
                hora_salida = EXCLUDED.hora_salida
        """, (empleado_id, dias_string, hora_entrada, hora_salida))

        conn.commit()
        cur.close()
        conn.close()

        return render_template('asignar_horario.html', empleados=[], mensaje="Horario asignado correctamente.")

    # GET
    cur.execute("""
        SELECT id_empleado, nombre, apellido
        FROM empleado
        WHERE id_empleado NOT IN (
            SELECT id_empleado FROM horarios
        )
    """)
    empleados = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('asignar_horario.html', empleados=empleados)


@main_bp.route('/admin/gestionar-horarios', methods=['GET', 'POST'])
def gestionar_horarios():
    from .database import get_connection

    if 'documento' not in session or session.get('rol') != 'administrador':
        return redirect(url_for('main.login'))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        id_empleado = request.form['empleado_id']
        nueva_entrada = request.form['hora_entrada']
        nueva_salida = request.form['hora_salida']
        dias = request.form.getlist('dias_laborales')
        dias_string = ''.join(dias)

        cur.execute("""
            UPDATE horarios
            SET hora_entrada = %s,
                hora_salida = %s,
                dias_laborales = %s
            WHERE id_empleado = %s
        """, (nueva_entrada, nueva_salida, dias_string, id_empleado))

        conn.commit()

    # Obtener empleados con horarios
    cur.execute("""
        SELECT e.id_empleado, e.nombre, e.apellido, h.hora_entrada, h.hora_salida, h.dias_laborales
        FROM horarios h
        JOIN empleado e ON h.id_empleado = e.id_empleado
        ORDER BY e.apellido
    """)
    horarios = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('gestionar_horarios.html', horarios=horarios)


def esta_en_horario(documento):
    from .database import get_connection
    from datetime import datetime
    import pytz

    conn = get_connection()
    cur = conn.cursor()

    # Buscar ID del empleado
    cur.execute("SELECT id_empleado FROM empleado WHERE documento = %s", (documento,))
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        return False, "Empleado no encontrado"

    id_empleado = result[0]

    # Buscar horario asignado
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

    # Hora y día actual en Colombia
    zona_colombia = pytz.timezone('America/Bogota')
    ahora = datetime.now(zona_colombia)
    dia_actual = ahora.strftime('%a').lower()[0]  # 'l', 'm', 'w', etc.
    hora_actual = ahora.time()

    cur.close()
    conn.close()

    if dia_actual not in dias_str:
        return False, "Hoy no es uno de tus días laborales"

    if not (hora_entrada <= hora_actual <= hora_salida):
        return False, f"Solo puedes registrar entre {hora_entrada} y {hora_salida}"

    return True, "Horario válido"


@main_bp.route('/supervisor/retrasos')
def ver_retrasos():
    from .database import get_connection

    if 'documento' not in session or session.get('rol') != 'supervisor':
        return redirect(url_for('main.login'))

    documento = session['documento']

    conn = get_connection()
    cur = conn.cursor()

    # Obtener id_supervisor desde su documento
    cur.execute("SELECT id_supervisor FROM supervisor WHERE documento = %s", (documento,))
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        return render_template('panel_supervisor.html', error="No se encontró el supervisor.")

    id_supervisor = result[0]

    # Obtener empleados asignados y sus retrasos
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

    return render_template('reporte_retrasos.html', retrasos=retrasos)


@main_bp.route('/supervisor/retrasos/exportar')
def exportar_retrasos():
    import pandas as pd
    from io import BytesIO
    from flask import send_file

    if 'documento' not in session or session.get('rol') != 'supervisor':
        return redirect(url_for('main.login'))

    documento = session['documento']
    conn = get_connection()
    cur = conn.cursor()

    # Obtener id del supervisor
    cur.execute("SELECT id_supervisor FROM supervisor WHERE documento = %s", (documento,))
    id_supervisor = cur.fetchone()[0]

    # Obtener datos
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

    # Crear DataFrame
    df = pd.DataFrame(rows, columns=['Nombre', 'Apellido', 'Veces tarde', 'Minutos de retraso'])

    # Guardar a Excel en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Retrasos')

    output.seek(0)

    return send_file(output, download_name="reporte_retrasos.xlsx", as_attachment=True)


@main_bp.route('/empleado/tiempo-extra', methods=['GET', 'POST'])
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

    if 'documento' not in session or session.get('rol') != 'empleado':
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        documento = session['documento']
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

        return render_template('solicitar_tiempo_extra.html', mensaje="Solicitud enviada correctamente.")

    return render_template('solicitar_tiempo_extra.html')

@main_bp.route('/supervisor/tiempo-extra', methods=['GET'])
def revisar_tiempo_extra():
    from .database import get_connection

    if 'documento' not in session or session.get('rol') != 'supervisor':
        return redirect(url_for('main.login'))

    documento = session['documento']
    conn = get_connection()
    cur = conn.cursor()

    # Obtener solicitudes de empleados asignados a este supervisor
    cur.execute("""
        SELECT te.id, e.nombre, e.apellido, te.fecha, te.hora_inicio, te.hora_fin,
               te.motivo, te.archivo_justificacion
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

    return render_template('revisar_tiempo_extra.html', solicitudes=solicitudes)


@main_bp.route('/descargar/justificativo/<filename>')
def descargar_justificativo(filename):
    import os
    from flask import current_app
    ruta = os.path.join(current_app.root_path, 'uploads', 'tiempo_extra')
    return send_from_directory(ruta, filename, as_attachment=True)

