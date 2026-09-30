"""Recuperación con tokens aleatorios, caducables y de un solo uso."""
import hashlib
import logging
import os
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib.parse import urlsplit

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario, RestablecimientoContrasena
from app.routers.auth import templates
from app.security import hash_password

router = APIRouter(tags=["recuperación de contraseña"])
logger = logging.getLogger(__name__)


class Solicitud(BaseModel):
    email: EmailStr


class Confirmacion(BaseModel):
    token: str = Field(min_length=40, max_length=128)
    contrasena_nueva: str = Field(min_length=8, max_length=128)


def enviar_correo(destinatario: str, token: str):
    base = os.getenv("PUBLIC_BASE_URL", "http://localhost:8001").rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("PUBLIC_BASE_URL no es válida")
    if os.getenv("ENVIRONMENT", "development") in {"production", "staging"} and parsed.scheme != "https":
        raise ValueError("PUBLIC_BASE_URL debe utilizar HTTPS")
    message = EmailMessage()
    message["Subject"] = "Restablecer tu contraseña de Distans"
    message["From"] = os.environ["SMTP_FROM"]
    message["To"] = destinatario
    # El fragmento evita incluir el token en los registros de acceso del servidor.
    message.set_content("Para restablecer tu contraseña abre este enlace (caduca en 30 minutos):\n"
                        + base + "/restablecer-contrasena#" + token
                        + "\nSi no lo solicitaste, puedes ignorar este mensaje.")
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=10) as smtp:
        if os.getenv("SMTP_STARTTLS", "true").lower() == "true":
            smtp.starttls(context=ssl.create_default_context())
        if os.getenv("SMTP_USER"):
            smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)


def entregar_correo(engine, token_hash: str, email: str, token: str):
    try:
        enviar_correo(email, token)
    except (OSError, smtplib.SMTPException, KeyError, ValueError):
        # Una sesión independiente evita depender del ciclo de vida de la petición.
        with Session(bind=engine) as db:
            db.query(RestablecimientoContrasena).filter_by(token_hash=token_hash).delete()
            db.commit()
        logger.error("No se pudo enviar el correo de recuperación; revisa la configuración SMTP")


@router.get("/recuperar-contrasena", response_class=HTMLResponse)
@router.get("/restablecer-contrasena", response_class=HTMLResponse)
def pagina_recuperacion(request: Request):
    response = templates.TemplateResponse(request=request, name="recuperacion.html", context={
        "restablecer": request.url.path == "/restablecer-contrasena",
    })
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/api/recuperar-contrasena")
def solicitar(datos: Solicitud, background: BackgroundTasks, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter_by(email=datos.email, activo=True).with_for_update().first()
    now = datetime.utcnow()
    if usuario:
        reciente = db.query(RestablecimientoContrasena).filter(
            RestablecimientoContrasena.usuario_id == usuario.id,
            RestablecimientoContrasena.fecha_expiracion > now + timedelta(minutes=29),
        ).first()
        if not reciente:
            token = secrets.token_urlsafe(32)
            registro = RestablecimientoContrasena(
                token_hash=hashlib.sha256(token.encode()).hexdigest(), usuario_id=usuario.id,
                email=usuario.email, contrasena_anterior_hash=usuario.contrasena_hash,
                fecha_expiracion=now + timedelta(minutes=30),
            )
            db.query(RestablecimientoContrasena).filter(
                RestablecimientoContrasena.usuario_id == usuario.id,
                RestablecimientoContrasena.fecha_expiracion <= now,
            ).delete()
            db.add(registro)
            db.commit()
            # El envío SMTP ocurre después de responder, para no revelar cuentas por su tiempo de envío.
            background.add_task(entregar_correo, db.get_bind(), registro.token_hash, usuario.email, token)
    return {"mensaje": "Si el correo corresponde a una cuenta activa, recibirás un enlace para restablecer tu contraseña."}


@router.post("/api/restablecer-contrasena")
def confirmar(datos: Confirmacion, request: Request, db: Session = Depends(get_db)):
    registro = db.query(RestablecimientoContrasena).filter_by(
        token_hash=hashlib.sha256(datos.token.encode()).hexdigest(),
    ).first()
    if not registro or registro.fecha_expiracion <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="El enlace no es válido o ha caducado")
    usuario = db.query(Usuario).filter_by(id=registro.usuario_id).first()
    if not usuario or not usuario.activo or usuario.email != registro.email or usuario.contrasena_hash != registro.contrasena_anterior_hash:
        raise HTTPException(status_code=400, detail="El enlace no es válido o ha caducado")
    # La actualización condicional impide utilizar simultáneamente dos enlaces de la misma cuenta.
    actualizados = db.query(Usuario).filter_by(
        id=usuario.id, email=registro.email, activo=True,
        contrasena_hash=registro.contrasena_anterior_hash,
    ).update({Usuario.contrasena_hash: hash_password(datos.contrasena_nueva)}, synchronize_session=False)
    if actualizados != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="El enlace no es válido o ha caducado")
    db.query(RestablecimientoContrasena).filter_by(usuario_id=usuario.id).delete(synchronize_session=False)
    db.commit()
    request.session.clear()
    return {"mensaje": "Contraseña restablecida. Ya puedes iniciar sesión."}
