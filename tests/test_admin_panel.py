import pytest
from app.models import Categoria, RolUsuario, Pedido, ProductoPedido, MetodoPago, Producto


def login(client, user):
    assert client.post('/api/login', json={'email': user.email, 'contrasena': 'clave12345'}).status_code == 200
    return {'X-CSRF-Token': client.cookies.get('csrf_token')}


@pytest.fixture
def admin_data(client, user_factory):
    seller = user_factory(email='panelseller@example.com', rol=RolUsuario.VENDEDOR)
    buyer = user_factory(email='panelbuyer@example.com')
    admin = user_factory(email='paneladmin@example.com', rol=RolUsuario.ADMIN)
    h = login(client, admin)
    shop = client.post('/api/gestion/tiendas', json={'nombre': 'Tienda panel', 'direccion': 'Carmona', 'latitud': 37.47, 'longitud': -5.64, 'vendedor_id': seller.id}, headers=h).json()
    product = client.post(f'/api/gestion/tiendas/{shop["id"]}/productos', json={'nombre': 'Producto panel', 'precio': 20, 'precio_oferta': 15, 'stock': 8, 'categoria': Categoria.HOGAR_BRICOLAJE.value}, headers=h).json()
    return admin, seller, buyer, shop, product, h


def test_admin_navigation_and_account_filters(client, admin_data):
    admin, seller, buyer, shop, product, h = admin_data
    for path in ('/admin/tiendas', '/admin/usuarios/panel', '/admin/pedidos/panel', f'/gestion/tiendas/{shop["id"]}/productos', f'/gestion/tiendas/{shop["id"]}/editar'):
        page = client.get(path)
        assert page.status_code == 200
        assert 'aria-label="Panel de administración"' in page.text
        assert 'href="/admin/tiendas"' in page.text
        assert 'href="/admin/usuarios/panel"' in page.text
        assert 'management-subtabs' not in page.text
    accounts_page = client.get('/admin/usuarios/panel').text
    assert '<dialog id="accountEditor" aria-labelledby="formTitle">' in accounts_page
    assert accounts_page.index('<dialog id="accountEditor"') < accounts_page.index('<form id="adminForm"') < accounts_page.index('</dialog>')
    products_page = client.get(f'/gestion/tiendas/{shop["id"]}/productos').text
    assert 'product-grid management-product-grid' in products_page
    assert 'class="product-card"' in products_page
    assert 'data-add-cart=' not in products_page
    assert 'data-edit-product=' in products_page
    assert 'data-stock-product=' in products_page
    assert f'href="/tiendas/{shop["id"]}"' not in products_page
    accounts = client.get('/admin/usuarios/', params={'q': buyer.email, 'rol': 'comprador'}).json()
    assert [u['id'] for u in accounts] == [buyer.id]
    assert 'contrasena_hash' not in str(accounts)
    assert client.get('/admin/usuarios/', params={'skip': -1}).status_code == 422
    assert 'data-delete-store' in client.get('/admin/tiendas').text


def payload(buyer, product, code='ADMIN-001'):
    return {'codigo_pedido': code, 'usuario_id': buyer.id, 'estado': 'pendiente', 'metodo_pago': 'efectivo',
            'direccion_envio': 'Carmona', 'direccion_facturacion': 'Carmona', 'impuesto': 2, 'coste_entrega': 3,
            'lineas': [{'producto_id': product['id'], 'cantidad': 2}]}


def test_save_multiple_stocks_atomically(client, admin_data, db_session):
    admin, seller, buyer, shop, product, h = admin_data
    second = client.post(f'/api/gestion/tiendas/{shop["id"]}/productos', json={
        'nombre': 'Segundo producto', 'precio': 10, 'stock': 4, 'categoria': Categoria.HOGAR_BRICOLAJE.value}, headers=h).json()
    url = f'/api/gestion/tiendas/{shop["id"]}/stock'
    changes = {'productos': [{'producto_id': product['id'], 'stock': 12}, {'producto_id': second['id'], 'stock': 0}]}
    assert client.patch(url, json=changes).status_code == 403
    assert client.patch(url, json={'productos': [changes['productos'][0], {'producto_id': 99999, 'stock': 2}]}, headers=h).status_code == 404
    db_session.expire_all()
    assert db_session.get(Producto, product['id']).stock == 8
    assert client.patch(url, json=changes, headers=h).status_code == 200
    db_session.expire_all()
    assert db_session.get(Producto, product['id']).stock == 12
    assert db_session.get(Producto, second['id']).stock == 0
    headers = login(client, buyer)
    assert client.patch(url, json=changes, headers=headers).status_code == 403


