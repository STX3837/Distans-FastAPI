import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.crud import autenticar_usuario, crear_usuario
from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate

router = APIRouter(tags=["autenticación"])
templates = Jinja2Templates(directory="templates")


class LoginRequest(BaseModel):
    email: EmailStr
    contrasena: str


def _template_context(request: Request, active_route: str = "", user_name: str | None = None) -> dict:
    return {
        "request": request,
        "active_route": active_route,
        "user_name": user_name,
    }


def _validar_csrf(request: Request) -> None:
    """Valida token CSRF con patrón double-submit cookie."""
    session_token = request.session.get("csrf_token")
    header_token = request.headers.get("x-csrf-token")
    cookie_token = request.cookies.get("csrf_token")

    if not session_token or not header_token or not cookie_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token faltante",
        )

    if session_token != header_token or session_token != cookie_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token inválido",
        )


@router.get("/", response_class=HTMLResponse)
def pagina_inicio(request: Request):
    """Página de inicio con redirección visual al registro."""
    return templates.TemplateResponse(
        request=request,
        name="inicio.html",
        context=_template_context(request, active_route="/registro"),
    )


@router.get("/registro", response_class=HTMLResponse)
def pagina_registro(request: Request):
    """Sirve la página HTML de registro."""
    return templates.TemplateResponse(
        request=request,
        name="registro.html",
        context=_template_context(request, active_route="/registro"),
    )


@router.post("/api/registro", status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario_data: UsuarioCreate, db: Session = Depends(get_db)):
    """Endpoint de API para registrar un nuevo usuario."""
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario_data.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado",
        )

    if isinstance(usuario_data.rol, str):
        from app.schemas import RolUsuario as RolUsuarioSchema

        try:
            usuario_data.rol = RolUsuarioSchema(usuario_data.rol)
        except Exception:
            raise HTTPException(status_code=400, detail="Rol no válido")

    try:
        nuevo_usuario = crear_usuario(db, usuario_data)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    return {
        "id": nuevo_usuario.id,
        "nombre": nuevo_usuario.nombre,
        "apellidos": nuevo_usuario.apellidos,
        "email": nuevo_usuario.email,
        "rol": nuevo_usuario.rol.value,
        "mensaje": "Usuario registrado exitosamente",
    }


@router.post("/api/login", status_code=status.HTTP_200_OK)
def iniciar_sesion(datos: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Verifica credenciales y guarda la sesión del usuario."""
    usuario = autenticar_usuario(db, datos.email, datos.contrasena)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta está inactiva",
        )

    request.session["usuario"] = {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "apellidos": usuario.apellidos,
        "email": usuario.email,
    }
    csrf_token = secrets.token_urlsafe(32)
    request.session["csrf_token"] = csrf_token

    response = JSONResponse(content={
        "mensaje": "Inicio de sesión correcto",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "apellidos": usuario.apellidos,
            "email": usuario.email,
        },
    })
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@router.post("/api/logout", status_code=status.HTTP_200_OK)
def cerrar_sesion(request: Request):
    """Cierra la sesión del usuario actual."""
    _validar_csrf(request)
    request.session.clear()
    response = JSONResponse(content={"mensaje": "Sesión cerrada"})
    response.delete_cookie("csrf_token")
    return response


@router.get("/login", response_class=HTMLResponse)
def pagina_login(request: Request):
    """Página de login."""
    if request.session.get("usuario"):
        return RedirectResponse(url="/bienvenida", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=_template_context(request, active_route="/login"),
    )


@router.get("/bienvenida", response_class=HTMLResponse)
def pagina_bienvenida(request: Request):
    """Página mostrada después de un login correcto."""
    usuario = request.session.get("usuario")
    if not usuario:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="bienvenida.html",
        context=_template_context(
            request,
            active_route="/bienvenida",
            user_name=usuario.get("nombre", "Usuario"),
        ),
    )
