from fastapi import APIRouter, Depends, HTTPException, Request, status
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


def _obtener_usuario_actual(request: Request, db: Session) -> Usuario:
    """Obtiene el usuario autenticado desde la sesión activa."""
    session_user = request.session.get("usuario")
    if not session_user or "id" not in session_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado"
        )

    usuario = obtener_usuario_por_id(db, session_user["id"])
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


def _obtener_admin_actual(request: Request, db: Session) -> Usuario:
    """Valida que el usuario autenticado tenga rol administrador."""
    usuario = _obtener_usuario_actual(request, db)
    if usuario.rol != RolUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    return usuario


# ============ RF28: Vistas de Usuario ============

@router.get("/me", response_model=UsuarioResponse)
def obtener_perfil(request: Request, db: Session = Depends(get_db)):
    """
    Obtiene el perfil del usuario autenticado.
    RF28: El sistema debe aportar una vista del usuario que le permita modificar sus datos.
    """
    return _obtener_usuario_actual(request, db)


@router.put("/me", response_model=UsuarioResponse)
def actualizar_perfil(
    request: Request,
    datos: UsuarioUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza los datos del perfil del usuario autenticado.
    RF28: El usuario puede modificar sus datos (menos contraseña).
    """
    usuario = _obtener_usuario_actual(request, db)
    
    usuario_actualizado = actualizar_usuario(db, usuario.id, datos)
    return usuario_actualizado


@router.post("/me/cambiar-contrasena", status_code=status.HTTP_200_OK)
def cambiar_contrasena_usuario(
    request: Request,
    datos: UsuarioCambiarContrasena,
    db: Session = Depends(get_db)
):
    """
    Cambia la contraseña del usuario autenticado.
    Requiere que verifique su contraseña actual.
    """
    usuario = _obtener_usuario_actual(request, db)
    
    if not cambiar_contrasena(db, usuario.id, datos.contrasena_actual, datos.contrasena_nueva):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña actual incorrecta"
        )
    
    return {"mensaje": "Contraseña actualizada exitosamente"}


# ============ RF32: Vistas de Administrador ============

@admin_router.get("/", response_model=List[UsuarioAdminResponse])
def listar_usuarios(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lista todos los usuarios del sistema.
    RF32: Los administradores deben poder modificar los datos de los usuarios, 
           crear usuarios nuevos y eliminar usuarios.
    
    El usuario administrador se obtiene de la sesión activa.
    """
    _obtener_admin_actual(request, db)
    
    usuarios = obtener_todos_usuarios(db, skip, limit)
    return usuarios


@admin_router.get("/{usuario_id}", response_model=UsuarioAdminResponse)
def obtener_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Obtiene los datos de un usuario específico (acceso administrativo).
    """
    _obtener_admin_actual(request, db)
    
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return usuario


@admin_router.post("/", response_model=UsuarioAdminResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario_admin(
    request: Request,
    usuario_data: UsuarioCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo usuario en el sistema (acceso administrativo).
    RF32: Los administradores deben poder crear usuarios nuevos.
    """
    _obtener_admin_actual(request, db)
    
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
    request: Request,
    datos: UsuarioAdminUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza los datos de un usuario (acceso administrativo).
    RF32: Los administradores deben poder modificar los datos de los usuarios.
    """
    _obtener_admin_actual(request, db)
    
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
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Elimina un usuario del sistema (acceso administrativo).
    RF32: Los administradores deben poder eliminar usuarios.
    """
    _obtener_admin_actual(request, db)
    
    if not eliminar_usuario(db, usuario_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
