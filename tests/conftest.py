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
from app.models import Base, Usuario, RestablecimientoContrasena
from app.password_reset import router as password_reset_router
from app.routers import auth, users, catalogo, gestion
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

    Base.metadata.create_all(bind=engine, tables=[t for t in Base.metadata.sorted_tables if t.name != "ubicaciones"])
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
    test_app.include_router(catalogo.router)
    test_app.include_router(gestion.router)
    test_app.include_router(auth.router)
    test_app.include_router(password_reset_router)
    test_app.include_router(users.router)
    test_app.include_router(users.admin_router)
    return test_app


@pytest.fixture(scope="function")
def client(app: FastAPI) -> TestClient:
    class CsrfClient(TestClient):
        def request(self, method, url, **kwargs):
            if method.upper() in {"POST", "PUT", "DELETE", "PATCH"} and str(url).startswith(("/usuarios", "/admin/usuarios")):
                headers = dict(kwargs.pop("headers", {}) or {})
                token = self.cookies.get("csrf_token")
                if token:
                    headers.setdefault("X-CSRF-Token", token)
                kwargs["headers"] = headers
            return super().request(method, url, **kwargs)
    return CsrfClient(app)


@pytest.fixture(scope="function")
def user_factory(db_session: Session):
    """Creador de usuarios reutilizable para tests."""

    def _create_user(
        *,
        nombre: str = "Ana",
        apellidos: str = "Pérez",
        email: str = "ana@example.com",
        contrasena: str = "clave12345",
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
