import pytest
from app.models import Categoria, MetodoPago, Pedido, ProductoPedido, RolUsuario, Tienda, Producto


STORE = {"nombre": "Tienda pruebas", "direccion": "Carmona", "latitud": 37.47, "longitud": -5.64}
PRODUCT = {"nombre": "Taza pruebas", "precio": 20, "precio_oferta": 15, "stock": 6,
           "categoria": Categoria.HOGAR_BRICOLAJE.value}


def login(client, user):
    response = client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def test_seller_store_product_crud_and_pages(client, user_factory):
    seller = user_factory(rol=RolUsuario.VENDEDOR)
    h = login(client, seller)
    assert client.get("/login", follow_redirects=False).headers["location"] == "/mi-tienda"
    assert client.post("/api/gestion/tiendas", json=STORE).status_code == 403
    response = client.post("/api/gestion/tiendas", json=STORE, headers=h)
    assert response.status_code == 201
    store = response.json()
    assert store["latitud"] == STORE["latitud"]
    assert store["categorias"] == []
    base = f'/api/gestion/tiendas/{store["id"]}'
    response = client.post(base + "/productos", json=PRODUCT, headers=h)
    assert response.status_code == 201
    product = response.json()
    assert product["descuento"] == 25
    assert client.get(base).json()["categorias"] == [Categoria.HOGAR_BRICOLAJE.value]
    for path in ("/mi-tienda", "/gestion/tiendas/nueva", f'/gestion/tiendas/{store["id"]}', f'/gestion/tiendas/{store["id"]}/editar', f'/gestion/tiendas/{store["id"]}/productos'):
        page = client.get(path)
        assert page.status_code == 200
        assert "Mi tienda" in page.text
    response = client.put(f'/api/gestion/productos/{product["id"]}', json={**PRODUCT, "categoria": Categoria.CULTURA_OCIO.value, "stock": 2}, headers=h)
    assert response.status_code == 200
    assert response.json()["stock"] == 2
    assert client.get(base).json()["categorias"] == [Categoria.CULTURA_OCIO.value]
    assert client.get(base + "/productos").json()["total"] == 1
    assert client.put(base, json={**STORE, "nombre": "Tienda editada"}, headers=h).status_code == 200
    assert client.delete(f'/api/gestion/productos/{product["id"]}', headers=h).status_code == 200
    assert client.get(base).json()["categorias"] == []
    assert client.delete(base, headers=h).status_code == 200


def test_ownership_admin_and_buyer_permissions(client, user_factory):
    owner = user_factory(email="owner@example.com", rol=RolUsuario.VENDEDOR)
    h = login(client, owner)
    store = client.post("/api/gestion/tiendas", json=STORE, headers=h).json()
    base = f'/api/gestion/tiendas/{store["id"]}'
    product = client.post(base + "/productos", json=PRODUCT, headers=h).json()
    other = user_factory(email="other@example.com", rol=RolUsuario.VENDEDOR)
    h = login(client, other)
    assert client.get("/api/gestion/tiendas").json() == []
    assert client.get(base).status_code == 404
    assert client.put(base, json=STORE, headers=h).status_code == 404
    assert client.delete(f'/api/gestion/productos/{product["id"]}', headers=h).status_code == 404
    assert client.post("/api/gestion/tiendas", json={**STORE, "vendedor_id": owner.id}, headers=h).status_code == 403
    admin = user_factory(email="admin@example.com", rol=RolUsuario.ADMIN)
    h = login(client, admin)
    assert len(client.get("/api/gestion/tiendas").json()) == 1
    assert client.get(base).status_code == 200
    assert client.put(f'/api/gestion/productos/{product["id"]}', json={**PRODUCT, "stock": 10}, headers=h).status_code == 200
    assert client.put(base, json={**STORE, "vendedor_id": other.id}, headers=h).status_code == 200
    buyer = user_factory(email="buyer@example.com")
    h = login(client, buyer)
    assert client.get("/mi-tienda").status_code == 403
    assert client.post("/api/gestion/tiendas", json=STORE, headers=h).status_code == 403


def test_single_store_seller_flow_and_stock_editor(client, user_factory):
    seller = user_factory(rol=RolUsuario.VENDEDOR)
    h = login(client, seller)
    assert 'Registrar tienda' in client.get('/mi-tienda').text
    store = client.post('/api/gestion/tiendas', json=STORE, headers=h).json()
    assert client.post('/api/gestion/tiendas', json=STORE, headers=h).status_code == 409
    assert client.get('/gestion/tiendas/nueva', follow_redirects=False).headers['location'] == '/mi-tienda'
    page = client.get('/mi-tienda')
    assert page.text.count('class="store-card"') == 1
    assert 'Registrar tienda' not in page.text
    assert f'href="/gestion/tiendas/{store["id"]}/productos"' in page.text
    assert 'Editar tienda' in page.text
    product = client.post(f'/api/gestion/tiendas/{store["id"]}/productos', json=PRODUCT, headers=h).json()
    url = f'/api/gestion/productos/{product["id"]}/stock'
    assert client.patch(url, json={'stock': 12}).status_code == 403
    assert client.patch(url, json={'stock': -1}, headers=h).status_code == 422
    assert client.patch(url, json={'stock': 12}, headers=h).json()['stock'] == 12
    data = client.get(f'/api/gestion/productos/{product["id"]}').json()
    assert data['precio'] == PRODUCT['precio'] and data['categoria'] == PRODUCT['categoria']
    products_page = client.get(f'/gestion/tiendas/{store["id"]}/productos')
    assert 'id="createProduct"' in products_page.text and 'id="editStock"' in products_page.text
    other = user_factory(email='stockother@example.com', rol=RolUsuario.VENDEDOR)
    h = login(client, other)
    assert client.patch(url, json={'stock': 20}, headers=h).status_code == 404


