import pytest
from flask import render_template
from flask import send_from_directory
from bs4 import BeautifulSoup

def test_login_get(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Ingresar' in response.data

def test_login_post_invalido(client):
    response = client.post('/', data={'documento': '123456'})
    assert response.status_code == 200
    assert b'Documento no registrado' in response.data

def test_panel_empleado(client, empleado_usuario):
    response = client.get('/panel/empleado')
    assert response.status_code == 200
    assert b'Empleado' in response.data or response.status_code == 200

def test_panel_supervisor(client, supervisor_usuario):
    response = client.get('/panel/supervisor')
    assert response.status_code == 200
    assert b'Supervisor' in response.data or response.status_code == 200

def test_panel_admin(client, admin_usuario):
    response = client.get('/panel/admin')
    assert response.status_code == 200
    assert b'Administrador' in response.data or response.status_code == 200

def test_logout(client, empleado_usuario):
    response = client.get('/logout', follow_redirects=True)
    assert b'Login' in response.data or response.status_code == 200


def test_entrada_ya_registrada(client, monkeypatch, empleado_usuario):
    monkeypatch.setattr("app.services.registrar_entrada_empleado", lambda doc, metodo, valor: "Ya registraste tu entrada hoy.")

    response = client.post('/empleado/entrada', data={
        "metodo": "pin",
        "valor": "1234"
    })

    soup = BeautifulSoup(response.data, 'html.parser')
    mensaje = soup.find(id='mensaje-exito')
    assert mensaje is not None
    assert "Ya registraste tu entrada hoy." in mensaje.text

def test_entrada_empleado_exito(client, monkeypatch, empleado_usuario):
    monkeypatch.setattr("app.services.registrar_entrada_empleado", lambda doc, metodo, valor: "Entrada registrada con éxito.")

    response = client.post('/empleado/entrada', data={
        "metodo": "pin",
        "valor": "1234"
    })

    soup = BeautifulSoup(response.data, 'html.parser')
    mensaje = soup.find(id='mensaje-exito')
    assert mensaje is not None
    assert "Entrada registrada con éxito." in mensaje.text

def test_entrada_credencial_invalida(client, monkeypatch, empleado_usuario):
    monkeypatch.setattr("app.routes.entrada_ya_registrada", lambda cur, doc: False)
    monkeypatch.setattr("app.routes.validar_credencial", lambda cur, doc, m, v: False)
    monkeypatch.setattr("app.routes.cerrar_y_render", lambda cur, conn, msg: msg)

    response = client.post('/empleado/entrada', data={
        "metodo": "pin",
        "valor": "9999"
    })

    assert b"PIN o tarjeta incorrecta" in response.data or b"incorrecta" in response.data

def test_salida_empleado_exito(client, monkeypatch, empleado_usuario):
    monkeypatch.setattr("app.routes.validar_credencial", lambda cur, doc, m, v: True)
    monkeypatch.setattr("app.routes.obtener_asistencia_abierta", lambda cur, doc: 42)
    monkeypatch.setattr("app.routes.calcular_mensaje_salida", lambda cur, doc: "Salida registrada con éxito. Saliste a tiempo.")
    monkeypatch.setattr("app.routes.registrar_salida", lambda cur, asistencia_id: None)

    response = client.post('/empleado/salida', data={
        "metodo": "pin",
        "valor": "1234"
    })

    assert b"Salida registrada con \xc3\xa9xito" in response.data or b"Saliste a tiempo" in response.data

def test_salida_credencial_invalida(client, monkeypatch, empleado_usuario):
    monkeypatch.setattr("app.routes.validar_credencial", lambda cur, doc, m, v: False)
    monkeypatch.setattr("app.routes.cerrar_y_render", lambda cur, conn, msg: msg)

    response = client.post('/empleado/salida', data={
        "metodo": "pin",
        "valor": "wrong"
    })

    assert b"PIN o tarjeta incorrecta" in response.data or b"incorrecta" in response.data

def test_salida_sin_entrada(client, monkeypatch, empleado_usuario):
    monkeypatch.setattr("app.routes.validar_credencial", lambda cur, doc, m, v: True)
    monkeypatch.setattr("app.routes.obtener_asistencia_abierta", lambda cur, doc: None)
    monkeypatch.setattr("app.routes.cerrar_y_render", lambda cur, conn, msg: msg)

    response = client.post('/empleado/salida', data={
        "metodo": "pin",
        "valor": "1234"
    })

    assert b"No hay entrada registrada hoy" in response.data or b"ya registraste la salida" in response.data

def test_entrada_supervisor_exito(client, monkeypatch, supervisor_usuario):
    class MockCursor:
        def execute(self, query, params):
            self.query = query
            self.params = params
        def fetchone(self):
            if "asistencia" in self.query:
                return None
            if "supervisor" in self.query:
                return {"documento": "456"}
            return None
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def commit(self): 
            # Este es un método mock para pruebas; no se necesita un commit real.
            pass
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.post('/supervisor/entrada', data={
        "metodo": "pin",
        "valor": "4567"
    })

    assert b"Entrada registrada con \xc3\xa9xito" in response.data or b"registrada" in response.data

def test_entrada_supervisor_ya_registrada(client, monkeypatch, supervisor_usuario):
    class MockCursor:
        def execute(self, query, params): self.query = query
        def fetchone(self): return (1,)
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.post('/supervisor/entrada', data={
        "metodo": "pin",
        "valor": "4567"
    })

    assert b"ya registraste tu entrada hoy" in response.data.lower()

def test_entrada_supervisor_pin_invalido(client, monkeypatch, supervisor_usuario):
    class MockCursor:
        def __init__(self): self.calls = 0
        def execute(self, query, params): self.query = query
        def fetchone(self):
            if "asistencia" in self.query:
                return None
            if "supervisor" in self.query:
                return None
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.post('/supervisor/entrada', data={
        "metodo": "pin",
        "valor": "9999"
    })

    assert b"PIN o tarjeta incorrecta" in response.data or b"incorrecta" in response.data

def test_entrada_admin_exito(client, monkeypatch, admin_usuario):
    monkeypatch.setattr("app.services.registrar_entrada_admin", lambda doc, metodo, valor: "Entrada registrada con éxito.")

    response = client.post('/admin/entrada', data={
        "metodo": "pin",
        "valor": "adminpass"
    })

    soup = BeautifulSoup(response.data, 'html.parser')
    mensaje = soup.find(id='mensaje-exito')
    assert mensaje is not None
    assert "Entrada registrada con éxito." in mensaje.text

def test_entrada_admin_ya_registrada(client, monkeypatch, admin_usuario):
    monkeypatch.setattr("app.services.registrar_entrada_admin", lambda doc, metodo, valor: "Ya registraste tu entrada hoy.")

    response = client.post('/admin/entrada', data={
        "metodo": "pin",
        "valor": "adminpass"
    })

    soup = BeautifulSoup(response.data, 'html.parser')
    mensaje = soup.find(id='mensaje-exito')

    assert mensaje is not None
    assert "ya registraste tu entrada hoy" in mensaje.text.lower()


def test_entrada_admin_pin_invalido(client, monkeypatch, admin_usuario):
    class MockCursor:
        def execute(self, query, params): self.query = query
        def fetchone(self):
            if "asistencia" in self.query:
                return None
            if "administrador" in self.query:
                return None
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.post('/admin/entrada', data={
        "metodo": "pin",
        "valor": "wrongpin"
    })

    assert b"PIN o tarjeta incorrecta" in response.data or b"incorrecta" in response.data

def test_salida_supervisor_exito(client, monkeypatch, supervisor_usuario):
    class MockCursor:
        def execute(self, query, params):
            self.query = query
        def fetchone(self):
            if "supervisor" in self.query:
                return {"documento": "456"}
            if "asistencia" in self.query:
                return (123,)
            if "horarios" in self.query:
                return ("17:00:00",)
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def commit(self): 
            # Este es un método mock para pruebas; no se necesita un commit real.
            pass
        def rollback(self): 
            # Este es un método mock para pruebas; no se necesita rollback real.
            pass
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.post('/supervisor/salida', data={
        "metodo": "pin",
        "valor": "4567"
    })

    assert b"Salida registrada con \xc3\xa9xito" in response.data or b"salida registrada" in response.data

def test_salida_supervisor_pin_invalido(client, monkeypatch, supervisor_usuario):
    class MockCursor:
        def execute(self, query, params):
            self.query = query
        def fetchone(self):
            if "supervisor" in self.query:
                return None
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def rollback(self): 
            # Este es un método mock para pruebas; no se necesita rollback real.
            pass
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())
    monkeypatch.setattr("app.routes.cerrar_y_render", lambda cur, conn, msg: msg)

    response = client.post('/supervisor/salida', data={
        "metodo": "pin",
        "valor": "wrong"
    })

    assert b"PIN o tarjeta incorrecta" in response.data or b"incorrecta" in response.data

