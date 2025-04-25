from .database import get_connection

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