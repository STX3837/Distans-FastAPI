import os
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from geoalchemy2 import Geometry

# 1. Leer variables de entorno
DB_USER = os.getenv("DB_USER", "mi_usuario")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mi_contrasena")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mi_base_datos")

# 2. Configurar la URL de conexión de PostgreSQL
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 3. Crear el motor de la base de datos
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 4. Definir un Modelo Espacial (Equivalente al que hicimos en Django)
class Ubicacion(Base):
    __tablename__ = "ubicaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    # Campo geométrico de PostGIS para un punto (Longitud, Latitud)
    punto = Column(Geometry(geometry_type='POINT', srid=4326))

# 5. Crear la aplicación FastAPI
app = FastAPI(title="Mi TFG con FastAPI y PostGIS")

# Crear las tablas en la BD (En un proyecto real se usan migraciones con 'Alembic')
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

# 6. Definir rutas (Endpoints)
@app.get("/")
def read_root():
    return {"mensaje": "¡FastAPI y PostGIS están conectados y funcionando!"}