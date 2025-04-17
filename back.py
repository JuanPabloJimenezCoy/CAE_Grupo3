from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
from db import get_connection
from datetime import datetime, time
import random
import string
import uuid  # Para generación de UUIDs

app = Flask(__name__, template_folder="Frontend")
app.secret_key = 'supersecreto'

def generar_id_numerico():
    """Genera un ID numérico de 10 dígitos que cabe en un INTEGER"""
    return random.randint(1000000000, 2147483647)  # Rango seguro para INT

def generar_codigo_temporal():
    """Genera código con timestamp + random (ej: '141523_4297')"""
    timestamp = datetime.now().strftime("%H%M%S")
    random_num = random.randint(1000, 9999)
    return f"{timestamp}_{random_num}"

def obtener_turno():
    """
    Devuelve el turno actual (mañana/tarde/noche) concatenado con un código único
    Formato: 'mañana_162304_4297', 'tarde_162305_5832', etc.
    """
    hora_actual = datetime.now().time()
    
    # Determinar el turno base
    if time(6, 0) <= hora_actual < time(14, 0):
        turno_base = 'mañana'
    elif time(14, 0) <= hora_actual < time(22, 0):
        turno_base = 'tarde'
    else:
        turno_base = 'noche'
    
    # Combinar turno con código temporal
    return f"{turno_base}_{generar_codigo_temporal()}"
    
# Decorador para verificar roles
def rol_requerido(rol_necesario):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario' not in session or session['usuario']['rol'] != rol_necesario:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Panel de administrador
@app.route('/admin')
@rol_requerido('admin')
def panel_admin():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT credencial, nombre, apellido, cargo FROM empleado")
            empleados = cur.fetchall()
    return render_template("InicioAdministrador.html", 
                         usuario=session['usuario'],
                         empleados=empleados)

# Panel de supervisor
@app.route('/supervisor')
@rol_requerido('supervisor')
def panel_supervisor():
    return render_template("panel_supervisor.html", usuario=session['usuario'])

# Panel de empleado
@app.route('/inicio')
@rol_requerido('empleado')
def inicio():
    # Obtener solo los datos necesarios
    usuario_data = {
        'nombre_completo': session['usuario']['nombre'],
        'hora_login': session['usuario']['hora_login']
    }
    return render_template("Inicio.html", usuario=usuario_data)
    
@app.route("/")
def home():
    return render_template("Login.html")

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        credencial = request.form.get('credencial')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        cargo = request.form.get('cargo')
        horario = request.form.get('horario')

        with get_connection() as conn:
            with conn.cursor() as cur:
                # Verificar si la credencial ya existe
                cur.execute("SELECT * FROM EMPLEADO WHERE CREDENCIAL = %s", (credencial,))
                existente = cur.fetchone()

                if existente:
                    return render_template("Registro.html", error="Credencial ya existe")

                # Insertar el nuevo empleado
                cur.execute("""
                    INSERT INTO EMPLEADO (CREDENCIAL, CARGO, NOMBRE, APELLIDO, HORARIO)
                    VALUES (%s, %s, %s, %s, %s)
                """, (credencial, cargo, nombre, apellido, horario))
                conn.commit()

                return redirect(url_for('home'))

    return render_template("Registro.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        credencial = request.form.get('credencial')
        rol = request.form.get('rol')

        if not credencial or not credencial.isdigit():
            return render_template("Login.html", error="Credencial inválida")

        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    usuario = None
                    tipo_usuario = None
                    
                    # Verificación según rol
                    if rol == 'admin':
                        cur.execute("SELECT id_admin, nombre, apellido FROM administrador WHERE id_admin = %s", (credencial,))
                        tipo_usuario = 'admin'
                    elif rol == 'supervisor':
                        cur.execute("SELECT id_supervisor, nombre, apellido FROM supervisor WHERE id_supervisor = %s", (credencial,))
                        tipo_usuario = 'supervisor'
                    else:
                        cur.execute("SELECT credencial, nombre, apellido FROM empleado WHERE credencial = %s", (credencial,))
                        tipo_usuario = 'empleado'

                    usuario = cur.fetchone()
                    if not usuario:
                        return render_template("Login.html", error="Credencial no encontrada")

                    # Generar identificadores únicos
                    id_unico = generar_id_numerico()
                    hora_actual = datetime.now()

                    if tipo_usuario == 'empleado':
                        turno = obtener_turno()
                        # Registro detallado para empleados
                        cur.execute(
                            "INSERT INTO horario (tipo, credencial, entrada) VALUES (%s, %s, %s)",
                            (turno, credencial, hora_actual)
                        )
                        # Registrar en logs con el mismo turno
                        cur.execute(
                            "INSERT INTO logs (id_log, credencial, horario) VALUES (%s, %s, %s)",
                            (id_unico, credencial, turno)
                        )
                    else:
                        # Para admin/supervisor, usar código de acceso único
                        codigo_acceso = f"acceso_{tipo_usuario}_{generar_codigo_temporal()}"
                        cur.execute(
                            "INSERT INTO logs (id_log, credencial, horario) VALUES (%s, %s, %s)",
                            (id_unico, credencial, codigo_acceso)
                        )

                    conn.commit()
                    
                    # Configurar sesión
                    session['usuario'] = {
                        'id': usuario[0],
                        'nombre': f"{usuario[1]} {usuario[2]}",
                        'rol': tipo_usuario,
                        'hora_login': hora_actual.strftime('%Y-%m-%d %H:%M:%S'),
                        'codigo_acceso': id_unico
                    }
                    
                    # Redirección según rol
                    if tipo_usuario == 'admin':
                        return redirect(url_for('panel_admin'))
                    elif tipo_usuario == 'supervisor':
                        return redirect(url_for('panel_supervisor'))
                    else:
                        return redirect(url_for('inicio'))

                except Exception as e:
                    conn.rollback()
                    app.logger.error(f"Error en login: {str(e)}")
                    return render_template("Login.html", error="Error al iniciar sesión")

    return render_template("Login.html")

@app.route('/logout')
def logout():
    if 'usuario' in session:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Registrar hora de salida para empleados
                    if session['usuario']['rol'] == 'empleado':
                        cur.execute("""
                            UPDATE horario 
                            SET salida = %s 
                            WHERE credencial = %s AND salida IS NULL
                        """, (datetime.now(), session['usuario']['id']))
                    conn.commit()
        except Exception as e:
            app.logger.error(f"Error al registrar salida: {e}")
    
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)