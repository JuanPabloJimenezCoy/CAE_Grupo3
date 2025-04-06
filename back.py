from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__, template_folder="Frontend")
app.secret_key = 'supersecreto'
empleados = {}

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        metodo = request.form.get('metodo')
        
        if metodo == 'tarjeta':
            num_tarjeta = request.form.get('num_tarjeta')
            if num_tarjeta in empleados and empleados[num_tarjeta]['tipo'] == 'tarjeta':
                session['usuario'] = empleados[num_tarjeta]
                return redirect(url_for('inicio'))
            return "Error: Tarjeta no registrada", 400

        elif metodo == 'pin':
            pin = request.form.get('pin')
            if pin in empleados and empleados[pin]['tipo'] == 'pin':
                session['usuario'] = empleados[pin]
                return redirect(url_for('inicio'))
            return "Error: PIN no registrado", 400

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