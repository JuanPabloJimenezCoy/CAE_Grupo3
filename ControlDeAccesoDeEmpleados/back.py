from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__, template_folder="Frontend")
app.secret_key = 'supersecreto'
empleados={}

@app.route("/")
def home():
    return render_template("Login.html")

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    num_tarjeta = request.args.get('num_tarjeta')
    if num_tarjeta:
        empleados[num_tarjeta] = {'num_tarjeta':num_tarjeta}
        print("Empleados registrados:", empleados)
        return f"empleado con tarjeta {num_tarjeta} registrado correctamente."
    return "Error: Tiene que poner el numero de la tarjeta.", 400

@app.route('/login', methods = ['GET', 'POST'])
def login():
    num_tarjeta = request.form['num_tarjeta']

    if num_tarjeta in empleados:
        session['usuario'] = empleados[num_tarjeta]
        return redirect(url_for('inicio'))
    return "Error: Tarjeta no registrada"

@app.route('/inicio')
def inicio():
    if 'usuario' in session:
        return render_template('Inicio.html', usuario=session['usuario'])
    return redirect(url_for('home'))

@app.route('/salir')
def salir():
    session.pop('usuario', None)
    return redirect(url_for('home'))

if __name__=='__main__':
    app.run(debug=True)