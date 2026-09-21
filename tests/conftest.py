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
from app.routers import auth, users, catalogo, gestion, admin_pedidos, favoritos
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
    test_app.include_router(favoritos.router)
    test_app.include_router(gestion.router)
    test_app.include_router(admin_pedidos.router)
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

@pytest.fixture
def stripe_gateway(monkeypatch):
    from types import SimpleNamespace
    import stripe
    from datetime import datetime, timezone
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_fake')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', 'whsec_test')
    monkeypatch.setenv('PUBLIC_BASE_URL', 'http://localhost:8000')
    sessions = {}
    creations = []
    def create(params, options=None):
        key = options['idempotency_key']
        if key in sessions:
            return sessions[key]
        result = dict(id='cs_test_' + str(len(creations)), url='https://checkout.stripe.com/c/pay/test',
            status='open', payment_status='unpaid', currency='eur',
            amount_total=sum(line['price_data']['unit_amount'] * line['quantity'] for line in params['line_items']),
            metadata=params['metadata'], client_reference_id=params['client_reference_id'], expires_at=params['expires_at'])
        sessions[key] = result
        creations.append(params)
        return result
    def retrieve(session_id):
        return next(session for session in sessions.values() if session['id'] == session_id)
    def expire(session_id):
        result = retrieve(session_id)
        result['status'] = 'expired'
        return result
    api = SimpleNamespace(create=create, retrieve=retrieve, expire=expire)
    monkeypatch.setattr(stripe, 'StripeClient', lambda *args, **kwargs: SimpleNamespace(v1=SimpleNamespace(checkout=SimpleNamespace(sessions=api))))
    return SimpleNamespace(sessions=sessions, creations=creations, api=api)
