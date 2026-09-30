import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Leer variables de entorno
DB_USER = os.getenv("DB_USER", "mi_usuario")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mi_contrasena")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mi_base_datos")

# Configurar la URL de conexión de PostgreSQL
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Crear el motor de la base de datos
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependencia para obtener la sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
