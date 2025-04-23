from flask import Blueprint, render_template, session, redirect, url_for, request
from app.db import get_connection

admin_bp = Blueprint('admin', __name__)

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

@admin_bp.route('/admin')
@rol_requerido('admin')
def panel_admin():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT credencial, nombre, apellido, cargo FROM empleado")
            empleados = cur.fetchall()
    return render_template("inicio_administrador.html", 
                           usuario=session['usuario'],
                           empleados=empleados)

@admin_bp.route('/admin/asignar-empleados', methods=['GET', 'POST'])
@rol_requerido('admin')
def asignar_empleados():
    with get_connection() as conn:
        with conn.cursor() as cur:
            if request.method == 'POST':
                id_supervisor = request.form.get('supervisor')
                empleados_asignados = request.form.getlist('empleados')

                cur.execute("DELETE FROM supervisor_empleado WHERE id_supervisor = %s", (id_supervisor,))
                for credencial in empleados_asignados:
                    cur.execute("""
                        INSERT INTO supervisor_empleado (id_supervisor, credencial)
                        VALUES (%s, %s)
                    """, (id_supervisor, credencial))

                conn.commit()
                return redirect(url_for('admin.panel_admin'))

            cur.execute("SELECT id_supervisor, nombre, apellido FROM supervisor")
            supervisores = cur.fetchall()

            cur.execute("SELECT credencial, nombre, apellido FROM empleado")
            empleados = cur.fetchall()

    return render_template('asignar_empleados.html',
                           supervisores=supervisores,
                           empleados=empleados)