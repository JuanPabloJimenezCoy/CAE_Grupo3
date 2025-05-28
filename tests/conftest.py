import pytest
from app import create_app
from app.auth import Usuario

# Constantes
FLASK_LOGIN_GET_USER = "flask_login.utils._get_user"

@pytest.fixture
def client():
    app = create_app(testing=True)
    app.config['LOGIN_DISABLED'] = True  # Opcional: desactiva login_required para pruebas simples
    with app.test_client() as client:
        yield client

@pytest.fixture
def empleado_usuario(monkeypatch):
    usuario = Usuario(documento="123", role="empleado", nombre="Juan")
    monkeypatch.setattr(FLASK_LOGIN_GET_USER, lambda: usuario)
    return usuario

@pytest.fixture
def supervisor_usuario(monkeypatch):
    usuario = Usuario(documento="456", role="supervisor", nombre="Laura")
    monkeypatch.setattr(FLASK_LOGIN_GET_USER, lambda: usuario)
    return usuario

@pytest.fixture
def admin_usuario(monkeypatch):
    usuario = Usuario(documento="789", role="administrador", nombre="Carlos")
    monkeypatch.setattr(FLASK_LOGIN_GET_USER, lambda: usuario)
    return usuario