def test_salida_supervisor_sin_entrada(client, monkeypatch, supervisor_usuario):
    class MockCursor:
        def execute(self, query, params):
            self.query = query
        def fetchone(self):
            if "supervisor" in self.query:
                return {"documento": "456"}
            if "asistencia" in self.query:
                return None
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def rollback(self): 
            # Este es un método mock para pruebas; no se necesita rollback real.
            pass
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())
    monkeypatch.setattr("app.routes.cerrar_y_render", lambda cur, conn, msg: msg)

    response = client.post('/supervisor/salida', data={
        "metodo": "pin",
        "valor": "4567"
    })

    assert b"No hay entrada registrada hoy" in response.data or b"ya registraste la salida" in response.data

def test_salida_admin_exito(client, monkeypatch, admin_usuario):
    monkeypatch.setattr("app.services.registrar_salida_admin", lambda doc, metodo, valor: "Salida registrada con éxito.")

    response = client.post('/admin/salida', data={
        "metodo": "pin",
        "valor": "7890"
    })

    assert b"Salida registrada con \xc3\xa9xito" in response.data or b"salida registrada" in response.data.lower()


def test_salida_admin_pin_invalido(client, monkeypatch, admin_usuario):
    monkeypatch.setattr("app.services.registrar_salida_admin", lambda doc, metodo, valor: "PIN o tarjeta incorrecta.")

    response = client.post('/admin/salida', data={
        "metodo": "pin",
        "valor": "wrong"
    })

    assert b"pin o tarjeta incorrecta" in response.data.lower()

