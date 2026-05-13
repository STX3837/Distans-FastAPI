from app import crud
from app.models import RolUsuario
from app.schemas import RolUsuario as RolUsuarioSchema
from app.schemas import UsuarioAdminUpdate, UsuarioUpdate


def test_actualizar_usuario_aplica_solo_campos_enviados(user_factory, db_session):
    user = user_factory(
        nombre="Raul",
        apellidos="Diaz",
        email="raul@example.com",
        ciudad="Madrid",
    )

    datos = UsuarioUpdate(ciudad="Valencia")
    actualizado = crud.actualizar_usuario(db_session, user.id, datos)

    assert actualizado is not None
    assert actualizado.ciudad == "Valencia"
    assert actualizado.nombre == "Raul"


def test_actualizar_usuario_admin_permite_rol_y_activo(user_factory, db_session):
    user = user_factory(email="admin-update@example.com", rol=RolUsuarioSchema.COMPRADOR)

    datos = UsuarioAdminUpdate(rol=RolUsuarioSchema.VENDEDOR, activo=False)
    actualizado = crud.actualizar_usuario_admin(db_session, user.id, datos)

    assert actualizado is not None
    assert actualizado.rol == RolUsuario.VENDEDOR
    assert actualizado.activo is False


def test_autenticar_usuario_devuelve_none_si_password_incorrecta(user_factory, db_session):
    user_factory(email="auth1@example.com", contrasena="real123")

    autenticado = crud.autenticar_usuario(db_session, "auth1@example.com", "mal123")

    assert autenticado is None


def test_autenticar_usuario_devuelve_usuario_si_password_correcta(user_factory, db_session):
    user = user_factory(email="auth2@example.com", contrasena="real123")

    autenticado = crud.autenticar_usuario(db_session, "auth2@example.com", "real123")

    assert autenticado is not None
    assert autenticado.id == user.id