def test_image_upload_permissions_size_and_generated_path(client, admin_data, monkeypatch, tmp_path):
    from app.routers import gestion
    import base64
    monkeypatch.setattr(gestion, 'IMAGE_DIRECTORY', tmp_path)
    admin, seller, buyer, shop, product, h = admin_data
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a7WQAAAAASUVORK5CYII=')
    files = {'archivo': ('../../photo.png', png, 'image/png')}
    assert client.post('/api/gestion/imagenes', files=files).status_code == 403
    response = client.post('/api/gestion/imagenes', files=files, headers=h)
    assert response.status_code == 201
    name = response.json()['imagen'].split('/')[-1]
    assert response.json()['imagen'].startswith('/static/uploads/')
    assert (tmp_path / name).read_bytes() == png
    assert client.post('/api/gestion/imagenes', files={'archivo': ('image.png', b'<svg/>', 'image/png')}, headers=h).status_code == 422
    assert client.post('/api/gestion/imagenes', files={'archivo': ('large.png', b'x' * (5 * 1024 * 1024 + 1), 'image/png')}, headers=h).status_code == 413
    headers = login(client, seller)
    assert client.post('/api/gestion/imagenes', files=files, headers=headers).status_code == 201
    headers = login(client, buyer)
    assert client.post('/api/gestion/imagenes', files=files, headers=headers).status_code == 403


def existing_order(db, buyer, product):
    order = Pedido(codigo_pedido='ADMIN-001', usuario_id=buyer.id, metodo_pago=MetodoPago.EFECTIVO,
                   direccion_envio='Carmona', direccion_facturacion='Carmona', subtotal=30, impuesto=2, coste_entrega=3, total=35,
                   items=[ProductoPedido(producto_id=product['id'], cantidad=2, precio_unitario=15, total=30)])
    db.add(order)
    db.commit()
    return order.id


def test_admin_order_crud_totals_snapshots_and_cascade(client, admin_data, db_session):
    admin, seller, buyer, shop, product, h = admin_data
    data = payload(buyer, product)
    assert client.post('/admin/pedidos/', json=data).status_code == 403
    assert db_session.query(Pedido).count() == 0
    assert 'nuevoPedido' not in client.get('/admin/pedidos/panel').text
    response = client.post('/admin/pedidos/', json=data, headers=h)
    assert response.status_code == 201
    order = response.json()
    assert client.post('/admin/pedidos/', json=data, headers=h).status_code == 409
    assert order['subtotal'] == 30 and order['total'] == 35
    assert order['lineas'][0]['precio_unitario'] == 15
    assert db_session.query(Pedido).count() == 1
    url = f'/admin/pedidos/{order["id"]}'
    edited = client.put(url, json={**data, 'estado': 'confirmado', 'lineas': [{'producto_id': product['id'], 'cantidad': 3, 'precio_unitario': 14}]}, headers=h)
    assert edited.status_code == 200
    assert edited.json()['estado'] == 'confirmado' and edited.json()['total'] == 47
    assert db_session.query(ProductoPedido).count() == 1
    assert client.get(url).json()['lineas'][0]['cantidad'] == 3
    listing = client.get('/admin/pedidos/', params={'q': 'ADMIN', 'estado': 'confirmado'}).json()
    assert listing['total'] == 1
    assert client.get('/admin/pedidos/', params={'estado': 'cancelado'}).json()['total'] == 0
    assert client.delete(url, headers=h).status_code == 204
    assert db_session.query(ProductoPedido).count() == 0
    assert client.get(url).status_code == 404


def test_order_validation_and_non_admin_permissions(client, admin_data, db_session):
    admin, seller, buyer, shop, product, h = admin_data
    data = payload(buyer, product)
    order_id = existing_order(db_session, buyer, product)
    for invalid in ({**data, 'lineas': []}, {**data, 'usuario_id': seller.id}, {**data, 'lineas': [{'producto_id': 99999, 'cantidad': 1}]},
                    {**data, 'lineas': [{'producto_id': product['id'], 'cantidad': 0}]}, {**data, 'impuesto': -1},
                    {**data, 'lineas': data['lineas'] * 2},
                    {**data, 'lineas': [{'producto_id': product['id'], 'cantidad': 1000000, 'precio_unitario': 1e308}]}):
        assert client.put(f'/admin/pedidos/{order_id}', json=invalid, headers=h).status_code == 422
    for user in (seller, buyer):
        headers = login(client, user)
        for path in ('/admin/tiendas', '/admin/usuarios/panel', '/admin/pedidos/panel', '/admin/pedidos/', '/admin/pedidos/999'):
            assert client.get(path).status_code == 403
        assert client.put(f'/admin/pedidos/{order_id}', json=data, headers=headers).status_code == 403
