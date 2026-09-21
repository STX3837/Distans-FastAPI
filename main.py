from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os
import asyncio
import logging
from contextlib import suppress
from sqlalchemy import text
from app.database import engine
from app.models import Base, Tienda
from app.routers import users, auth, catalogo, gestion, admin_pedidos, favoritos, pedidos
from app.password_reset import router as password_reset_router
from app.migrations import actualizar_pedidos, actualizar_cesta, actualizar_filtros

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
async def startup_event():
    Base.metadata.create_all(bind=engine)
    # create_all no añade índices a tablas existentes.
    with engine.connect() as connection:
        vendedores_duplicados = connection.execute(text(
            "SELECT vendedor_id FROM tiendas GROUP BY vendedor_id HAVING COUNT(*) > 1 LIMIT 1"
        )).first()
    if vendedores_duplicados:
        logging.warning("No se crea el índice único de tiendas: hay vendedores con varias tiendas existentes")
    else:
        for index in Tienda.__table__.indexes:
            if index.name == "uq_tiendas_vendedor_id":
                index.create(bind=engine, checkfirst=True)
    actualizar_pedidos(engine)
    actualizar_cesta(engine)
    actualizar_filtros(engine)
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
app.include_router(admin_pedidos.router)
app.include_router(pedidos.router)
app.include_router(auth.router)
app.include_router(password_reset_router)
app.include_router(users.router)
app.include_router(users.admin_router)
