from flask import Flask, render_template, request, redirect, url_for, session
from db import get_connection
from datetime import datetime

app = Flask(__name__, template_folder="Frontend")
app.secret_key = 'supersecreto'

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
                # Verificar si la credencial existe en EMPLEADO
                cur.execute("SELECT NOMBRE, APELLIDO FROM EMPLEADO WHERE CREDENCIAL = %s", (credencial,))
                empleado = cur.fetchone()

                if empleado:
                    nombre_completo = f"{empleado[0]} {empleado[1]}"
                    session['usuario'] = {'credencial': credencial, 'nombre': nombre_completo}

                    # Registrar entrada en la tabla HORARIO
                    cur.execute(
                        "INSERT INTO HORARIO (TIPO, CREDENCIAL, ENTRADA) VALUES (%s, %s, %s)",
                        ('entrada', credencial, datetime.now())
                    )

                    # Obtener ID del horario recién insertado (por ejemplo, con RETURNING si se desea)
                    cur.execute("SELECT MAX(TIPO) FROM HORARIO WHERE CREDENCIAL = %s", (credencial,))
                    horario_id = cur.fetchone()[0]

                    # Insertar log en la tabla LOGS
                    cur.execute(
                        "INSERT INTO LOGS (CREDENCIAL, HORARIO) VALUES (%s, %s)",
                        (credencial, horario_id)
                    )

                    conn.commit()
                    return redirect(url_for('inicio'))

                return "Credencial no registrada", 400

    return render_template("Login.html")

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