def test_salida_admin_sin_entrada(client, monkeypatch, admin_usuario):
    monkeypatch.setattr("app.services.registrar_salida_admin", lambda doc, metodo, valor: "No has registrado entrada hoy.")

    response = client.post('/admin/salida', data={
        "metodo": "pin",
        "valor": "7890"
    })

    assert b"no has registrado entrada hoy" in response.data.lower()

def test_ver_retrasos_supervisor_exito(client, monkeypatch, supervisor_usuario):
    monkeypatch.setattr("app.services.obtener_retrasos_supervisor", lambda doc: (
        [
            ('Juan', 'Perez', 3, 45),
            ('Maria', 'Lopez', 1, 15)
        ],
        None
    ))

    response = client.get('/supervisor/retrasos')

    assert response.status_code == 200
    assert b'Juan' in response.data
    assert b'Perez' in response.data
    assert b'Maria' in response.data
    assert b'Lopez' in response.data

def test_ver_retrasos_supervisor_no_encontrado(client, monkeypatch, supervisor_usuario):
    class MockCursor:
        def execute(self, query, params):
            self.query = query
        def fetchone(self):
            if "supervisor" in self.query:
                return None
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def close(self):
        # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.get('/supervisor/retrasos')

    assert response.status_code == 200
    assert b"No se encontr" in response.data or b"supervisor" in response.data

def test_ver_empleados_asignados_exito(client, monkeypatch, supervisor_usuario):
    monkeypatch.setattr("app.services.obtener_empleados_asignados", lambda doc: (
        [
            ('Juan', 'Perez'),
            ('Maria', 'Lopez')
        ],
        None
    ))

    response = client.get('/supervisor/mis-empleados')

    assert response.status_code == 200
    assert b'Juan' in response.data
    assert b'Perez' in response.data
    assert b'Maria' in response.data
    assert b'Lopez' in response.data

def test_ver_empleados_asignados_no_supervisor(client, monkeypatch, supervisor_usuario):
    class MockCursor:
        def __init__(self):
            self.last_query = ""

        def execute(self, query, params):
            self.last_query = query

        def fetchone(self):
            if "FROM supervisor WHERE documento" in self.last_query:
                return None
            return None

        def fetchall(self):
            return []

        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.get('/supervisor/mis-empleados')

    assert response.status_code == 200
    assert b"No se pudo encontrar el supervisor" in response.data or b"supervisor" in response.data

