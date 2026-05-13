from app.models import RolUsuario
from app.security import verify_password
from app.schemas import RolUsuario as RolUsuarioSchema


def test_registro_exitoso_crea_usuario(client, db_session):
    payload = {
        "nombre": "Lucia",
        "apellidos": "Gomez",
        "email": "lucia@example.com",
        "telefono": "600123123",
        "rol": "comprador",
        "ciudad": "Madrid",
        "direccion": "Calle Sol 1",
        "codigo_postal": "28001",
        "contrasena": "mi-clave-segura",
    }

    response = client.post("/api/registro", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == payload["email"]
    assert body["rol"] == "comprador"

    from app.models import Usuario

    user = db_session.query(Usuario).filter(Usuario.email == payload["email"]).first()
    assert user is not None
    assert user.contrasena_hash != payload["contrasena"]
    assert verify_password(payload["contrasena"], user.contrasena_hash)


def test_registro_email_duplicado_devuelve_400(client, user_factory):
    user_factory(email="repetido@example.com")

    payload = {
        "nombre": "Otro",
        "apellidos": "Usuario",
        "email": "repetido@example.com",
        "rol": "comprador",
        "contrasena": "clave123",
    }

    response = client.post("/api/registro", json=payload)

    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()


def test_login_exitoso_y_bienvenida_con_sesion(client, user_factory):
    user = user_factory(
        nombre="Carlos",
        apellidos="Ruiz",
        email="carlos@example.com",
        contrasena="abc12345",
    )

    login_response = client.post(
        "/api/login",
        json={"email": user.email, "contrasena": "abc12345"},
    )

    assert login_response.status_code == 200
    assert login_response.json()["usuario"]["nombre"] == "Carlos"

    welcome_response = client.get("/bienvenida")
    assert welcome_response.status_code == 200
    assert "¡Bienvenido!" in welcome_response.text
    assert "Carlos" in welcome_response.text


def test_login_invalido_devuelve_401(client, user_factory):
    user_factory(email="maria@example.com", contrasena="clave-real")

    response = client.post(
        "/api/login",
        json={"email": "maria@example.com", "contrasena": "clave-mala"},
    )

    assert response.status_code == 401
    assert "incorrectos" in response.json()["detail"].lower()


def test_login_usuario_inactivo_devuelve_403(client, user_factory):
    user_factory(email="inactivo@example.com", contrasena="clave123", activo=False)

    response = client.post(
        "/api/login",
        json={"email": "inactivo@example.com", "contrasena": "clave123"},
    )

    assert response.status_code == 403
    assert "inactiva" in response.json()["detail"].lower()


def test_bienvenida_sin_sesion_redirige_a_login(client):
    response = client.get("/bienvenida", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_logout_cierra_sesion(client, user_factory):
    user_factory(email="logout@example.com", contrasena="clave123")

    login_response = client.post(
        "/api/login",
        json={"email": "logout@example.com", "contrasena": "clave123"},
    )
    assert login_response.status_code == 200

    csrf_token = client.cookies.get("csrf_token")
    assert csrf_token is not None

    logout_response = client.post(
        "/api/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert logout_response.status_code == 200

    welcome_response = client.get("/bienvenida", follow_redirects=False)
    assert welcome_response.status_code == 303
    assert welcome_response.headers["location"] == "/login"


def test_logout_sin_csrf_devuelve_403(client, user_factory):
    user_factory(email="logout-nocsrf@example.com", contrasena="clave123")

    login_response = client.post(
        "/api/login",
        json={"email": "logout-nocsrf@example.com", "contrasena": "clave123"},
    )
    assert login_response.status_code == 200

    response = client.post("/api/logout")

    assert response.status_code == 403
    assert "csrf" in response.json()["detail"].lower()


def test_logout_con_csrf_invalido_devuelve_403(client, user_factory):
    user_factory(email="logout-badcsrf@example.com", contrasena="clave123")

    login_response = client.post(
        "/api/login",
        json={"email": "logout-badcsrf@example.com", "contrasena": "clave123"},
    )
    assert login_response.status_code == 200

    response = client.post(
        "/api/logout",
        headers={"X-CSRF-Token": "token-invalido"},
    )

    assert response.status_code == 403
    assert "csrf" in response.json()["detail"].lower()


def test_obtener_y_actualizar_perfil_usuario(client, user_factory):
    user = user_factory(
        nombre="Sonia",
        apellidos="Mata",
        email="sonia@example.com",
        contrasena="clave123",
    )

    login_response = client.post(
        "/api/login",
        json={"email": "sonia@example.com", "contrasena": "clave123"},
    )
    assert login_response.status_code == 200

    profile_response = client.get("/usuarios/me")
    assert profile_response.status_code == 200
    assert profile_response.json()["email"] == "sonia@example.com"

    update_response = client.put(
        "/usuarios/me",
        json={"ciudad": "Sevilla", "telefono": "611000111"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["ciudad"] == "Sevilla"
    assert update_response.json()["telefono"] == "611000111"


def test_perfil_requiere_sesion(client):
    response = client.get("/usuarios/me")

    assert response.status_code == 401
    assert "autenticado" in response.json()["detail"].lower()


def test_perfil_usuario_inactivo_devuelve_403(client, user_factory):
    user = user_factory(email="perfil-inactivo@example.com", activo=False)

    login_response = client.post(
        "/api/login",
        json={"email": user.email, "contrasena": "clave123"},
    )
    assert login_response.status_code == 403

    response = client.get("/usuarios/me")

    assert response.status_code == 401
    assert "autenticado" in response.json()["detail"].lower()


def test_query_param_usuario_id_no_permite_suplantacion(client, user_factory):
    user1 = user_factory(email="user1@example.com", contrasena="clave123")
    user2 = user_factory(email="user2@example.com", contrasena="clave456")

    login_response = client.post(
        "/api/login",
        json={"email": user1.email, "contrasena": "clave123"},
    )
    assert login_response.status_code == 200

    response = client.get(f"/usuarios/me?usuario_id={user2.id}")

    assert response.status_code == 200
    assert response.json()["id"] == user1.id


def test_cambiar_contrasena_y_relogin(client, user_factory):
    user = user_factory(email="clave@example.com", contrasena="anterior123")

    login_response = client.post(
        "/api/login",
        json={"email": "clave@example.com", "contrasena": "anterior123"},
    )
    assert login_response.status_code == 200

    change_response = client.post(
        "/usuarios/me/cambiar-contrasena",
        json={
            "contrasena_actual": "anterior123",
            "contrasena_nueva": "nueva12345",
        },
    )
    assert change_response.status_code == 200

    bad_login = client.post(
        "/api/login",
        json={"email": "clave@example.com", "contrasena": "anterior123"},
    )
    assert bad_login.status_code == 401

    good_login = client.post(
        "/api/login",
        json={"email": "clave@example.com", "contrasena": "nueva12345"},
    )
    assert good_login.status_code == 200


def test_admin_sin_permisos_no_puede_listar(client, user_factory):
    user = user_factory(email="normal@example.com", rol=RolUsuarioSchema.COMPRADOR)

    login_response = client.post(
        "/api/login",
        json={"email": user.email, "contrasena": "clave123"},
    )
    assert login_response.status_code == 200

    response = client.get("/admin/usuarios/")

    assert response.status_code == 403
    assert "administrador" in response.json()["detail"].lower()


def test_admin_sin_sesion_devuelve_401(client):
    response = client.get("/admin/usuarios/")

    assert response.status_code == 401
    assert "autenticado" in response.json()["detail"].lower()


def test_admin_puede_listar_crear_actualizar_y_eliminar(client, user_factory):
    admin = user_factory(
        email="admin@example.com",
        rol=RolUsuarioSchema.ADMIN,
        contrasena="admin123",
    )
    existente = user_factory(email="existente@example.com", rol=RolUsuarioSchema.COMPRADOR)

    login_response = client.post(
        "/api/login",
        json={"email": admin.email, "contrasena": "admin123"},
    )
    assert login_response.status_code == 200

    list_response = client.get("/admin/usuarios/")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 2

    create_response = client.post(
        "/admin/usuarios/",
        json={
            "nombre": "Nuevo",
            "apellidos": "Usuario",
            "email": "nuevo-admin@example.com",
            "rol": "vendedor",
            "contrasena": "clave123",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    update_response = client.put(
        f"/admin/usuarios/{existente.id}",
        json={"rol": "vendedor", "activo": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["rol"] == RolUsuario.VENDEDOR.value
    assert update_response.json()["activo"] is False

    delete_response = client.delete(
        f"/admin/usuarios/{created_id}"
    )
    assert delete_response.status_code == 204

    get_deleted = client.get(
        f"/admin/usuarios/{created_id}"
    )
    assert get_deleted.status_code == 404
