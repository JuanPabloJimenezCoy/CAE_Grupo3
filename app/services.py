from .database import get_connection
from .auth import (
    entrada_ya_registrada,
    validar_credencial,
    obtener_horario,
    es_dia_laboral,
    esta_en_rango_horario,
    calcular_retraso,
    registrar_asistencia_y_mensaje,
    validar_credencial_generico,
    obtener_asistencia_abierta,
    calcular_mensaje_salida_admin,
    registrar_salida
)

#Constantes
ZONA_HORARIA_CO = 'America/Bogota'

def registrar_entrada_empleado(documento, metodo, valor):
    conn = get_connection()
    cur = conn.cursor()

    try:
        if entrada_ya_registrada(cur, documento):
            return "Ya registraste tu entrada hoy."

        if not validar_credencial(cur, documento, metodo, valor):
            return "PIN o tarjeta incorrecta."

        horario = obtener_horario(cur, documento)
        if not horario:
            return "No tienes un horario asignado."

        if not es_dia_laboral(horario['dias_laborales']):
            return "Hoy no es uno de tus días laborales."

        if not esta_en_rango_horario(horario['hora_entrada'], horario['hora_salida']):
            return f"Solo puedes registrar entrada entre {horario['hora_entrada']} y {horario['hora_salida']}."

        minutos_retraso = calcular_retraso(horario['hora_entrada'])
        mensaje = registrar_asistencia_y_mensaje(cur, conn, documento, metodo, minutos_retraso)

        return mensaje
    finally:
        cur.close()
        conn.close()


def registrar_salida_admin(documento, metodo, valor):
    from .database import get_connection

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Verificar credencial (usa tu función auxiliar)
        if not validar_credencial_generico(cur, documento, metodo, valor, 'administrador'):
            return "PIN o tarjeta incorrecta."

        # Verificar si hay asistencia abierta
        asistencia_id = obtener_asistencia_abierta(cur, documento)
        if not asistencia_id:
            return "No has registrado entrada hoy."

        # Calcular el mensaje de salida
        mensaje = calcular_mensaje_salida_admin(cur, documento)

        # Registrar la salida en la base
        registrar_salida(cur, asistencia_id)
        conn.commit()
        return mensaje

    except Exception as e:
        conn.rollback()
        return f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()


def obtener_retrasos_supervisor(documento):
    from .database import get_connection

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id_supervisor FROM supervisor WHERE documento = %s", (documento,))
        result = cur.fetchone()
        if not result:
            return None, "No se encontró el supervisor."

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

        return retrasos, None

    except Exception as e:
        return None, f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()


def obtener_empleados_asignados(documento):
    from .database import get_connection

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id_supervisor FROM supervisor WHERE documento = %s", (documento,))
        result = cur.fetchone()
        if not result:
            return None, "No se pudo encontrar el supervisor."

        id_supervisor = result[0]

        cur.execute("""
            SELECT e.nombre, e.apellido
            FROM empleado_supervisor es
            JOIN empleado e ON es.id_empleado = e.id_empleado
            WHERE es.id_supervisor = %s
            ORDER BY e.apellido
        """, (id_supervisor,))
        empleados = cur.fetchall()

        return empleados, None

    except Exception as e:
        return None, f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()


def registrar_tiempo_extra(documento, fecha, hora_inicio, hora_fin, motivo, archivo):
    from .database import get_connection
    from flask import current_app
    import os
    from werkzeug.utils import secure_filename

    def archivo_valido(nombre):
        return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in {
            'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'
        }

    nombre_archivo = None
    if archivo and archivo.filename and archivo_valido(archivo.filename):
        nombre_archivo = f"{documento}_{fecha}_{secure_filename(archivo.filename)}"
        ruta_guardado = os.path.join(current_app.root_path, 'uploads', 'tiempo_extra', nombre_archivo)
        os.makedirs(os.path.dirname(ruta_guardado), exist_ok=True)
        archivo.save(ruta_guardado)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO tiempo_extra (
                documento_empleado, fecha, hora_inicio, hora_fin, motivo, archivo_justificacion
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (documento, fecha, hora_inicio, hora_fin, motivo, nombre_archivo))
        conn.commit()
        return "Solicitud enviada correctamente."

    except Exception as e:
        conn.rollback()
        return f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()


def enviar_aviso_supervisor(documento_supervisor, id_empleado, archivo):
    from .database import get_connection
    import os
    from werkzeug.utils import secure_filename
    from flask import current_app

    if not id_empleado or not archivo:
        return False, 'Faltan datos para enviar el aviso.'

    filename = secure_filename(archivo.filename)
    ruta_guardado = os.path.join(current_app.root_path, 'uploads', 'avisos')
    os.makedirs(ruta_guardado, exist_ok=True)
    archivo.save(os.path.join(ruta_guardado, filename))

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id_supervisor FROM supervisor WHERE documento = %s", (documento_supervisor,))
        supervisor = cur.fetchone()

        if not supervisor:
            return False, 'Supervisor no encontrado.'

        id_supervisor = supervisor[0]

        cur.execute("""
            INSERT INTO avisos (id_empleado, id_supervisor, archivo_justificativo)
            VALUES (%s, %s, %s)
        """, (id_empleado, id_supervisor, filename))
        conn.commit()
        return True, 'Aviso enviado exitosamente.'

    except Exception as e:
        conn.rollback()
        return False, f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()


