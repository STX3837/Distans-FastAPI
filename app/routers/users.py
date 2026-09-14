from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List
import hashlib
import secrets
from fastapi.responses import HTMLResponse, RedirectResponse
from app.routers.auth import templates, _validar_csrf
from app.models import Usuario, RolUsuario
from app.schemas import (
    UsuarioAdminCreate,
    DatosCompradorPago,
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

    expected = hashlib.sha256(usuario.contrasena_hash.encode()).hexdigest()
    if not secrets.compare_digest(session_user.get("version_contrasena", ""), expected):
        request.session.clear()
        raise HTTPException(status_code=401, detail="La sesión ha caducado; inicia sesión de nuevo")

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


@router.get("/me/datos-pago", response_model=DatosCompradorPago)
def obtener_datos_comprador_pago(request: Request, db: Session = Depends(get_db)):
    """RF27: facilita los datos guardados de la cuenta para el formulario de pago."""
    usuario = _obtener_usuario_actual(request, db)
    campos = ("nombre", "apellidos", "email", "telefono", "direccion", "ciudad", "codigo_postal")
    faltantes = [campo for campo in campos if not getattr(usuario, campo) or not getattr(usuario, campo).strip()]
    if faltantes:
        raise HTTPException(status_code=409, detail="Completa los datos de tu cuenta antes de pagar: " + ", ".join(faltantes))
    return usuario


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
    _validar_csrf(request)
    
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
    _validar_csrf(request)
    
    if not cambiar_contrasena(db, usuario.id, datos.contrasena_actual, datos.contrasena_nueva):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña actual incorrecta"
        )
    
    request.session.clear()
    return {"mensaje": "Contraseña actualizada; inicia sesión de nuevo"}


# ============ RF32: Vistas de Administrador ============

@admin_router.get("/", response_model=List[UsuarioAdminResponse])
def listar_usuarios(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    q: str = Query("", max_length=120),
    rol: RolUsuario | None = None,
    db: Session = Depends(get_db)
):
    """
    Lista todos los usuarios del sistema.
    RF32: Los administradores deben poder modificar los datos de los usuarios, 
           crear usuarios nuevos y eliminar usuarios.
    
    El usuario administrador se obtiene de la sesión activa.
    """
    _obtener_admin_actual(request, db)
    
    query = db.query(Usuario)
    if q.strip():
        query = query.filter(or_(*[campo.icontains(q.strip(), autoescape=True) for campo in (Usuario.nombre, Usuario.apellidos, Usuario.email)]))
    if rol: query = query.filter(Usuario.rol == rol)
    usuarios = query.order_by(Usuario.id).offset(skip).limit(limit).all()
    return usuarios


@router.get("/cuenta", response_class=HTMLResponse)
def pagina_cuenta(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("usuario"):
        return RedirectResponse("/login", status_code=303)
    usuario = _obtener_usuario_actual(request, db)
    return templates.TemplateResponse(request=request, name="cuenta.html", context={
        "usuario": usuario, "user_name": usuario.nombre, "es_admin": usuario.rol == RolUsuario.ADMIN,
        "es_vendedor": usuario.rol == RolUsuario.VENDEDOR,
    })


@admin_router.get("/panel", response_class=HTMLResponse)
def pagina_admin(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("usuario"):
        return RedirectResponse("/login", status_code=303)
    usuario = _obtener_admin_actual(request, db)
    from app.routers.catalogo import pagina_publica
    return pagina_publica(request, db, "administracion.html", {"panel_cuentas": True})


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
    usuario_data: UsuarioAdminCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo usuario en el sistema (acceso administrativo).
    RF32: Los administradores deben poder crear usuarios nuevos.
    """
    _obtener_admin_actual(request, db)
    _validar_csrf(request)
    
    # Verificar que el email no exista
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario_data.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    try:
        nuevo_usuario = crear_usuario(db, usuario_data)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
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
    
    _validar_csrf(request)
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
    
    _validar_csrf(request)
    if not eliminar_usuario(db, usuario_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
