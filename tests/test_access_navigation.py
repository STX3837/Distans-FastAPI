import pytest
from fastapi.testclient import TestClient


def test_access_screen_has_three_options(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'href="/registro"' in response.text
    assert 'href="/login"' in response.text
    assert 'action="/invitado"' in response.text
    assert "Entrar como invitado" in response.text
    token = client.cookies.get("csrf_token")
    assert token and f'name="csrf_token" value="{token}"' in response.text
    assert 'id="productsMap"' not in response.text
    assert 'href="/carrito"' not in response.text
    assert 'aria-label="Usuario"' not in response.text


def test_login_offers_guest_mode_without_cart_or_account_controls(app):
    visitor = TestClient(app)
    response = visitor.get("/login")
    assert response.status_code == 200
    assert 'action="/invitado"' in response.text
    assert "Entrar como invitado" in response.text
    assert 'href="/carrito"' not in response.text
    assert 'href="/usuarios/cuenta"' not in response.text
    assert 'class="persistent-cart"' not in response.text
    assert 'class="market-header"' not in response.text
    assert 'aria-label="Navegación de compras"' not in response.text


@pytest.mark.parametrize("path", [
    "/inicio", "/carrito", "/productos/1", "/tiendas/1", "/pedidos/seguimiento",
])
def test_visitor_must_choose_guest_or_login_before_viewing_content(app, path):
    visitor = TestClient(app)
    response = visitor.get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_visitor_cannot_use_application_apis_before_choosing_access(app):
    visitor = TestClient(app)
    response = visitor.get("/api/productos")
    assert response.status_code == 401
    assert response.json()["detail"] == "Debes iniciar sesión o entrar como invitado"


def test_guest_reaches_home_without_account(client):
    response = client.post("/invitado", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/inicio"
    home = client.get("/inicio")
    assert home.status_code == 200
    assert 'cart-icon' in home.text
    assert 'class="persistent-cart"' in home.text
    assert 'href="/usuarios/cuenta"' not in home.text
    assert client.get("/usuarios/me").status_code == 401


def test_login_keeps_existing_guest_session_and_shows_guest_navigation(client):
    login = client.get("/login")
    assert login.status_code == 200
    assert "Ya estás conectado como" in login.text
    assert "Invitado" in login.text
    assert 'action="/invitado"' not in login.text
    assert 'aria-label="Navegación de compras"' in login.text
    assert 'href="/inicio?tab=tiendas"' in login.text


@pytest.mark.parametrize("path", [
    "/usuarios/cuenta", "/favoritos", "/pedidos/historial", "/mi-tienda",
    "/admin/tiendas", "/admin/usuarios/panel", "/admin/pedidos/panel",
    "/gestion/plan", "/gestion/plan/resultado", "/gestion/tiendas/nueva",
    "/gestion/tiendas/999/editar", "/gestion/tiendas/999/productos",
    "/gestion/tiendas/999/estadisticas", "/gestion/tiendas/999/pedidos",
])
def test_private_pages_redirect_anonymous_users_to_login(client, path):
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_public_pages_and_private_apis_keep_their_existing_behavior(client):
    for path in ("/inicio", "/carrito"):
        assert client.get(path).status_code == 200
    assert client.get("/api/favoritos").status_code == 401
    assert client.get("/usuarios/me").status_code == 401


def test_guest_clears_authenticated_session_with_csrf(client, user_factory):
    user = user_factory()
    assert client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"}).status_code == 200
    assert client.post("/invitado", follow_redirects=False).status_code == 403
    response = client.post("/invitado", data={"csrf_token": client.cookies.get("csrf_token")}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/inicio"
    assert client.get("/usuarios/me").status_code == 401
    assert client.cookies.get("csrf_token") is None


def test_guest_button_restores_missing_csrf_cookie_for_authenticated_session(client, user_factory):
    user = user_factory()
    assert client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"}).status_code == 200
    client.cookies.delete("csrf_token")
    access = client.get("/")
    token = client.cookies.get("csrf_token")
    assert token and f'name="csrf_token" value="{token}"' in access.text
    response = client.post("/invitado", data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/inicio"


def test_authenticated_login_shows_navigation_and_legacy_welcome_leads_home(client, user_factory):
    user = user_factory()
    assert client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"}).status_code == 200
    login = client.get("/login", follow_redirects=False)
    assert login.status_code == 200
    assert 'aria-label="Navegación de compras"' in login.text
    assert user.nombre in login.text
    assert 'class="market-icon account-icon"' in login.text
    assert '>Mi cuenta<' not in login.text
    welcome = client.get("/bienvenida", follow_redirects=False)
    assert welcome.status_code == 303 and welcome.headers["location"] == "/inicio"
    home = client.get("/inicio")
    assert home.status_code == 200 and user.nombre in home.text
