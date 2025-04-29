from .database import get_connection
from datetime import datetime as dt
import pytz

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