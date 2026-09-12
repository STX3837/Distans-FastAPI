def test_access_screen_has_three_options(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'href="/registro"' in response.text
    assert 'href="/login"' in response.text
    assert 'action="/invitado"' in response.text
    assert "Entrar como invitado" in response.text
    assert 'id="productsMap"' not in response.text


def test_guest_reaches_home_without_account(client):
    response = client.post("/invitado", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/inicio"
    assert client.get("/inicio").status_code == 200
    assert client.get("/usuarios/me").status_code == 401


def test_guest_clears_authenticated_session_with_csrf(client, user_factory):
    user = user_factory()
    assert client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"}).status_code == 200
    assert client.post("/invitado", follow_redirects=False).status_code == 403
    response = client.post("/invitado", data={"csrf_token": client.cookies.get("csrf_token")}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/inicio"
    assert client.get("/usuarios/me").status_code == 401
    assert client.cookies.get("csrf_token") is None


def test_authenticated_login_and_legacy_welcome_lead_to_home(client, user_factory):
    user = user_factory()
    assert client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"}).status_code == 200
    for url in ["/login", "/bienvenida"]:
        response = client.get(url, follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/inicio"
    home = client.get("/inicio")
    assert home.status_code == 200 and user.nombre in home.text