def test_admin_cannot_assign_second_store_to_seller(client, user_factory):
    seller = user_factory(rol=RolUsuario.VENDEDOR)
    h = login(client, seller)
    client.post('/api/gestion/tiendas', json=STORE, headers=h)
    other = user_factory(email='secondowner@example.com', rol=RolUsuario.VENDEDOR)
    h = login(client, other)
    second = client.post('/api/gestion/tiendas', json=STORE, headers=h).json()
    admin = user_factory(email='singlestoreadmin@example.com', rol=RolUsuario.ADMIN)
    h = login(client, admin)
    assert client.post('/api/gestion/tiendas', json={**STORE, 'vendedor_id': seller.id}, headers=h).status_code == 409
    assert client.put(f'/api/gestion/tiendas/{second["id"]}', json={**STORE, 'vendedor_id': seller.id}, headers=h).status_code == 409


def test_seller_cannot_read_foreign_public_or_management_data(client, user_factory):
    owner = user_factory(email='privateowner@example.com', rol=RolUsuario.VENDEDOR)
    h = login(client, owner)
    shop = client.post('/api/gestion/tiendas', json=STORE, headers=h).json()
    product = client.post(f'/api/gestion/tiendas/{shop["id"]}/productos', json=PRODUCT, headers=h).json()
    other = user_factory(email='privateseller@example.com', rol=RolUsuario.VENDEDOR)
    h = login(client, other)
    assert client.get('/inicio', follow_redirects=False).headers['location'] == '/mi-tienda'
    data = client.get('/api/productos').json()
    assert data['productos'] == [] and data['tiendas'] == []
    for path in (f'/tiendas/{shop["id"]}', f'/productos/{product["id"]}', f'/api/productos/{product["id"]}',
                 f'/api/gestion/tiendas/{shop["id"]}', f'/api/gestion/tiendas/{shop["id"]}/productos',
                 f'/api/gestion/productos/{product["id"]}', f'/gestion/tiendas/{shop["id"]}',
                 f'/gestion/tiendas/{shop["id"]}/editar', f'/gestion/tiendas/{shop["id"]}/productos'):
        response = client.get(path)
        assert response.status_code == 404
        assert PRODUCT['nombre'] not in response.text and STORE['nombre'] not in response.text
    assert client.get('/admin/usuarios/panel').status_code == 403
    assert client.get('/carrito').status_code == 403
    h = login(client, owner)
    data = client.get('/api/productos').json()
    assert [p['id'] for p in data['productos']] == [product['id']]
    assert [s['id'] for s in data['tiendas']] == [shop['id']]
    assert client.get(f'/productos/{product["id"]}').status_code == 200


@pytest.mark.parametrize("patch", [{"precio_oferta": 20}, {"precio_oferta": -1}, {"stock": -1}, {"nombre": "   "}, {"imagen": "javascript:alert(1)"}])
def test_invalid_products_rejected(client, user_factory, patch):
    h = login(client, user_factory(rol=RolUsuario.VENDEDOR))
    store = client.post("/api/gestion/tiendas", json=STORE, headers=h).json()
    assert client.post(f'/api/gestion/tiendas/{store["id"]}/productos', json={**PRODUCT, **patch}, headers=h).status_code == 422


def test_dashboard_scopes_order_lines_and_preserves_history(client, db_session, user_factory):
    seller = user_factory(rol=RolUsuario.VENDEDOR)
    buyer = user_factory(email="buyer@example.com")
    h = login(client, seller)
    store = client.post("/api/gestion/tiendas", json=STORE, headers=h).json()
    product = client.post(f'/api/gestion/tiendas/{store["id"]}/productos', json=PRODUCT, headers=h).json()
    other_seller = user_factory(email="orderseller@example.com", rol=RolUsuario.VENDEDOR)
    other_store = Tienda(nombre="Otra tienda", vendedor_id=other_seller.id)
    db_session.add(other_store); db_session.flush()
    other_product = Producto(nombre="Linea ajena", precio=50, stock=5, categoria=Categoria.CULTURA_OCIO, tienda_id=other_store.id)
    db_session.add(other_product); db_session.flush()
    order = Pedido(codigo_pedido="PEDIDO-TEST", usuario_id=buyer.id, subtotal=65, total=65, metodo_pago=MetodoPago.EFECTIVO, direccion_envio="Carmona", direccion_facturacion="Carmona")
    db_session.add(order); db_session.flush()
    db_session.add_all([ProductoPedido(pedido_id=order.id, producto_id=product["id"], cantidad=1, precio_unitario=15, total=15), ProductoPedido(pedido_id=order.id, producto_id=other_product.id, cantidad=1, precio_unitario=50, total=50)])
    db_session.commit()
    page = client.get(f'/gestion/tiendas/{store["id"]}')
    assert "PEDIDO-TEST" in page.text and "15.00 €" in page.text
    assert "Linea ajena" not in page.text
    assert client.delete(f'/api/gestion/productos/{product["id"]}', headers=h).status_code == 409
    assert client.delete(f'/api/gestion/tiendas/{store["id"]}', headers=h).status_code == 409
