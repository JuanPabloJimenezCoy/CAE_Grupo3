from .database import get_connection
from datetime import datetime as dt
import pytz
from flask import render_template

LOGIN_ROUTE = 'main.login'
MENSAJE_PIN_INCORRECTO = "PIN o tarjeta incorrecta."
MENSAJE_NO_ENTRADA_HOY = "No hay entrada registrada hoy o ya registraste la salida."
MENSAJE_SALIDA_REGISTRADA = "Salida registrada con éxito."
TEMPLATE_REGISTRO_ENTRADA = 'registro_entrada.html'
TEMPLATE_REGISTRO_SALIDA = 'registro_salida.html'
MENSAJE_SALISTE_A_TIEMPO = " Saliste a tiempo."
MENSAJE_SALISTE_ANTES = " Saliste antes de tiempo."
MENSAJE_SALISTE_DESPUES = " Saliste después de tu hora."


def buscar_usuario_por_documento(documento):
    """
    Busca un usuario en cualquiera de las tablas por su documento.
    Devuelve una tupla (rol, datos) si lo encuentra, o (None, None) si no.
    """
    conn = get_connection()
    cur = conn.cursor()

    roles = [
        ('administrador', 'administrador'),
        ('supervisor', 'supervisor'),
        ('empleado', 'empleado')
    ]

    for rol, tabla in roles:
        cur.execute(f"SELECT * FROM {tabla} WHERE documento = %s", (documento,))
        usuario = cur.fetchone()
        if usuario:
            cur.close()
            conn.close()
            return rol, usuario

    cur.close()
    conn.close()
    return None, None

def zona_colombia():
    return pytz.timezone('America/Bogota')

def ahora_colombia():
    ahora = dt.now(zona_colombia())
    return ahora.date(), ahora.time().replace(microsecond=0)

def entrada_ya_registrada(cur, documento):
    hoy, _ = ahora_colombia()
    cur.execute("SELECT 1 FROM asistencia WHERE documento_empleado = %s AND fecha = %s", (documento, hoy))
    return cur.fetchone() is not None

def validar_credencial(cur, documento, metodo, valor):
    campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
    cur.execute(f"SELECT 1 FROM empleado WHERE documento = %s AND {campo} = %s", (documento, valor))
    return cur.fetchone() is not None

def obtener_horario(cur, documento):
    cur.execute("SELECT id_empleado FROM empleado WHERE documento = %s", (documento,))
    id_empleado = cur.fetchone()
    if not id_empleado:
        return None
    cur.execute("""
        SELECT dias_laborales, hora_entrada, hora_salida
        FROM horarios
        WHERE id_empleado = %s
    """, (id_empleado[0],))
    row = cur.fetchone()
    if not row:
        return None
    return {'dias_laborales': row[0], 'hora_entrada': row[1], 'hora_salida': row[2]}

def es_dia_laboral(dias_laborales):
    codigos = {0: 'l', 1: 'm', 2: 'w', 3: 'j', 4: 'v', 5: 's', 6: 'd'}
    dia = dt.now(zona_colombia()).weekday()
    return codigos[dia] in dias_laborales

def esta_en_rango_horario(hora_entrada, hora_salida):
    _, hora_actual = ahora_colombia()
    if hora_entrada <= hora_salida:
        return hora_entrada <= hora_actual <= hora_salida
    return hora_actual >= hora_entrada or hora_actual <= hora_salida

def calcular_retraso(hora_entrada):
    _, hora_actual = ahora_colombia()
    entrada_prog = dt.strptime(str(hora_entrada), "%H:%M:%S")
    entrada_real = dt.strptime(str(hora_actual), "%H:%M:%S")
    delta = (entrada_real - entrada_prog).seconds // 60 if entrada_real > entrada_prog else 0
    return delta

def obtener_asistencia_abierta(cur, documento):
    hoy, _ = ahora_colombia()
    cur.execute("""
        SELECT id FROM asistencia 
        WHERE documento_empleado = %s AND fecha = %s AND hora_salida IS NULL
    """, (documento, hoy))
    fila = cur.fetchone()
    return fila[0] if fila else None

def calcular_mensaje_salida(cur, documento):
    _, hora_real = ahora_colombia()

    cur.execute("""
        SELECT h.hora_salida
        FROM horarios h
        JOIN empleado e ON h.id_empleado = e.id_empleado
        WHERE e.documento = %s
    """, (documento,))
    row = cur.fetchone()

    if not row:
        return MENSAJE_SALIDA_REGISTRADA

    hora_prog = row[0]
    salida_real = dt.strptime(str(hora_real), "%H:%M:%S")
    salida_prog = dt.strptime(str(hora_prog), "%H:%M:%S")
    diferencia = (salida_real - salida_prog).total_seconds()

    if abs(diferencia) <= 600:
        return MENSAJE_SALIDA_REGISTRADA + MENSAJE_SALISTE_A_TIEMPO
    elif diferencia < -600:
        return MENSAJE_SALIDA_REGISTRADA + MENSAJE_SALISTE_ANTES
    else:
        return MENSAJE_SALIDA_REGISTRADA + MENSAJE_SALISTE_DESPUES