def obtener_solicitudes_tiempo_extra(documento):
    from .database import get_connection

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, fecha, hora_inicio, hora_fin, motivo, archivo_justificacion, estado
            FROM tiempo_extra
            WHERE documento_empleado = %s
            ORDER BY fecha DESC
        """, (documento,))
        solicitudes = cur.fetchall()
        return solicitudes, None

    except Exception as e:
        return None, f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()


def obtener_solicitudes_tiempo_extra_supervisor(documento):
    from .database import get_connection

    conn = get_connection()
    cur = conn.cursor()

    try:
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
        return solicitudes, None

    except Exception as e:
        return None, f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()


def actualizar_estado_tiempo_extra(id_solicitud, accion):
    from .database import get_connection

    if accion not in ['aprobar', 'rechazar']:
        return False, 'Acción no válida.'

    nuevo_estado = 'Aprobado' if accion == 'aprobar' else 'Rechazado'

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE tiempo_extra
            SET estado = %s
            WHERE id = %s
        """, (nuevo_estado, id_solicitud))
        conn.commit()
        return True, 'Solicitud actualizada exitosamente.'

    except Exception as e:
        conn.rollback()
        return False, f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()


def obtener_avisos_empleado(documento_empleado):
    from .database import get_connection

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id_empleado FROM empleado WHERE documento = %s", (documento_empleado,))
        empleado = cur.fetchone()

        if not empleado:
            return [], None  # No hay empleado, lista vacía

        id_empleado = empleado[0]

        cur.execute("""
            SELECT fecha, archivo_justificativo
            FROM avisos
            WHERE id_empleado = %s
            ORDER BY fecha DESC
        """, (id_empleado,))
        avisos = cur.fetchall()
        return avisos, None

    except Exception as e:
        return None, f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()


def obtener_avisos_admin():
    from .database import get_connection

    conn = get_connection()
    cur = conn.cursor()

    try:
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
        return avisos, None

    except Exception as e:
        return None, f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()


def gestionar_asignaciones_admin(request_form):
    from .database import get_connection

    conn = get_connection()
    cur = conn.cursor()
    mensaje = None
    error = None

    try:
        if 'supervisor_id' in request_form and 'empleado_ids' in request_form:
            # Asignación de empleados a supervisor
            supervisor_id = request_form['supervisor_id']
            empleados_seleccionados = request_form.getlist('empleado_ids')

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

        elif 'empleado_id' in request_form and 'supervisor_id_eliminar' in request_form:
            # Eliminación de asignación
            empleado_id = request_form['empleado_id']
            supervisor_id = request_form['supervisor_id_eliminar']

            cur.execute("""
                DELETE FROM empleado_supervisor
                WHERE id_empleado = %s AND id_supervisor = %s
            """, (empleado_id, supervisor_id))
            conn.commit()
            mensaje = "Asignación eliminada con éxito."

        # Obtener supervisores
        cur.execute("SELECT id_supervisor, nombre, apellido FROM supervisor")
        supervisores = cur.fetchall()

        # Obtener empleados no asignados
        cur.execute("""
            SELECT id_empleado, nombre, apellido FROM empleado
            WHERE id_empleado NOT IN (
                SELECT id_empleado FROM empleado_supervisor
            )
        """)
        empleados_no_asignados = cur.fetchall()

        # Obtener registros actuales
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

        # Organizar en diccionario
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

        return {
            'mensaje': mensaje,
            'error': error,
            'supervisores': supervisores,
            'empleados': empleados_no_asignados,
            'asignaciones': asignaciones
        }

    except Exception as e:
        conn.rollback()
        return {'mensaje': None, 'error': f"Ocurrió un error: {str(e).splitlines()[0]}"}

    finally:
        cur.close()
        conn.close()


def registrar_entrada_admin(documento, metodo, valor):
    from .database import get_connection
    from datetime import datetime
    import pytz

    zona_colombia = pytz.timezone(ZONA_HORARIA_CO)
    ahora = datetime.now(zona_colombia)
    hora_local = ahora.time().replace(microsecond=0)
    hoy = ahora.date()

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Verificar entrada hoy
        cur.execute("""
            SELECT 1 FROM asistencia 
            WHERE documento_empleado = %s AND fecha = %s
        """, (documento, hoy))
        if cur.fetchone():
            return "Ya registraste tu entrada hoy administrador."

        # Verificar credencial
        campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
        cur.execute(f"""
            SELECT 1 FROM administrador 
            WHERE documento = %s AND {campo} = %s
        """, (documento, valor))
        if not cur.fetchone():
            return "PIN o tarjeta incorrecta."

        # Registrar entrada
        cur.execute("""
            INSERT INTO asistencia (documento_empleado, metodo, hora_entrada, fecha)
            VALUES (%s, %s, %s, %s)
        """, (documento, metodo, hora_local, hoy))
        conn.commit()
        return "Entrada registrada con éxito."

    except Exception as e:
        conn.rollback()
        return f"Ocurrió un error: {str(e).splitlines()[0]}"

    finally:
        cur.close()
        conn.close()
        
