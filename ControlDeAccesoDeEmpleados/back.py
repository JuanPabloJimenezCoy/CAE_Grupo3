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
        num_tarjeta = request.form.get('num_tarjeta')
        nombre = request.form.get('nombre')

        if num_tarjeta and nombre:
            empleados[num_tarjeta] = {'num_tarjeta': num_tarjeta, 'nombre': nombre}
            print("Empleado registrado:", empleados)
            return redirect(url_for('login'))
        return "Error: Debes completar todos los campos.", 400

    return render_template('Registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        num_tarjeta = request.form.get('num_tarjeta')

        if num_tarjeta in empleados:
            session['usuario'] = empleados[num_tarjeta]
            return redirect(url_for('inicio'))
        return "Error: Tarjeta no registrada", 400

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