def registrar_salida(cur, asistencia_id):
    _, hora_salida = ahora_colombia()
    cur.execute("""
        UPDATE asistencia 
        SET hora_salida = %s
        WHERE id = %s
    """, (hora_salida, asistencia_id))

def cerrar_y_render(cur, conn, mensaje):
    cur.close()
    conn.close()
    return render_template(TEMPLATE_REGISTRO_ENTRADA, error=mensaje)


def registrar_asistencia_y_mensaje(cur, conn, documento, metodo, minutos_retraso):
    _, hora_actual = ahora_colombia()
    hoy = dt.now(zona_colombia()).date()
    try:
        cur.execute("""
            INSERT INTO asistencia (documento_empleado, metodo, hora_entrada, fecha, minutos_retraso)
            VALUES (%s, %s, %s, %s, %s)
        """, (documento, metodo, hora_actual, hoy, minutos_retraso))
        conn.commit()
        return (
            f"Entrada registrada con éxito. Llegaste con {minutos_retraso} minutos de retraso."
            if minutos_retraso > 0 else
            "Entrada registrada a tiempo. ¡Buen trabajo!"
        )
    except Exception as e:
        conn.rollback()
        return f"Ocurrió un error al registrar la entrada: {str(e).splitlines()[0]}"
    
def verificar_credencial(cur, documento, metodo, valor, tabla):
    campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
    cur.execute(f"SELECT * FROM {tabla} WHERE documento = %s AND {campo} = %s", (documento, valor))
    return cur.fetchone()

def obtener_asistencia_sin_salida(cur, documento, fecha):
    cur.execute("""
        SELECT id FROM asistencia 
        WHERE documento_empleado = %s AND fecha = %s AND hora_salida IS NULL
    """, (documento, fecha))
    return cur.fetchone()

def obtener_hora_salida_programada(cur, documento, tabla_id, tabla):
    cur.execute(f"""
        SELECT h.hora_salida
        FROM horarios h
        JOIN {tabla} t ON h.id_empleado = t.{tabla_id}
        WHERE t.documento = %s
    """, (documento,))
    result = cur.fetchone()
    return result[0] if result else None

def comparar_salida_programada(hora_prog, hora_real, fecha):
    salida_real = dt.strptime(str(hora_real), "%H:%M:%S")
    salida_prog = dt.strptime(str(hora_prog), "%H:%M:%S")

    if hora_prog >= hora_real:
        diferencia = (salida_real - salida_prog).total_seconds()
    else:
        salida_prog_completa = dt.combine(fecha, hora_prog)
        salida_real_completa = dt.combine(fecha, hora_real)
        diferencia = (salida_real_completa - salida_prog_completa).total_seconds()

    if abs(diferencia) <= 600:
        return MENSAJE_SALISTE_A_TIEMPO
    elif diferencia < -600:
        return MENSAJE_SALISTE_ANTES
    else:
        return MENSAJE_SALISTE_DESPUES
    
def validar_credencial_generico(cur, documento, metodo, valor, tabla):
    campo = 'pin' if metodo == 'pin' else 'tarjeta_id'
    cur.execute(f"SELECT 1 FROM {tabla} WHERE documento = %s AND {campo} = %s", (documento, valor))
    return cur.fetchone() is not None

def calcular_mensaje_salida_admin(cur, documento):
    _, hora_real = ahora_colombia()
    cur.execute("""
        SELECT h.hora_salida
        FROM horarios h
        JOIN administrador a ON h.id_empleado = a.id_admin
        WHERE a.documento = %s
    """, (documento,))
    row = cur.fetchone()
    if not row:
        return MENSAJE_SALIDA_REGISTRADA

    hora_prog = row[0]
    salida_real = dt.strptime(str(hora_real), "%H:%M:%S")
    salida_prog = dt.strptime(str(hora_prog), "%H:%M:%S")
    diferencia = (salida_real - salida_prog).total_seconds()

    if abs(diferencia) <= 600:
        return MENSAJE_SALIDA_REGISTRADA + MENSAJE_SALISTE_A_TIEMPO
    elif diferencia < -600:
        return MENSAJE_SALIDA_REGISTRADA + MENSAJE_SALISTE_ANTES
    else:
        return MENSAJE_SALIDA_REGISTRADA + MENSAJE_SALISTE_DESPUES

def cerrar_y_render_salida(cur, conn, mensaje):
    cur.close()
    conn.close()
    return render_template(TEMPLATE_REGISTRO_SALIDA, error=mensaje)