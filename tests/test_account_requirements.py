import hashlib
import smtplib
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import password_reset
from app.models import RestablecimientoContrasena, Usuario, Tienda
from app.schemas import RolUsuario
from app.security import hash_password, verify_password


def login(client, user):
    response = client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"})
    assert response.status_code == 200


@pytest.fixture
def outbox(monkeypatch):
    messages = []
    monkeypatch.setattr(password_reset, "enviar_correo", lambda email, token: messages.append((email, token)))
    return messages


def request_token(client, user, outbox):
    response = client.post("/api/recuperar-contrasena", json={"email": user.email})
    assert response.status_code == 200
    return outbox[-1][1]


def test_public_registration_cannot_create_admin(client, db_session):
    response = client.post("/api/registro", json={"nombre": "Ana", "apellidos": "Ruiz", "telefono": "600123123", "direccion": "Calle Sol 1", "ciudad": "Madrid", "codigo_postal": "28001", "email": "intruso@example.com", "contrasena": "clave12345", "rol": "admin"})
    assert response.status_code == 403
    assert db_session.query(Usuario).count() == 0


@pytest.mark.parametrize("password", ["", "corta", "a" * 129])
def test_password_policy_enforced_by_server(client, password):
    response = client.post("/api/registro", json={"nombre": "Ana", "apellidos": "Ruiz", "telefono": "600123123", "direccion": "Calle Sol 1", "ciudad": "Madrid", "codigo_postal": "28001", "email": "ana@example.com", "contrasena": password})
    assert response.status_code == 422


def test_user_can_edit_email_and_clear_optional_fields(client, user_factory, db_session):
    user = user_factory(ciudad="Madrid")
    login(client, user)
    created = user.fecha_creacion
    response = client.put("/usuarios/me", json={"email": "nuevo@example.com", "ciudad": None})
    assert response.status_code == 200
    assert response.json()["email"] == "nuevo@example.com"
    assert response.json()["ciudad"] is None
    assert user.fecha_creacion == created
    assert user.fecha_actualizacion >= created
    assert "contrasena_hash" not in response.json()


@pytest.mark.parametrize("admin", [False, True])
def test_duplicate_email_update_returns_400(client, user_factory, admin):
    user = user_factory(rol=RolUsuario.ADMIN if admin else RolUsuario.COMPRADOR)
    other = user_factory(email="otro@example.com")
    login(client, user)
    url = f"/admin/usuarios/{user.id}" if admin else "/usuarios/me"
    response = client.put(url, json={"email": other.email})
    assert response.status_code == 400
    assert client.get("/usuarios/me").status_code == 200


@pytest.mark.parametrize("changes", [{"nombre": "  "}, {"email": None}, {"apellidos": ""}])
def test_empty_identity_updates_rejected(client, user_factory, changes):
    user = user_factory()
    login(client, user)
    assert client.put("/usuarios/me", json=changes).status_code == 422


@pytest.mark.parametrize("method,url,body", [
    ("PUT", "/usuarios/me", {"ciudad": "Madrid"}),
    ("POST", "/usuarios/me/cambiar-contrasena", {"contrasena_actual": "clave12345", "contrasena_nueva": "nueva12345"}),
    ("PUT", "/admin/usuarios/1", {"ciudad": "Madrid"}),
    ("DELETE", "/admin/usuarios/1", None),
    ("POST", "/admin/usuarios/", {"nombre": "Ana", "apellidos": "Ruiz", "email": "nueva@example.com", "contrasena": "clave12345"}),
])
def test_authenticated_mutations_require_csrf(app, user_factory, method, url, body):
    user = user_factory(rol=RolUsuario.ADMIN)
    with TestClient(app) as raw_client:
        login(raw_client, user)
        assert raw_client.request(method, url, json=body).status_code == 403


def test_html_views_and_admin_permissions(client, user_factory):
    assert client.get("/usuarios/cuenta", follow_redirects=False).status_code == 303
    assert client.get("/admin/usuarios/panel", follow_redirects=False).status_code == 303
    normal = user_factory()
    login(client, normal)
    profile = client.get("/usuarios/cuenta")
    assert profile.status_code == 200 and 'id="cuentaForm"' in profile.text
    assert normal.contrasena_hash not in profile.text
    assert client.get("/admin/usuarios/panel").status_code == 403
    admin = user_factory(email="admin@example.com", rol=RolUsuario.ADMIN)
    login(client, admin)
    assert 'id="adminForm"' in client.get("/admin/usuarios/panel").text
    assert '/admin/usuarios/panel' in client.get("/bienvenida").text


def test_recovery_pages_have_privacy_headers(client):
    for url in ["/recuperar-contrasena", "/restablecer-contrasena"]:
        response = client.get(url)
        assert response.status_code == 200
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "no-store"


def test_recovery_unknown_and_inactive_accounts_same_response(client, user_factory, outbox):
    active = user_factory()
    inactive = user_factory(email="inactivo@example.com", activo=False)
    responses = [client.post("/api/recuperar-contrasena", json={"email": email}) for email in [active.email, inactive.email, "desconocido@example.com"]]
    assert all(r.status_code == 200 and r.json() == responses[0].json() for r in responses)
    assert len(outbox) == 1


