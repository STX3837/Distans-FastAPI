from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os
from app.database import engine
from app.models import Base
from app.routers import users, auth

# Crear la aplicación FastAPI
app = FastAPI(
    title="Distans - Sistema de Gestión",
    description="API para gestión de usuarios con soporte administrativo",
    version="1.0.0"
)

environment = os.getenv("ENVIRONMENT", "development").lower()
session_secret_key = os.getenv("SESSION_SECRET_KEY")
if not session_secret_key:
    raise RuntimeError("SESSION_SECRET_KEY environment variable is required")

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret_key,
    same_site="lax",
    https_only=environment in {"production", "staging"},
)

# Servir archivos estáticos
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Crear las tablas en la BD (En un proyecto real se usan migraciones con 'Alembic')
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

# Registrar routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(users.admin_router)