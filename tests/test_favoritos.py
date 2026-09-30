import pytest
from app.models import Categoria, Producto, Tienda
from app.schemas import RolUsuario


@pytest.fixture
def catalog(db_session, user_factory):
    vendedor = user_factory(rol=RolUsuario.VENDEDOR)
    tienda = Tienda(nombre='Taller Centro', vendedor_id=vendedor.id)
    db_session.add(tienda)
    db_session.flush()
    producto = Producto(nombre='Taza artesanal', precio=20, categoria=Categoria.HOGAR_BRICOLAJE,
                        tienda_id=tienda.id, stock=5)
    db_session.add(producto)
    db_session.commit()
    return vendedor, tienda, producto, None, None


def entrar(client, usuario):
    assert client.post('/api/login', json={'email': usuario.email, 'contrasena': 'clave12345'}).status_code == 200
    return {'X-CSRF-Token': client.cookies.get('csrf_token')}


def test_favoritos_guardar_listar_y_quitar(client, catalog, user_factory):
    _, tienda, producto, _, _ = catalog
    comprador = user_factory(email='comprador@example.com')
    headers = entrar(client, comprador)
    assert client.get('/favoritos').status_code == 200
    assert 'Favoritos' in client.get('/inicio').text
    for tipo, identificador in [('productos', producto.id), ('tiendas', tienda.id)]:
        url = f'/api/favoritos/{tipo}/{identificador}'
        assert client.put(url, headers=headers).status_code == 200
        assert client.put(url, headers=headers).status_code == 200
    lista = client.get('/api/favoritos').json()
    assert [p['id'] for p in lista['productos']] == [producto.id]
    assert [t['id'] for t in lista['tiendas']] == [tienda.id]
    assert producto.nombre in client.get('/favoritos').text
    assert client.delete(f'/api/favoritos/productos/{producto.id}', headers=headers).status_code == 200
    assert client.get('/api/favoritos').json()['productos'] == []


def test_favoritos_permisos_y_csrf(client, catalog, user_factory):
    vendedor, tienda, producto, _, _ = catalog
    url = f'/api/favoritos/productos/{producto.id}'
    assert client.get('/api/favoritos').status_code == 401
    assert client.put(url).status_code == 401
    entrar(client, vendedor)
    assert client.put(url, headers={'X-CSRF-Token': client.cookies.get('csrf_token')}).status_code == 403
    comprador = user_factory(email='comprador2@example.com')
    entrar(client, comprador)
    assert client.put(url).status_code == 403
    assert client.put('/api/favoritos/tiendas/999999', headers={'X-CSRF-Token': client.cookies.get('csrf_token')}).status_code == 404


def test_favoritos_aislados_y_vendedor_inactivo(client, catalog, user_factory, db_session):
    vendedor, tienda, producto, _, _ = catalog
    primero = user_factory(email='uno@example.com')
    segundo = user_factory(email='dos@example.com')
    headers = entrar(client, primero)
    assert client.put(f'/api/favoritos/productos/{producto.id}', headers=headers).status_code == 200
    assert client.put(f'/api/favoritos/tiendas/{tienda.id}', headers=headers).status_code == 200
    entrar(client, segundo)
    assert client.get('/api/favoritos').json() == {'productos': [], 'tiendas': []}
    entrar(client, primero)
    vendedor.activo = False
    db_session.commit()
    assert client.get('/api/favoritos').json() == {'productos': [], 'tiendas': []}
