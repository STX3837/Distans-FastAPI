from app.models import Categoria, ComentarioProducto, ComentarioTienda, Producto, Tienda
from app.schemas import RolUsuario
from app.crud import eliminar_usuario


def login(client, usuario):
    assert client.post('/api/login', json={'email': usuario.email, 'contrasena': 'clave12345'}).status_code == 200
    return {'X-CSRF-Token': client.cookies.get('csrf_token')}


def test_comentarios_producto_y_tienda_son_independientes_de_las_estrellas(client, db_session, user_factory):
    vendedor = user_factory(rol=RolUsuario.VENDEDOR)
    tienda = Tienda(nombre='Tienda comentada', vendedor_id=vendedor.id)
    db_session.add(tienda)
    db_session.flush()
    producto = Producto(nombre='Producto comentado', precio=10, categoria=Categoria.HOGAR_BRICOLAJE,
                        tienda_id=tienda.id)
    db_session.add(producto)
    db_session.commit()
    comprador = user_factory(email='comentador@example.com')
    headers = login(client, comprador)

    for tipo, identificador, pagina in [('productos', producto.id, f'/productos/{producto.id}'),
                                       ('tiendas', tienda.id, f'/tiendas/{tienda.id}')]:
        url = f'/api/comentarios/{tipo}/{identificador}'
        assert 'Todavía no hay comentarios.' in client.get(pagina).text
        assert client.put(url, json={'texto': '   '}, headers=headers).status_code == 422
        assert client.put(url, json={'texto': 'x' * 1001}, headers=headers).status_code == 422
        assert client.put(url, json={'texto': '  <script>alert(1)</script>  '}, headers=headers).status_code == 200
        html = client.get(pagina).text
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
        assert '<script>alert(1)</script>' not in html
        assert 'Editar tu comentario' in html
        assert client.put(url, json={'texto': 'Muy bueno'}, headers=headers).status_code == 200
        assert 'Muy bueno' in client.get(pagina).text

    assert db_session.query(ComentarioProducto).count() == 1
    assert db_session.query(ComentarioTienda).count() == 1
    assert producto.valoracion_media is None and tienda.valoracion_media is None
    assert client.delete(f'/api/comentarios/productos/{producto.id}', headers=headers).status_code == 200
    assert db_session.query(ComentarioProducto).count() == 0
    assert 'Todavía no hay comentarios.' in client.get(f'/productos/{producto.id}').text
    assert db_session.query(ComentarioTienda).count() == 1
    assert eliminar_usuario(db_session, comprador.id)
    assert db_session.query(ComentarioTienda).count() == 0


def test_comentarios_permisos_y_lectura_publica(client, db_session, user_factory):
    vendedor = user_factory(rol=RolUsuario.VENDEDOR)
    tienda = Tienda(nombre='Tienda pública', vendedor_id=vendedor.id)
    db_session.add(tienda)
    db_session.commit()
    url = f'/api/comentarios/tiendas/{tienda.id}'
    assert client.put(url, json={'texto': 'Bien'}).status_code == 401
    headers = login(client, vendedor)
    assert client.put(url, json={'texto': 'Bien'}, headers=headers).status_code == 403
    comprador = user_factory(email='lector@example.com')
    headers = login(client, comprador)
    assert client.put(url, json={'texto': 'Bien'}).status_code == 403
    assert client.put('/api/comentarios/tiendas/99999', json={'texto': 'Bien'}, headers=headers).status_code == 404
    assert client.put(url, json={'texto': 'Bien'}, headers=headers).status_code == 200
    assert client.post('/api/logout', headers=headers).status_code == 200
    pagina = client.get(f'/tiendas/{tienda.id}').text
    assert 'Bien' in pagina
    assert 'class="comment-form"' not in pagina


def test_admin_puede_editar_y_borrar_comentarios_ajenos(client, db_session, user_factory):
    vendedor = user_factory(rol=RolUsuario.VENDEDOR)
    tienda = Tienda(nombre='Tienda moderada', vendedor_id=vendedor.id)
    db_session.add(tienda)
    db_session.flush()
    producto = Producto(nombre='Producto moderado', precio=10, categoria=Categoria.HOGAR_BRICOLAJE,
                        tienda_id=tienda.id)
    db_session.add(producto)
    db_session.commit()
    comprador = user_factory(email='autor@example.com')
    admin = user_factory(email='admin-comentarios@example.com', rol=RolUsuario.ADMIN)
    headers = login(client, comprador)
    for tipo, entidad_id in [('productos', producto.id), ('tiendas', tienda.id)]:
        assert client.put(f'/api/comentarios/{tipo}/{entidad_id}',
                          json={'texto': 'Comentario original'}, headers=headers).status_code == 200
    admin_producto = f'/api/admin/comentarios/productos/{producto.id}/{comprador.id}'
    admin_tienda = f'/api/admin/comentarios/tiendas/{tienda.id}/{comprador.id}'
    assert client.put(admin_producto, json={'texto': 'Manipulado'}, headers=headers).status_code == 403
    assert client.delete(admin_tienda, headers=headers).status_code == 403
    assert 'admin-comment-form' not in client.get(f'/productos/{producto.id}').text

    headers = login(client, admin)
    for pagina in (f'/productos/{producto.id}', f'/tiendas/{tienda.id}'):
        assert 'class="admin-comment-form"' in client.get(pagina).text
    assert client.put(admin_producto, json={'texto': 'Cambio sin token'}).status_code == 403
    assert client.put(admin_producto, json={'texto': '   '}, headers=headers).status_code == 422
    assert client.put('/api/admin/comentarios/productos/99999/99999',
                      json={'texto': 'Nada'}, headers=headers).status_code == 404
    assert client.put(admin_producto, json={'texto': 'Editado por administración'}, headers=headers).status_code == 200
    assert 'Editado por administración' in client.get(f'/productos/{producto.id}').text
    assert db_session.query(ComentarioProducto).one().usuario_id == comprador.id
    assert client.delete(admin_tienda, headers=headers).status_code == 200
    assert db_session.query(ComentarioTienda).count() == 0
    assert 'Todavía no hay comentarios.' in client.get(f'/tiendas/{tienda.id}').text
