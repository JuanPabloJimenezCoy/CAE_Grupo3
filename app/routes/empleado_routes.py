from flask import Blueprint, render_template, session, redirect, url_for

empleado_bp = Blueprint('empleado', __name__)

def rol_requerido(rol_necesario):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario' not in session or session['usuario']['rol'] != rol_necesario:
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@empleado_bp.route('/inicio')
@rol_requerido('empleado')
def inicio():
    usuario_data = {
        'nombre_completo': session['usuario']['nombre'],
        'hora_login': session['usuario']['hora_login']
    }
    return render_template("inicio_empleado.html", usuario=usuario_data)