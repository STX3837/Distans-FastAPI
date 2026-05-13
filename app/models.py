from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime
from geoalchemy2 import Geometry
from enum import Enum as PyEnum

Base = declarative_base()


class RolUsuario(PyEnum):
    """Roles disponibles para los usuarios"""
    COMPRADOR = "comprador"
    VENDEDOR = "vendedor"
    ADMIN = "admin"


class Usuario(Base):
    """
    Entidad de Usuario según RI01
    Almacena los datos de los usuarios registrados:
    nombre, apellidos, email, teléfono, fecha de creación, 
    fecha de actualización, dirección, ciudad, código postal y contraseña.
    """
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    apellidos = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    telefono = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    ciudad = Column(String, nullable=True)
    codigo_postal = Column(String, nullable=True)
    
    # Contraseña cifrada según RNF02
    contrasena_hash = Column(String, nullable=False)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Rol del usuario (Comprador, Vendedor, Admin)
    rol = Column(Enum(RolUsuario), default=RolUsuario.COMPRADOR, nullable=False)
    
    # Campos administrativos
    activo = Column(Boolean, default=True, nullable=False)


class Ubicacion(Base):
    __tablename__ = "ubicaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    # Campo geométrico de PostGIS para un punto (Longitud, Latitud)
    punto = Column(Geometry(geometry_type='POINT', srid=4326))
