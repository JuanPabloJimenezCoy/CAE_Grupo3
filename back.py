from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__, template_folder="Frontend")
app.secret_key = 'supersecreto'
from datetime import datetime
empleados = {}
# Registrar al admin como empleado al inicio
empleados['7854'] = {'tipo': 'admin', 'pin': '7854', 'nombre': 'Administrador'}
registro_accesos = []

@app.route("/")
def home():
    return render_template("Login.html")

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        metodo = request.form.get('metodo')
        nombre = request.form.get('nombre')

        if metodo == 'tarjeta':
            num_tarjeta = request.form.get('num_tarjeta')
            if num_tarjeta and nombre:
                empleados[num_tarjeta] = {'tipo': 'tarjeta', 'num_tarjeta': num_tarjeta, 'nombre': nombre}
                print("Empleado registrado con tarjeta:", empleados)
                return redirect(url_for('login'))
            return "Error: Debes completar todos los campos.", 400

        elif metodo == 'pin':
            pin = request.form.get('pin')
            if pin and nombre and pin.isdigit() and len(pin) == 6:
                empleados[pin] = {'tipo': 'pin', 'pin': pin, 'nombre': nombre}
                print("Empleado registrado con PIN:", empleados)
                return redirect(url_for('login'))
            return "Error: El PIN debe tener exactamente 6 dígitos.", 400

    return render_template('Registro.html')

@app.route('/historial')
def historial():
    return render_template('Historial.html', accesos=registro_accesos)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        metodo = request.form.get('metodo')
        
        if metodo == 'tarjeta':
            num_tarjeta = request.form.get('num_tarjeta')
            if num_tarjeta in empleados and empleados[num_tarjeta]['tipo'] == 'tarjeta':
                session['usuario'] = empleados[num_tarjeta]
                registro_accesos.append({
                    'nombre': empleados[num_tarjeta]['nombre'],
                    'metodo': 'tarjeta',
                    'hora': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                return redirect(url_for('inicio'))
            return "Error: Tarjeta no registrada", 400

        elif metodo == 'pin':
            pin = request.form.get('pin')
            if pin in empleados and empleados[pin]['tipo'] == 'pin':
                session['usuario'] = empleados[pin]
                registro_accesos.append({
                    'nombre': empleados[pin]['nombre'],
                    'metodo': 'pin',
                    'hora': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                return redirect(url_for('inicio'))
            return "Error: PIN no registrado", 400
        
        elif metodo == 'admin':
             codigo_admin = '7854'
             if request.form.get('codigo') == codigo_admin:
                    session['usuario'] = {'nombre': 'Administrador', 'tipo': 'admin'}
                    return redirect(url_for('inicio_admin'))
        return "Error: Código de administrador incorrecto", 400

    return render_template("Login.html")

@app.route('/inicio_admin')
def inicio_admin():
    if 'usuario' in session and session['usuario']['tipo'] == 'admin':
        return render_template('InicioAdministrador.html', accesos=registro_accesos, empleados=empleados)
    return redirect(url_for('home'))

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