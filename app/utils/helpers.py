from datetime import datetime, time

def obtener_turno():
    hora_actual = datetime.now().time()

    if time(6, 0) <= hora_actual < time(14, 0):
        return 'mañana'
    elif time(14, 0) <= hora_actual < time(22, 0):
        return 'tarde'
    else:
        return 'noche'