from app.models import Categoria, Producto, Tienda, ValoracionProducto, ValoracionTienda
from app.schemas import RolUsuario
from app.crud import eliminar_usuario


def login(client, usuario):
    assert client.post('/api/login', json={'email': usuario.email, 'contrasena': 'clave12345'}).status_code == 200
    return {'X-CSRF-Token': client.cookies.get('csrf_token')}


def test_compradores_valoran_y_actualizan_medias(client, db_session, user_factory):
    vendedor = user_factory(rol=RolUsuario.VENDEDOR)
    tienda = Tienda(nombre='Tienda valorada', vendedor_id=vendedor.id)
    db_session.add(tienda)
    db_session.flush()
    producto = Producto(nombre='Producto valorado', precio=12, categoria=Categoria.HOGAR_BRICOLAJE,
                        tienda_id=tienda.id)
    db_session.add(producto)
    db_session.commit()
    primero = user_factory(email='valorador1@example.com')
    segundo = user_factory(email='valorador2@example.com')

    headers = login(client, primero)
    assert 'Sin valoraciones' in client.get(f'/productos/{producto.id}').text
    for tipo, identificador in [('productos', producto.id), ('tiendas', tienda.id)]:
        url = f'/api/valoraciones/{tipo}/{identificador}'
        assert client.put(url, json={'puntuacion': 5}).status_code == 403
        assert client.put(url, json={'puntuacion': 0}, headers=headers).status_code == 422
        assert client.put(url, json={'puntuacion': 3.5}, headers=headers).status_code == 422
        assert client.put(url, json={'puntuacion': 5}, headers=headers).json()['valoracion_media'] == 5

    headers = login(client, segundo)
    assert client.put(f'/api/valoraciones/productos/{producto.id}', json={'puntuacion': 3}, headers=headers).json()['valoracion_media'] == 4
    assert client.put(f'/api/valoraciones/tiendas/{tienda.id}', json={'puntuacion': 1}, headers=headers).json()['valoracion_media'] == 3
    assert '4.0 / 5' in client.get(f'/productos/{producto.id}').text
    assert '3.0 / 5' in client.get(f'/tiendas/{tienda.id}').text
    assert [p['id'] for p in client.get('/api/productos', params={'valoracion_min': 4}).json()['productos']] == [producto.id]
    assert client.get('/api/productos', params={'valoracion_min': 4.1}).json()['total'] == 0
    assert [t['id'] for t in client.get('/api/tiendas', params={'valoracion_min': 3}).json()] == [tienda.id]
    assert client.get('/api/tiendas', params={'valoracion_min': 3.1}).json() == []

    assert client.put(f'/api/valoraciones/productos/{producto.id}', json={'puntuacion': 1}, headers=headers).json()['valoracion_media'] == 3
    assert db_session.query(ValoracionProducto).count() == 2
    assert db_session.query(ValoracionTienda).count() == 2
    product_page = client.get(f'/productos/{producto.id}').text
    assert 'class="star-rating"' in product_page
    assert 'id="productRating1" name="puntuacion" value="1" checked' in product_page
    assert product_page.count('name="puntuacion"') == 5
    store_page = client.get(f'/tiendas/{tienda.id}').text
    assert 'class="star-rating"' in store_page
    assert 'id="storeRating1" name="puntuacion" value="1" checked' in store_page
    assert store_page.count('name="puntuacion"') == 5
    assert eliminar_usuario(db_session, primero.id)
    db_session.refresh(producto)
    db_session.refresh(tienda)
    assert producto.valoracion_media == 1
    assert tienda.valoracion_media == 1


def test_valoraciones_exigen_comprador_y_elemento_visible(client, db_session, user_factory):
    vendedor = user_factory(rol=RolUsuario.VENDEDOR)
    tienda = Tienda(nombre='Tienda', vendedor_id=vendedor.id)
    db_session.add(tienda)
    db_session.commit()
    url = f'/api/valoraciones/tiendas/{tienda.id}'
    assert client.put(url, json={'puntuacion': 4}).status_code == 401
    headers = login(client, vendedor)
    assert client.put(url, json={'puntuacion': 4}, headers=headers).status_code == 403
    comprador = user_factory(email='valorador3@example.com')
    headers = login(client, comprador)
    assert client.put('/api/valoraciones/tiendas/99999', json={'puntuacion': 4}, headers=headers).status_code == 404
    vendedor.activo = False
    db_session.commit()
    assert client.put(url, json={'puntuacion': 4}, headers=headers).status_code == 404
