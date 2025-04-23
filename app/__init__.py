from flask import Flask
from app.routes.auth_routes import auth_bp
from app.routes.admin_routes import admin_bp
from app.routes.empleado_routes import empleado_bp
from app.routes.supervisor_routes import supervisor_bp

def create_app():
    app = Flask(__name__, template_folder="../Frontend")
    app.secret_key = 'supersecreto'

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(empleado_bp)
    app.register_blueprint(supervisor_bp)

    return app