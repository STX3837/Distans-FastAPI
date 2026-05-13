from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models import Usuario, RolUsuario
from app.schemas import (
    UsuarioCreate, 
    UsuarioUpdate, 
    UsuarioResponse,
    UsuarioAdminUpdate,
    UsuarioAdminResponse,
    UsuarioCambiarContrasena,
    RolUsuario as RolSchema
)
from app.crud import (
    crear_usuario,
    obtener_usuario_por_id,
    obtener_todos_usuarios,
    actualizar_usuario,
    actualizar_usuario_admin,
    cambiar_contrasena,
    eliminar_usuario,
)
from app.database import get_db

router = APIRouter(
    prefix="/usuarios",
    tags=["usuarios"],
)

admin_router = APIRouter(
    prefix="/admin/usuarios",
    tags=["administrador"],
)


# ============ RF28: Vistas de Usuario ============

@router.get("/me", response_model=UsuarioResponse)
def obtener_perfil(usuario_id: int, db: Session = Depends(get_db)):
    """
    Obtiene el perfil del usuario autenticado.
    RF28: El sistema debe aportar una vista del usuario que le permita modificar sus datos.
    """
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    return usuario


@router.put("/me", response_model=UsuarioResponse)
def actualizar_perfil(
    usuario_id: int,
    datos: UsuarioUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza los datos del perfil del usuario autenticado.
    RF28: El usuario puede modificar sus datos (menos contraseña).
    """
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    usuario_actualizado = actualizar_usuario(db, usuario_id, datos)
    return usuario_actualizado


@router.post("/me/cambiar-contrasena", status_code=status.HTTP_200_OK)
def cambiar_contrasena_usuario(
    usuario_id: int,
    datos: UsuarioCambiarContrasena,
    db: Session = Depends(get_db)
):
    """
    Cambia la contraseña del usuario autenticado.
    Requiere que verifique su contraseña actual.
    """
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    if not cambiar_contrasena(db, usuario_id, datos.contrasena_actual, datos.contrasena_nueva):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña actual incorrecta"
        )
    
    return {"mensaje": "Contraseña actualizada exitosamente"}


# ============ RF32: Vistas de Administrador ============

@admin_router.get("/", response_model=List[UsuarioAdminResponse])
def listar_usuarios(
    usuario_admin_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lista todos los usuarios del sistema.
    RF32: Los administradores deben poder modificar los datos de los usuarios, 
           crear usuarios nuevos y eliminar usuarios.
    
    Nota: En producción, verificar que usuario_admin_id sea administrador.
    """
    admin = obtener_usuario_por_id(db, usuario_admin_id)
    if not admin or admin.rol != RolUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    
    usuarios = obtener_todos_usuarios(db, skip, limit)
    return usuarios


@admin_router.get("/{usuario_id}", response_model=UsuarioAdminResponse)
def obtener_usuario(
    usuario_id: int,
    usuario_admin_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene los datos de un usuario específico (acceso administrativo).
    """
    admin = obtener_usuario_por_id(db, usuario_admin_id)
    if not admin or admin.rol != RolUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return usuario


@admin_router.post("/", response_model=UsuarioAdminResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario_admin(
    usuario_admin_id: int,
    usuario_data: UsuarioCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo usuario en el sistema (acceso administrativo).
    RF32: Los administradores deben poder crear usuarios nuevos.
    """
    admin = obtener_usuario_por_id(db, usuario_admin_id)
    if not admin or admin.rol != RolUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    
    # Verificar que el email no exista
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario_data.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    nuevo_usuario = crear_usuario(db, usuario_data)
    return nuevo_usuario


@admin_router.put("/{usuario_id}", response_model=UsuarioAdminResponse)
def actualizar_usuario_admin_endpoint(
    usuario_id: int,
    usuario_admin_id: int,
    datos: UsuarioAdminUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza los datos de un usuario (acceso administrativo).
    RF32: Los administradores deben poder modificar los datos de los usuarios.
    """
    admin = obtener_usuario_por_id(db, usuario_admin_id)
    if not admin or admin.rol != RolUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    usuario_actualizado = actualizar_usuario_admin(db, usuario_id, datos)
    return usuario_actualizado


@admin_router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario_admin(
    usuario_id: int,
    usuario_admin_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un usuario del sistema (acceso administrativo).
    RF32: Los administradores deben poder eliminar usuarios.
    """
    admin = obtener_usuario_por_id(db, usuario_admin_id)
    if not admin or admin.rol != RolUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    
    if not eliminar_usuario(db, usuario_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