def test_recovery_flow_hashes_token_and_password_and_revokes_sessions(client, app, user_factory, db_session, outbox):
    user = user_factory()
    login(client, user)
    second = TestClient(app)
    login(second, user)
    token = request_token(client, user, outbox)
    record = db_session.query(RestablecimientoContrasena).one()
    assert record.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert record.token_hash != token
    response = client.post("/api/restablecer-contrasena", json={"token": token, "contrasena_nueva": "nueva12345"})
    assert response.status_code == 200
    db_session.refresh(user)
    assert verify_password("nueva12345", user.contrasena_hash)
    assert not verify_password("clave12345", user.contrasena_hash)
    assert db_session.query(RestablecimientoContrasena).count() == 0
    assert second.get("/usuarios/me").status_code == 401
    assert client.post("/api/restablecer-contrasena", json={"token": token, "contrasena_nueva": "otra12345"}).status_code == 400
    assert client.post("/api/login", json={"email": user.email, "contrasena": "nueva12345"}).status_code == 200


@pytest.mark.parametrize("invalidation", ["expired", "email", "password", "inactive", "tampered"])
def test_invalid_reset_links_rejected(client, user_factory, db_session, outbox, invalidation):
    user = user_factory()
    token = request_token(client, user, outbox)
    if invalidation == "expired": db_session.query(RestablecimientoContrasena).one().fecha_expiracion = datetime.utcnow() - timedelta(seconds=1)
    elif invalidation == "email": user.email = "cambiado@example.com"
    elif invalidation == "password": user.contrasena_hash = hash_password("otra12345")
    elif invalidation == "inactive": user.activo = False
    else: token = "x" * 43
    db_session.commit()
    original = user.contrasena_hash
    assert client.post("/api/restablecer-contrasena", json={"token": token, "contrasena_nueva": "nueva12345"}).status_code == 400
    db_session.refresh(user)
    assert user.contrasena_hash == original


def test_recovery_cooldown_and_retry_after_smtp_failure(client, user_factory, db_session, outbox, monkeypatch):
    user = user_factory()
    request_token(client, user, outbox)
    request_token(client, user, outbox)
    assert len(outbox) == 1
    db_session.query(RestablecimientoContrasena).one().fecha_expiracion -= timedelta(minutes=2)
    db_session.commit()
    def fail(*args): raise smtplib.SMTPException("failure")
    monkeypatch.setattr(password_reset, "enviar_correo", fail)
    response = client.post("/api/recuperar-contrasena", json={"email": user.email})
    assert response.status_code == 200
    assert db_session.query(RestablecimientoContrasena).count() == 1
    monkeypatch.setattr(password_reset, "enviar_correo", lambda email, token: outbox.append((email, token)))
    request_token(client, user, outbox)
    assert len(outbox) == 2


def test_seller_deletion_preserves_shops(client, user_factory, db_session):
    admin = user_factory(rol=RolUsuario.ADMIN)
    seller = user_factory(email="seller@example.com", rol=RolUsuario.VENDEDOR)
    shop = Tienda(nombre="Tienda", vendedor_id=seller.id)
    db_session.add(shop); db_session.commit()
    login(client, admin)
    assert client.delete(f"/admin/usuarios/{seller.id}").status_code == 409
    assert db_session.get(Usuario, seller.id) is not None
    assert db_session.get(Tienda, shop.id) is not None


def test_password_hash_has_unique_salt_and_work_factor():
    first, second = hash_password("clave12345"), hash_password("clave12345")
    assert first != second
    assert first.startswith("$pbkdf2-sha256$600000$")
    assert verify_password("clave12345", first)


def test_smtp_delivery_uses_configured_public_url_and_tls(monkeypatch):
    events = []
    class FakeSMTP:
        def __init__(self, host, port, timeout): events.append((host, port, timeout))
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def starttls(self, context): events.append("tls")
        def login(self, user, password): events.append((user, password))
        def send_message(self, message): events.append(message)
    monkeypatch.setattr(password_reset.smtplib, "SMTP", FakeSMTP)
    for key, value in {"PUBLIC_BASE_URL": "https://distans.example", "SMTP_HOST": "smtp.example", "SMTP_PORT": "587", "SMTP_FROM": "no-reply@example.com", "SMTP_USER": "smtp-user", "SMTP_PASSWORD": "smtp-password", "SMTP_STARTTLS": "true"}.items(): monkeypatch.setenv(key, value)
    password_reset.enviar_correo("ana@example.com", "token-example")
    assert "tls" in events
    assert events[-1]["To"] == "ana@example.com"
    assert "https://distans.example/restablecer-contrasena#token-example" in events[-1].get_content()


def test_admin_creates_inactive_user_in_one_operation(client, user_factory, db_session):
    admin = user_factory(rol=RolUsuario.ADMIN)
    login(client, admin)
    response = client.post("/admin/usuarios/", json={"nombre": "Ana", "apellidos": "Ruiz", "email": "nueva@example.com", "contrasena": "clave12345", "activo": False})
    assert response.status_code == 201
    assert response.json()["activo"] is False
    assert db_session.get(Usuario, response.json()["id"]).activo is False
