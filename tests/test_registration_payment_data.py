import pytest
from app.models import Usuario


FIELDS = ["telefono", "direccion", "ciudad", "codigo_postal"]


def registration(role="comprador"):
    return {"nombre": "Lucía", "apellidos": "Gómez", "email": "lucia@example.com", "contrasena": "clave12345", "rol": role, "telefono": "600123123", "direccion": "Calle Sol 1", "ciudad": "Madrid", "codigo_postal": "28001"}


@pytest.mark.parametrize("role", ["comprador", "vendedor"])
def test_registration_login_and_reusable_payment_data(client, db_session, role):
    payload = registration(role)
    for field in FIELDS: payload[field] = "  " + payload[field] + "  "
    assert client.post("/api/registro", json=payload).status_code == 201
    response = client.post("/api/login", json={"email": payload["email"], "contrasena": payload["contrasena"]})
    assert response.status_code == 200
    assert client.get("/usuarios/me").json()["rol"] == role
    response = client.get("/usuarios/me/datos-pago")
    assert response.status_code == 200
    expected = {field: payload[field].strip() for field in ["nombre", "apellidos", "email"] + FIELDS}
    assert response.json() == expected
    user = db_session.query(Usuario).one()
    assert all(getattr(user, field) == expected[field] for field in FIELDS)
    assert "contrasena" not in response.json() and "contrasena_hash" not in response.json()


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("invalid", [None, "", "   ", "missing"])
def test_registration_requires_contact_and_address(client, db_session, field, invalid):
    payload = registration()
    if invalid == "missing": del payload[field]
    else: payload[field] = invalid
    response = client.post("/api/registro", json=payload)
    assert response.status_code == 422
    assert any(error["loc"][-1] == field for error in response.json()["detail"])
    assert db_session.query(Usuario).count() == 0


def test_payment_data_requires_session(client):
    assert client.get("/usuarios/me/datos-pago").status_code == 401


def test_existing_incomplete_account_can_complete_data(client, user_factory):
    user = user_factory()
    assert client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"}).status_code == 200
    assert client.get("/usuarios/me/datos-pago").status_code == 409
    data = {field: registration()[field] for field in FIELDS}
    assert client.put("/usuarios/me", json=data).status_code == 200
    assert client.get("/usuarios/me/datos-pago").status_code == 200


def test_payment_data_always_uses_current_account(client, user_factory):
    user = user_factory()
    other = user_factory(email="otro@example.com")
    assert client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"}).status_code == 200
    assert client.put("/usuarios/me", json={field: registration()[field] for field in FIELDS}).status_code == 200
    response = client.get(f"/usuarios/me/datos-pago?usuario_id={other.id}")
    assert response.status_code == 200 and response.json()["email"] == user.email


@pytest.mark.parametrize("invalidated", ["password", "inactive"])
def test_login_page_accepts_account_with_revoked_session(client, user_factory, db_session, invalidated):
    from app.security import hash_password
    user = user_factory()
    assert client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"}).status_code == 200
    if invalidated == "password": user.contrasena_hash = hash_password("nueva12345")
    else: user.activo = False
    db_session.commit()
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 200
    assert 'id="loginForm"' in response.text


def test_registration_page_marks_buyer_data_required(client):
    from html.parser import HTMLParser
    class Inputs(HTMLParser):
        def __init__(self):
            super().__init__()
            self.fields = {}
        def handle_starttag(self, tag, attrs):
            if tag == "input":
                attributes = dict(attrs)
                self.fields[attributes.get("name")] = attributes
    parser = Inputs()
    response = client.get("/registro")
    assert response.status_code == 200
    parser.feed(response.text)
    assert all("required" in parser.fields[field] for field in FIELDS + ["nombre", "apellidos", "email", "contrasena"])
