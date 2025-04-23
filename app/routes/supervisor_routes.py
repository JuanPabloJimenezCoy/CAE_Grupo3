from flask import Blueprint, render_template, session, redirect, url_for
from app.db import get_connection

supervisor_bp = Blueprint('supervisor', __name__)

# Decorador para verificar rol
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

@supervisor_bp.route('/supervisor')
@rol_requerido('supervisor')
def panel_supervisor():
    supervisor_id = session['usuario']['id']

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.credencial, e.nombre, e.apellido, e.cargo
                FROM empleado e
                JOIN supervisor_empleado se ON e.credencial = se.credencial
                WHERE se.id_supervisor = %s
            """, (supervisor_id,))
            empleados = cur.fetchall()

    return render_template("inicio_supervisor.html",
                           usuario=session['usuario'],
                           empleados=empleados)