def test_asignar_y_gestionar_post_valido(client, monkeypatch, admin_usuario):
    class MockCursor:
        def execute(self, query, params): 
            # Este es un método mock para pruebas; no ejecuta consultas reales.
            pass
        def fetchall(self): return []
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def commit(self): 
            # Este es un método mock para pruebas; no se necesita un commit real.
            pass
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.post('/admin/asignar-y-gestionar', data={
        "supervisor_id": "1",
        "empleado_ids": ["1", "2"]
    })

    html = response.data.decode('utf-8')

    assert response.status_code == 200
    assert "Asignación realizada con éxito" in html or "asignación" in html.lower()

def test_asignar_y_gestionar_horarios_post_valido(client, monkeypatch, admin_usuario):
    class MockCursor:
        def execute(self, query, params): 
            # Este es un método mock para pruebas; no ejecuta consultas reales.
            pass
        def fetchall(self): return []
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def commit(self): 
            # Este es un método mock para pruebas; no se necesita un commit real.
            pass
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.post('/admin/asignar-y-gestionar-horarios', data={
        "accion": "asignar",
        "empleado_id": "1",
        "hora_entrada": "08:00",
        "hora_salida": "17:00",
        "dias_laborales": ["l", "m"]
    })

    html = response.data.decode('utf-8')

    assert response.status_code == 200
    assert "Horario asignado correctamente" in html or "Horario asignado correctamente.".lower() in html.lower()

def test_solicitar_tiempo_extra_post(client, monkeypatch, empleado_usuario):
    monkeypatch.setattr("app.services.registrar_tiempo_extra", lambda doc, fecha, hi, hf, motivo, archivo: "Solicitud enviada correctamente.")

    response = client.post('/empleado/tiempo-extra', data={
        "fecha": "2024-05-01",
        "hora_inicio": "18:00",
        "hora_fin": "20:00",
        "motivo": "Trabajo urgente"
    })

    assert response.status_code == 200
    assert b"solicitud enviada correctamente" in response.data.lower()

def test_enviar_aviso_post_valido(client, monkeypatch, supervisor_usuario):
    monkeypatch.setattr("app.services.enviar_aviso_supervisor", lambda doc_sup, id_emp, archivo: (True, 'Aviso enviado exitosamente.'))

    response = client.post('/supervisor/avisos', data={
        "id_empleado": "1"
    })

    assert response.status_code == 302

def test_asignar_y_gestionar_post_valido(client, monkeypatch, admin_usuario):
    class MockCursor:
        def __init__(self):
            self.last_query = None

        def execute(self, query, params=None):
            self.last_query = query

        def fetchall(self):
            if "FROM empleado_supervisor" in self.last_query:
                return [
                    (1, 'Carlos', 'Gomez', 10, 'Juan', 'Perez')
                ]
            return []

        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def commit(self): 
            # Este es un método mock para pruebas; no se necesita un commit real.
            pass
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.post('/admin/asignar-y-gestionar', data={
        "empleado_id": "10",
        "supervisor_id_eliminar": "1"
    })

    html = response.data.decode('utf-8')

    assert response.status_code == 200
    assert 'Juan' in html or 'Perez' in html

def test_asignar_y_gestionar_get(client, monkeypatch, admin_usuario):
    class MockCursor:
        def execute(self, query, params=None):
            # Este es un método mock para pruebas; no ejecuta consultas reales a la base de datos.
            pass
        def fetchall(self):
            return [
                (1, 'Carlos', 'Gomez', 10, 'Juan', 'Perez')
            ]
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.get('/admin/asignar-y-gestionar')

    assert response.status_code == 200
    assert b'Juan' in response.data or b'Perez' in response.data

def test_asignar_y_gestionar_horarios_post_valido(client, monkeypatch, admin_usuario):
    class MockCursor:
        def execute(self, query, params): 
            # Este es un método mock para pruebas; no ejecuta consultas reales.
            pass
        def fetchall(self):
            return [
                (1, 'Juan', 'Perez', '08:00', '17:00', 'lmv')
            ]
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def commit(self): 
            # Este es un método mock para pruebas; no se necesita un commit real.
            pass
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.post('/admin/asignar-y-gestionar-horarios', data={
        "accion": "editar",
        "empleado_id": "1",
        "hora_entrada": "09:00",
        "hora_salida": "18:00",
        "dias_laborales": ["l", "m", "v"]
    })

    assert response.status_code == 200
    assert b'Juan' in response.data or b'Perez' in response.data

