from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.sessions import SessionMiddleware

from app import crud
from app.database import get_db
from app.models import Usuario
from app.routers import auth, users
from app.schemas import RolUsuario as RolUsuarioSchema
from app.schemas import UsuarioCreate


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Crea una base de datos SQLite en memoria por test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Usuario.__table__.create(bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def app(db_session: Session) -> FastAPI:
    """App de pruebas con dependencias sobreescritas y middleware de sesión."""
    test_app = FastAPI()
    test_app.add_middleware(SessionMiddleware, secret_key="test-session-secret")

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.include_router(auth.router)
    test_app.include_router(users.router)
    test_app.include_router(users.admin_router)
    return test_app


@pytest.fixture(scope="function")
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="function")
def user_factory(db_session: Session):
    """Creador de usuarios reutilizable para tests."""

    def _create_user(
        *,
        nombre: str = "Ana",
        apellidos: str = "Pérez",
        email: str = "ana@example.com",
        contrasena: str = "clave123",
        rol: RolUsuarioSchema = RolUsuarioSchema.COMPRADOR,
        ciudad: str | None = None,
        activo: bool = True,
    ) -> Usuario:
        data = UsuarioCreate(
            nombre=nombre,
            apellidos=apellidos,
            email=email,
            telefono=None,
            direccion=None,
            ciudad=ciudad,
            codigo_postal=None,
            contrasena=contrasena,
            rol=rol,
        )
        user = crud.crear_usuario(db_session, data)
        user.activo = activo
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user
