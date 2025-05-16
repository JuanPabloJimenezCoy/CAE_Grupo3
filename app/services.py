from .database import get_connection
from .auth import (
    entrada_ya_registrada,
    validar_credencial,
    obtener_horario,
    es_dia_laboral,
    esta_en_rango_horario,
    calcular_retraso,
    registrar_asistencia_y_mensaje
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
