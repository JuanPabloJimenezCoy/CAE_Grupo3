# Control de Acceso de Empleados (CAE)
Este es un sistema de autenticación básico desarrollado en Flask que permite el registro e inicio de sesión de empleados mediante un número de tarjeta.

# Características
•	Registro de usuarios con nombre y número de tarjeta.
•	Inicio de sesión mediante el número de tarjeta.
•	Uso de sesiones para mantener la autenticación.
•	Posibilidad de cerrar sesión.

# Tecnologías utilizadas
•	Python 3
•	Flask
•	HTML/CSS

# Instalar las dependencias
•	pip install flask

# Ejecutar la aplicación
•	python back.py

# Uso
•	Al iniciar la aplicación, se muestra el formulario de inicio de sesión.
•	Si el usuario no está registrado, puede ir a la página de registro.
•	En la página de registro, el usuario ingresa su nombre y número de tarjeta.
•	Luego del registro, el usuario puede iniciar sesión con su número de tarjeta.
•	Si la tarjeta está registrada, se redirige a la página de bienvenida.
•	El usuario puede cerrar sesión cuando lo desee.

# Licencia
•	Este proyecto está bajo la licencia MIT.