from setuptools import setup, find_packages

setup(
    name="control-de-acceso",
    version="2.0.1",
    packages=find_packages(),
    install_requires=[
        "flask",
    ],
    description="Sistema de control de acceso de empleados en Flask",
    author="Grupo3",
    author_email="Grupo3@gmail.com",
    license="MIT",
)