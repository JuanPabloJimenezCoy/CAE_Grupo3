from flask import Flask, render_template, request, redirect, url_for, session
from db import get_connection
from datetime import datetime, time
import random
import string

app = Flask(__name__, template_folder="Frontend")
app.secret_key = 'supersecreto'

def generar_id_aleatorio():
    """Genera un ID aleatorio de 8 dígitos numéricos"""
    return ''.join(random.choices(string.digits, k=8))

def obtener_turno_actual():
    """Devuelve solo 'mañana', 'tarde' o 'noche'"""
    hora_actual = datetime.now().time()
    if time(8, 0) <= hora_actual < time(16, 0):
        return 'mañana'
    elif time(14, 0) <= hora_actual < time(22, 0):
        return 'tarde'
    else:
        return 'noche'
    
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

        with get_connection() as conn:
            with conn.cursor() as cur:
                # Verificar si la credencial ya existe
                cur.execute("SELECT * FROM EMPLEADO WHERE CREDENCIAL = %s", (credencial,))
                existente = cur.fetchone()

                if existente:
                    return "Ya existe un empleado con esa credencial.", 400

                # Insertar el nuevo empleado
                cur.execute("""
                    INSERT INTO EMPLEADO (CREDENCIAL, CARGO, NOMBRE, APELLIDO)
                    VALUES (%s, %s, %s, %s)
                """, (credencial, cargo, nombre, apellido))
                conn.commit()

                return redirect(url_for('home'))  # o podrías ir directo al login

    return render_template("Registro.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        credencial = request.form.get('credencial')
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    # 1. Verificar empleado
                    cur.execute("SELECT nombre, apellido FROM empleado WHERE credencial = %s", (credencial,))
                    empleado = cur.fetchone()
                    
                    if not empleado:
                        return render_template("Login.html", error="Credencial no existe")

                    # 2. Obtener turno actual
                    turno = obtener_turno_actual()
                    hora_entrada = datetime.now()

                    # 3. Primero insertar en HORARIO (para que exista la referencia)
                    tipo_horario = f"horario_{turno}_{credencial}_{hora_entrada.strftime('%Y%m%d%H%M%S')}"
                    cur.execute(
                        "INSERT INTO horario (tipo, credencial, entrada) VALUES (%s, %s, %s) RETURNING tipo",
                        (tipo_horario, credencial, hora_entrada)
                    )
                    tipo_horario = cur.fetchone()[0]

                    # 4. Ahora insertar en LOGS (con referencia válida)
                    cur.execute(
                        "INSERT INTO logs (id_log, credencial, horario) VALUES (%s, %s, %s)",
                        (generar_id_aleatorio(), credencial, tipo_horario)
                    )
                    
                    conn.commit()
                    
                    session['usuario'] = {
                        'credencial': credencial,
                        'nombre': f"{empleado[0]} {empleado[1]}",
                        'turno': turno,
                        'hora_login': hora_entrada.strftime('%H:%M:%S')
                    }
                    return redirect(url_for('inicio'))
                
                except Exception as e:
                    conn.rollback()
                    app.logger.error(f"Error en login: {str(e)}")
                    return render_template("Login.html", error="Error al iniciar sesión")

    return render_template("Login.html")

@app.route('/logout')
def logout():
    # Registrar hora de salida si es necesario
    if 'usuario' in session:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE HORARIO 
                        SET SALIDA = %s 
                        WHERE CREDENCIAL = %s 
                        AND SALIDA IS NULL
                    """, (datetime.now(), session['usuario']['credencial']))
                    conn.commit()
        except Exception as e:
            app.logger.error(f"Error al registrar salida: {e}")
    
    session.clear()
    return redirect(url_for('login'))

@app.route('/inicio')
def inicio():
    if 'usuario' in session:
        return render_template('Inicio.html', usuario=session['usuario']['nombre'])
    return redirect(url_for('home'))

@app.route('/salir')
def salir():
    session.pop('usuario', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)