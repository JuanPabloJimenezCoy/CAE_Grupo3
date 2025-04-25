# Control de Acceso de Empleados (CAE)

Sistema web de control de acceso para empleados, supervisores y administradores, desarrollado con **Python, Flask y PostgreSQL**, que permite gestionar registros de entrada y salida, asignar horarios, controlar asistencia y generar reportes.

---

## Características Principales

- Inicio de sesión con número de documento.
- Redirección automática a panel según el rol: **Empleado**, **Supervisor** o **Administrador**.
- Registro de entrada y salida con **validación de horario** (solo para empleados).
- Registro de entrada mediante:
  - PIN
  - Tarjeta
  - Código QR personalizado
- Asignación de horarios por día y hora.
- Solicitud de tiempo extra con carga de justificativos.
- Supervisores aprueban/rechazan solicitudes y envían avisos con archivo adjunto.
- Descarga de archivos (justificativos, avisos).
- Visualización de historial personal de asistencia.
- Generación de reportes con Pandas + Excel.
- Asignación de empleados a supervisores.
- Registro de retrasos, salidas tempranas o fuera de horario.

---

## Tecnologías Utilizadas

- **Backend:** Python 3, Flask, PostgreSQL (Neon), Jinja2
- **Frontend:** HTML5, Tailwind CSS, jQuery
- **Librerías clave:**
  - `psycopg2-binary`
  - `python-dotenv`
  - `pytz`
  - `qrcode[pil]`
  - `pandas`, `openpyxl`

---

# Instalar las dependencias
-	pip install flask
-   pip install flask
-   pip install psycopg2-binary
-   pip install python-dotenv
-   pip install pytz
-   pip install qrcode[pil]
-   pip install pandas
-   pip install openpyxl

---

# Ejecutar la aplicación
- 	python back.py

---

## Funcionalidades por Rol

### Empleado
- Registrar entrada/salida dentro del horario.
- Escanear QR para registrar entrada.
- Ver historial personal y retrasos.
- Solicitar tiempo extra con justificativo.

### Supervisor
- Visualizar y aprobar/rechazar solicitudes.
- Enviar avisos con archivos adjuntos.
- Ver lista de empleados asignados.

### Administrador
- Asignar horarios a usuarios.
- Asignar empleados a supervisores.
- Control total del sistema.

---

# Licencia
-	Este proyecto está bajo la licencia MIT.