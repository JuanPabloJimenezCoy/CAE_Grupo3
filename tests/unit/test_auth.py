import datetime
from app.auth import validar_credencial
from app.auth import entrada_ya_registrada
from app.auth import verificar_credencial
from app.auth import obtener_asistencia_abierta
import pytest
from datetime import time, date
from app.auth import (
    calcular_retraso,
    zona_colombia,
    ahora_colombia,
    es_dia_laboral,
    esta_en_rango_horario,
    comparar_salida_programada,
    MENSAJE_SALISTE_A_TIEMPO,
    MENSAJE_SALISTE_ANTES,
    MENSAJE_SALISTE_DESPUES
)

# Tests para calcular_retraso
def test_retraso_con_10_minutos(monkeypatch):
    monkeypatch.setattr("app.auth.ahora_colombia", lambda: (None, time(7, 10, 0)))
    assert calcular_retraso(time(7, 0, 0)) == 10

def test_sin_retraso(monkeypatch):
    monkeypatch.setattr("app.auth.ahora_colombia", lambda: (None, time(7, 0, 0)))
    assert calcular_retraso(time(7, 0, 0)) == 0

# Test zona_colombia
def test_zona_colombia():
    zona = zona_colombia()
    assert zona.zone == 'America/Bogota'

# Tests es_dia_laboral
def test_es_dia_laboral_true(monkeypatch):
    class FakeDateTime:
        @staticmethod
        def now(tz=None):
            return datetime.datetime(2024, 4, 1, tzinfo=tz)

    monkeypatch.setattr("app.auth.dt", FakeDateTime)
    assert es_dia_laboral('lmvj') == True

def test_es_dia_laboral_false(monkeypatch):
    class FakeDateTime:
        @staticmethod
        def now(tz=None):
            return datetime.datetime(2024, 4, 7, tzinfo=tz)

    monkeypatch.setattr("app.auth.dt", FakeDateTime)
    assert es_dia_laboral('lmvj') == False

# Tests esta_en_rango_horario
def test_esta_en_rango_horario_dentro(monkeypatch):
    monkeypatch.setattr("app.auth.ahora_colombia", lambda: (None, time(8, 0, 0)))
    assert esta_en_rango_horario(time(7, 0, 0), time(9, 0, 0)) == True

def test_esta_en_rango_horario_fuera(monkeypatch):
    monkeypatch.setattr("app.auth.ahora_colombia", lambda: (None, time(6, 0, 0)))
    assert esta_en_rango_horario(time(7, 0, 0), time(9, 0, 0)) == False

# Tests comparar_salida_programada
def test_salida_a_tiempo():
    assert comparar_salida_programada(time(17, 0, 0), time(17, 5, 0), date.today()) == MENSAJE_SALISTE_A_TIEMPO

def test_salida_antes():
    assert comparar_salida_programada(time(17, 0, 0), time(16, 30, 0), date.today()) == MENSAJE_SALISTE_ANTES

def test_salida_despues():
    assert comparar_salida_programada(time(17, 0, 0), time(17, 30, 0), date.today()) == MENSAJE_SALISTE_DESPUES

# Test ahora_colombia
def test_ahora_colombia_formato():
    fecha, hora = ahora_colombia()
    assert isinstance(fecha, datetime.date)
    assert isinstance(hora, datetime.time)

class MockCursor:
    def __init__(self, should_find=True):
        self.should_find = should_find
    def execute(self, query, params):
        self.query = query
        self.params = params
    def fetchone(self):
        return (1,) if self.should_find else None

def test_validar_credencial_correcta():
    cur = MockCursor(should_find=True)
    assert validar_credencial(cur, "123", "pin", "1111") == True

def test_validar_credencial_incorrecta():
    cur = MockCursor(should_find=False)
    assert validar_credencial(cur, "123", "pin", "9999") == False

class MockCursorEntrada:
    def __init__(self, registro_encontrado):
        self.registro_encontrado = registro_encontrado
    def execute(self, query, params):
        self.query = query
        self.params = params
    def fetchone(self):
        return (1,) if self.registro_encontrado else None

def test_entrada_ya_registrada_true(monkeypatch):
    mock_cur = MockCursorEntrada(registro_encontrado=True)
    monkeypatch.setattr("app.auth.ahora_colombia", lambda: ("2024-05-11", None))
    assert entrada_ya_registrada(mock_cur, "123456") == True

def test_entrada_ya_registrada_false(monkeypatch):
    mock_cur = MockCursorEntrada(registro_encontrado=False)
    monkeypatch.setattr("app.auth.ahora_colombia", lambda: ("2024-05-11", None))
    assert entrada_ya_registrada(mock_cur, "123456") == False

class MockCursorVerificacion:
    def __init__(self, encontrado):
        self.encontrado = encontrado
    def execute(self, query, params):
        self.query = query
        self.params = params
    def fetchone(self):
        return {"documento": "123"} if self.encontrado else None

def test_verificar_credencial_con_pin_correcto():
    cur = MockCursorVerificacion(encontrado=True)
    resultado = verificar_credencial(cur, "123", "pin", "1234", "empleado")
    assert resultado == {"documento": "123"}

def test_verificar_credencial_con_tarjeta_invalida():
    cur = MockCursorVerificacion(encontrado=False)
    resultado = verificar_credencial(cur, "123", "tarjeta", "xyz", "supervisor")
    assert resultado is None

class MockCursorAsistencia:
    def __init__(self, resultado):
        self.resultado = resultado
    def execute(self, query, params):
        self.query = query
        self.params = params
    def fetchone(self):
        return (77,) if self.resultado else None

def test_obtener_asistencia_abierta_encontrada(monkeypatch):
    cur = MockCursorAsistencia(resultado=True)
    monkeypatch.setattr("app.auth.ahora_colombia", lambda: ("2024-05-11", None))
    id_asistencia = obtener_asistencia_abierta(cur, "123456")
    assert id_asistencia == 77

def test_obtener_asistencia_abierta_no_encontrada(monkeypatch):
    cur = MockCursorAsistencia(resultado=False)
    monkeypatch.setattr("app.auth.ahora_colombia", lambda: ("2024-05-11", None))
    id_asistencia = obtener_asistencia_abierta(cur, "123456")
    assert id_asistencia is None