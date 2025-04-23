# db.py
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()  # Cargar variables de entorno desde .env
print("URL DE BASE:", os.getenv("DATABASE_URL"))

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))