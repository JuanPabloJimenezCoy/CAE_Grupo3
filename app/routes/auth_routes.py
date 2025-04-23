from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from datetime import datetime
from app.db import get_connection
from app.utils.helpers import obtener_turno

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def home():
    return render_template("login.html")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        metodo = request.form.get('metodo')  # 'pin' o 'tarjeta'
        valor = request.form.get('valor')
        rol = request.form.get('rol')

        if not valor:
            return render_template("login.html", error="Debes ingresar un valor.")

        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    usuario = None
                    tipo_usuario = rol

                    # Armar consulta según rol y método
                    if rol == 'empleado':
                        if metodo == 'tarjeta':
                            query = "SELECT credencial, nombre, apellido, pin, tarjeta_id FROM empleado WHERE tarjeta_id = %s"
                        else:
                            query = "SELECT credencial, nombre, apellido, pin, tarjeta_id FROM empleado WHERE pin = %s"
                    elif rol == 'supervisor':
                        if metodo == 'tarjeta':
                            query = "SELECT id_supervisor, nombre, apellido, pin, tarjeta_id FROM supervisor WHERE tarjeta_id = %s"
                        else:
                            query = "SELECT id_supervisor, nombre, apellido, pin, tarjeta_id FROM supervisor WHERE pin = %s"
                    elif rol == 'admin':
                        if metodo == 'tarjeta':
                            query = "SELECT id_admin, nombre, apellido, pin, tarjeta_id FROM administrador WHERE tarjeta_id = %s"
                        else:
                            query = "SELECT id_admin, nombre, apellido, pin, tarjeta_id FROM administrador WHERE pin = %s"
                    else:
                        return render_template("login.html", error="Rol no válido.")

                    # Ejecutar la consulta
                    cur.execute(query, (valor,))
                    usuario = cur.fetchone()

                    if not usuario:
                        return render_template("login.html", error="Usuario no encontrado.")

                    hora_actual = datetime.now()
                    turno = obtener_turno()
                    id_horario = None  # Inicializamos para poder usarlo en logs

                    if tipo_usuario == 'empleado':
                        # Insertar en horario
                        cur.execute("""
                            INSERT INTO horario (tipo, credencial, entrada)
                            VALUES (%s, %s, %s)
                            RETURNING id_horario
                        """, (turno, usuario[0], hora_actual))
                        id_horario = cur.fetchone()[0]

                    # Insertar en logs (ahora con usuario_id y rol)
                    cur.execute("""
                        INSERT INTO logs (usuario_id, id_horario, rol)
                        VALUES (%s, %s, %s)
                    """, (usuario[0], id_horario, tipo_usuario))

                    conn.commit()

                    # Guardar sesión
                    session['usuario'] = {
                        'id': usuario[0],
                        'nombre': f"{usuario[1]} {usuario[2]}",
                        'rol': tipo_usuario,
                        'hora_login': hora_actual.strftime('%Y-%m-%d %H:%M:%S')
                    }

                    # Redirigir al panel correspondiente
                    if tipo_usuario == 'admin':
                        return redirect(url_for('admin.panel_admin'))
                    elif tipo_usuario == 'supervisor':
                        return redirect(url_for('supervisor.panel_supervisor'))
                    else:
                        return redirect(url_for('empleado.inicio'))

                except Exception as e:
                    conn.rollback()
                    current_app.logger.error(f"Error en login: {str(e)}")
                    return render_template("login.html", error="Error al iniciar sesión")

    return render_template("login.html")

@auth_bp.route('/logout')
def logout():
    if 'usuario' in session:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    if session['usuario']['rol'] == 'empleado':
                        cur.execute("""
                            UPDATE horario
                            SET salida = %s
                            WHERE credencial = %s AND salida IS NULL
                        """, (datetime.now(), session['usuario']['id']))
                conn.commit()
        except Exception as e:
            current_app.logger.error(f"Error al registrar salida: {e}")

    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        rol = request.form.get('rol')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        pin = request.form.get('pin') or None  # Convertir "" a None
        tarjeta = request.form.get('tarjeta') or None

        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    if rol == 'empleado':
                        credencial = request.form.get('credencial')
                        cargo = request.form.get('cargo')
                        horario = request.form.get('horario')

                        # Validar campos obligatorios
                        if not credencial or not tarjeta:
                            return render_template("registro.html", error="Credencial y tarjeta son obligatorias para empleados.")

                        # Verificar que no exista ya esa credencial o tarjeta
                        cur.execute("SELECT * FROM empleado WHERE credencial = %s OR tarjeta_id = %s", (credencial, tarjeta))
                        if cur.fetchone():
                            return render_template("registro.html", error="Credencial o tarjeta ya registrada.")

                        cur.execute("""
                            INSERT INTO empleado (credencial, nombre, apellido, cargo, horario, pin, tarjeta_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (credencial, nombre, apellido, cargo, horario, pin, tarjeta))

                    elif rol == 'supervisor':
                        if not tarjeta:
                            return render_template("registro.html", error="La tarjeta es obligatoria para supervisores.")

                        # Verificar duplicado
                        cur.execute("SELECT * FROM supervisor WHERE tarjeta_id = %s", (tarjeta,))
                        if cur.fetchone():
                            return render_template("registro.html", error="Tarjeta ya registrada para otro supervisor.")

                        cur.execute("""
                            INSERT INTO supervisor (nombre, apellido, pin, tarjeta_id)
                            VALUES (%s, %s, %s, %s)
                        """, (nombre, apellido, pin, tarjeta))

                    elif rol == 'admin':
                        if not tarjeta:
                            return render_template("registro.html", error="La tarjeta es obligatoria para administradores.")

                        # Verificar duplicado
                        cur.execute("SELECT * FROM administrador WHERE tarjeta_id = %s", (tarjeta,))
                        if cur.fetchone():
                            return render_template("registro.html", error="Tarjeta ya registrada para otro administrador.")

                        cur.execute("""
                            INSERT INTO administrador (nombre, apellido, pin, tarjeta_id)
                            VALUES (%s, %s, %s, %s)
                        """, (nombre, apellido, pin, tarjeta))

                    conn.commit()
                    return redirect(url_for('auth.login'))

                except Exception as e:
                    conn.rollback()
                    current_app.logger.error(f"Error en registro: {e}")
                    return render_template("registro.html", error="Error al registrar usuario.")

    return render_template("registro.html")