from flask import Flask
import os
from dotenv import load_dotenv
from .routes import main_bp
from .auth import login_manager

load_dotenv()

def create_app(testing=False):
    app = Flask(__name__)

    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        raise RuntimeError("SECRET_KEY no está definida en las variables de entorno")

    app.config['SECRET_KEY'] = secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

    if testing:
        app.config['TESTING'] = True

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    app.register_blueprint(main_bp)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    return app