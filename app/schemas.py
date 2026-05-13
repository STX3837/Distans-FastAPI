from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from enum import Enum


class RolUsuario(str, Enum):
    """Roles disponibles para los usuarios"""
    COMPRADOR = "comprador"
    VENDEDOR = "vendedor"
    ADMIN = "admin"


class UsuarioBase(BaseModel):
    """Campos básicos de usuario"""
    nombre: str
    apellidos: str
    email: EmailStr
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    codigo_postal: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    """Schema para crear un usuario con contraseña"""
    contrasena: str  # Contraseña en texto plano
    rol: Optional[RolUsuario] = RolUsuario.COMPRADOR  # Rol por defecto: Comprador


class UsuarioUpdate(BaseModel):
    """Schema para actualizar datos del usuario - RF28"""
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    codigo_postal: Optional[str] = None


class UsuarioCambiarContrasena(BaseModel):
    """Schema para cambiar contraseña"""
    contrasena_actual: str
    contrasena_nueva: str


class UsuarioResponse(UsuarioBase):
    """Schema para respuesta de usuario - sin contraseña"""
    id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    activo: bool
    
    class Config:
        from_attributes = True


class UsuarioAdminUpdate(BaseModel):
    """Schema para actualizar usuario como administrador - RF32"""
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    codigo_postal: Optional[str] = None
    rol: Optional[RolUsuario] = None
    activo: Optional[bool] = None


class UsuarioAdminResponse(UsuarioBase):
    """Schema para respuesta de usuario en vista de administrador - RF32"""
    id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    rol: RolUsuario
    activo: bool
    
    class Config:
        from_attributes = True
