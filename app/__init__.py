from flask import Flask
from .routes import main_bp
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['AVISOS_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'avisos')
    app.config['TIEMPO_EXTRA_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'tiempo_extra')
    app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
    os.makedirs(app.config['AVISOS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TIEMPO_EXTRA_FOLDER'], exist_ok=True)

    app.register_blueprint(main_bp)
    return app