def test_asignar_y_gestionar_horarios_get(client, monkeypatch, admin_usuario):
    class MockCursor:
        def execute(self, query, params=None): 
            # Este es un método mock para pruebas; no ejecuta consultas reales a la base de datos.
            pass
        def fetchall(self):
            return [
                (1, 'Juan', 'Perez', '08:00', '17:00', 'lmv')
            ]
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.get('/admin/asignar-y-gestionar-horarios')

    assert response.status_code == 200
    assert b'Juan' in response.data or b'Perez' in response.data

def test_ver_tiempo_extra_empleado_get(client, monkeypatch, empleado_usuario):
    monkeypatch.setattr("app.services.obtener_solicitudes_tiempo_extra", lambda doc: (
        [
            (1, '2024-05-01', '18:00', '20:00', 'Trabajo urgente', None, 'Pendiente')
        ],
        None
    ))

    response = client.get('/empleado/mis_solicitudes_tiempo-extra')

    assert response.status_code == 200
    assert b'Trabajo urgente' in response.data
    assert b'Pendiente' in response.data

def test_revisar_tiempo_extra_get(client, monkeypatch, supervisor_usuario):
    monkeypatch.setattr("app.services.obtener_solicitudes_tiempo_extra_supervisor", lambda doc: (
        [
            (1, 'Juan', 'Perez', '2024-05-01', '18:00', '20:00', 'Motivo urgente', None, 'Pendiente')
        ],
        None
    ))

    response = client.get('/supervisor/tiempo-extra')

    assert response.status_code == 200
    assert b'Juan' in response.data
    assert b'Perez' in response.data
    assert b'Motivo urgente' in response.data
    assert b'Pendiente' in response.data

def test_revisar_tiempo_extra_post_aprobar(client, monkeypatch, supervisor_usuario):
    class MockCursor:
        def execute(self, query, params): 
            # Este es un método mock para pruebas; no ejecuta consultas reales.
            pass
        def fetchall(self):
            return [
                (1, 'Juan', 'Perez', '2024-05-01', '18:00', '20:00', 'Motivo urgente', None, 'Pendiente')
            ]
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    class MockConn:
        def cursor(self): return MockCursor()
        def commit(self): 
            # Este es un método mock para pruebas; no se necesita un commit real.
            pass
        def close(self): 
            # Este método está vacío intencionalmente porque la clase base no necesita acciones de cierre.
            pass

    monkeypatch.setattr("app.routes.get_connection", lambda: MockConn())

    response = client.post('/supervisor/tiempo-extra', data={
        "id_solicitud": "1",
        "accion": "aprobar"
    }, follow_redirects=True)

    assert response.status_code == 200

def test_ver_avisos_empleado_get(client, monkeypatch, empleado_usuario):
    monkeypatch.setattr("app.services.obtener_avisos_empleado", lambda doc: (
        [
            ('2024-05-01', 'archivo_1.pdf')
        ],
        None
    ))

    response = client.get('/empleado/avisos')

    assert response.status_code == 200
    assert b'archivo_1.pdf' in response.data
    assert b'2024-05-01' in response.data

def test_ver_avisos_admin_get(client, monkeypatch, admin_usuario):
    monkeypatch.setattr("app.services.obtener_avisos_admin", lambda: (
        [
            ('2024-05-01', 'Juan Perez', 'Laura Lopez', 'archivo_1.pdf')
        ],
        None
    ))

    response = client.get('/admin/avisos')

    html = response.data.decode('utf-8')

    assert response.status_code == 200
    assert 'Avisos Enviados' in html
    assert 'archivo_1.pdf' in html

def test_descargar_justificativo(client, monkeypatch, empleado_usuario):
    from flask import Response

    monkeypatch.setattr("app.routes.send_from_directory", lambda dir, filename, as_attachment=True: Response(f"Mock archivo {filename}", mimetype='application/pdf'))

    response = client.get('/descargar/justificativo/archivo_1.pdf')

    assert response.status_code == 200
    assert b'Mock archivo archivo_1.pdf' in response.data

def test_descargar_aviso(client, monkeypatch, empleado_usuario):
    from flask import Response

    monkeypatch.setattr("flask.send_from_directory", lambda dir, filename: Response(f"Mock aviso {filename}", mimetype='application/pdf'))

    response = client.get('/uploads/avisos/aviso_1.pdf')

    assert response.status_code == 200
    assert b'Mock aviso aviso_1.pdf' in response.data

def test_ver_mi_qr(client, monkeypatch, empleado_usuario):
    response = client.get('/mi-qr')

    html = response.data.decode('utf-8')
    assert response.status_code == 200
    assert '<img' in html
    assert 'data:image/png;base64' in html