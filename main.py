from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import os
import asyncio
from contextlib import suppress
from app.routers import users, auth, catalogo, gestion, admin_pedidos, favoritos, pedidos, planes
from app.password_reset import router as password_reset_router
from app.access_control import RequerirAccesoMiddleware

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

app.add_middleware(RequerirAccesoMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret_key,
    same_site="lax",
    https_only=environment in {"production", "staging"},
)

allowed_hosts = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if host.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Cabeceras defensivas comunes sin interferir con Stripe ni Leaflet."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(self)")
    response.headers.setdefault("Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
    if environment in {"production", "staging"}:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

# Servir archivos estáticos
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# El esquema se prepara mediante ``python -m scripts.migrate`` antes de servir HTTP.
@app.on_event("startup")
async def startup_event():
    from app.payment_worker import vigilar_reservas
    app.state.payment_worker = asyncio.create_task(vigilar_reservas())


@app.on_event("shutdown")
async def shutdown_event():
    app.state.payment_worker.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.payment_worker

# Registrar routers
app.include_router(catalogo.router)
app.include_router(favoritos.router)
app.include_router(gestion.router)
app.include_router(planes.router)
app.include_router(admin_pedidos.router)
app.include_router(pedidos.router)
app.include_router(auth.router)
app.include_router(password_reset_router)
app.include_router(users.router)
app.include_router(users.admin_router)
