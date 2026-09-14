import json
import re
from decimal import Decimal

import pytest
from app.models import Categoria, EstadoPedido, Pedido, Producto, RolUsuario, Tienda
from app.routers import compra

pytestmark = pytest.mark.usefixtures('stripe_gateway')


@pytest.fixture
def product(db_session, user_factory):
    seller = user_factory(email="seller@example.com", rol=RolUsuario.VENDEDOR)
    shop = Tienda(nombre="Tienda", vendedor_id=seller.id)
    db_session.add(shop)
    db_session.flush()
    product = Producto(nombre="Taza", tienda_id=shop.id, precio=20, precio_oferta=15,
                       categoria=Categoria.HOGAR_BRICOLAJE, stock=5, disponible=True)
    db_session.add(product)
    db_session.commit()
    return product


def start(client, product):
    response = client.get(f"/compra/{product.id}?cantidad=2")
    assert response.status_code == 200
    token = re.search(r'data-token="([^"]+)"', response.text)[1]
    address = dict(direccion="Calle Sol 1", ciudad="Madrid", codigo_postal="28001")
    return dict(token=token, nombre="Ana", apellidos="Pérez", email="ana@example.com",
                telefono="600123123", envio=address, facturacion=address, metodo="inmediato")


def submit(client, payload, csrf=True):
    return client.post("/api/compra", json=payload,
                       headers={"X-CSRF-Token": client.cookies.get("csrf_token")} if csrf else {})


@pytest.mark.parametrize("method", ["inmediato", "contrarrembolso"])
def test_guest_purchase_persisted_before_payment_and_idempotent(client, db_session, product, monkeypatch, method):
    client.get("/carrito")
    client.post(f"/api/carrito/productos/{product.id}", json={"cantidad": 1},
                headers={"X-CSRF-Token": client.cookies.get("csrf_token")})
    before = client.get("/api/carrito").json()
    payload = start(client, product)
    payload["metodo"] = method
    calls = []
    def payment(db, order):
        persisted = db_session.query(Pedido).filter_by(id=order.id).one()
        assert persisted.estado == EstadoPedido.PENDIENTE
        assert not persisted.pago_completado
        assert len(persisted.items) == 1
        calls.append(order.id)
        return 'https://checkout.stripe.com/c/pay/test'
    from app import stripe_payments
    monkeypatch.setattr(stripe_payments, "abrir_pago", payment)
    response = submit(client, payload)
    assert response.status_code == 200
    assert response.json()["total"] == "36.30"
    assert response.json()["moneda"] == "EUR"
    order = db_session.query(Pedido).one()
    assert order.usuario_id is None
    assert order.subtotal == Decimal("40.00")
    assert order.descuento == Decimal("10.00")
    assert order.impuesto == Decimal("6.30")
    assert order.items[0].precio_unitario == Decimal("15.00")
    assert order.items[0].total == Decimal("30.00")
    assert order.email_comprador == payload["email"]
    assert json.loads(order.direccion_envio) == payload["envio"]
    assert not order.pago_completado
    assert order.estado == (EstadoPedido.PENDIENTE if method == "inmediato" else EstadoPedido.CONFIRMADO)
    assert submit(client, payload).json() == response.json()
    assert db_session.query(Pedido).count() == 1
    db_session.refresh(product)
    assert product.stock == 3
    assert len(calls) == (2 if method == "inmediato" else 0)
    after = client.get("/api/carrito").json()
    assert after["cantidad"] == before["cantidad"]
    assert after["total"] == before["total"]
    assert [(item["producto"]["id"], item["cantidad"]) for item in after["items"]] == [
        (item["producto"]["id"], item["cantidad"]) for item in before["items"]]


def test_registered_defaults_and_order_owner(client, db_session, product, user_factory):
    buyer = user_factory(email="buyer@example.com", ciudad="Sevilla")
    buyer.direccion = "Calle Luna 5"
    buyer.codigo_postal = "41001"
    buyer.telefono = "600111222"
    db_session.commit()
    client.post("/api/login", json={"email": buyer.email, "contrasena": "clave12345"})
    page = client.get(f"/compra/{product.id}")
    for value in (buyer.email, buyer.direccion, buyer.ciudad, buyer.codigo_postal, buyer.telefono):
        assert f'value="{value}"' in page.text
    assert submit(client, start(client, product)).status_code == 200
    assert db_session.query(Pedido).one().usuario_id == buyer.id


@pytest.mark.parametrize("change", ["stock", "price", "unavailable"])
def test_changed_product_rejected(client, db_session, product, change):
    payload = start(client, product)
    if change == "stock": product.stock = 1
    elif change == "price": product.precio_oferta = 16
    else: product.disponible = False
    db_session.commit()
    assert submit(client, payload).status_code == 409
    assert db_session.query(Pedido).count() == 0


def test_csrf_and_invalid_contact_rejected(client, db_session, product):
    payload = start(client, product)
    assert submit(client, payload, csrf=False).status_code == 403
    payload["envio"]["ciudad"] = "   "
    assert submit(client, payload).status_code == 422
    assert db_session.query(Pedido).count() == 0


def test_free_offer_and_rounding(product, monkeypatch):
    monkeypatch.setenv("CHECKOUT_IVA", "0.21")
    monkeypatch.setenv("CHECKOUT_ENVIO", "0")
    product.precio_oferta = 0
    assert compra.importes(product, 2)["total"] == Decimal("0.00")
    product.precio = 0.10
    product.precio_oferta = None
    assert compra.importes(product, 3)["total"] == Decimal("0.36")


@pytest.mark.parametrize("quantity", [0, -1, 1000, "1.5"])
def test_invalid_quantity(client, product, quantity):
    assert client.get(f"/compra/{product.id}?cantidad={quantity}").status_code == 422


@pytest.mark.parametrize('registered', [False, True])
def test_cart_checkout_selected_quantities(client, db_session, product, user_factory, monkeypatch, registered):
    monkeypatch.setenv('CHECKOUT_ENVIO', '5')
    if registered:
        buyer = user_factory(email='cartbuyer@example.com')
        client.post('/api/login', json={'email': buyer.email, 'contrasena': 'clave12345'})
    second = Producto(nombre='Plato', tienda_id=product.tienda_id, precio=10,
                      categoria=Categoria.HOGAR_BRICOLAJE, stock=8, disponible=True)
    db_session.add(second)
    db_session.commit()
    client.get('/carrito')
    headers = {'X-CSRF-Token': client.cookies.get('csrf_token')}
    for item in (product, second):
        assert client.post(f'/api/carrito/productos/{item.id}', json={'cantidad': 1}, headers=headers).status_code == 200
    assert 'data-buy-cart' in client.get('/carrito').text
    selection = {str(product.id): 2, str(second.id): 3}
    assert client.post('/api/compra/carrito', json={'cantidades': selection}, headers=headers).status_code == 409
    for product_id, quantity in selection.items():
        assert client.put(f'/api/carrito/productos/{product_id}', json={'cantidad': quantity}, headers=headers).status_code == 200
    response = client.post('/api/compra/carrito', json={'cantidades': selection}, headers=headers)
    assert response.status_code == 200
    page = client.get(response.json()['url'])
    assert page.status_code == 200
    assert 'Taza' in page.text and 'Plato' in page.text
    token = re.search(r'data-token="([^"]+)"', page.text)[1]
    address = dict(direccion='Calle Sol 1', ciudad='Madrid', codigo_postal='28001')
    payload = dict(token=token, nombre='Ana', apellidos='Perez', email='ana@example.com',
                   telefono='600123123', envio=address, facturacion=address, metodo='inmediato')
    response = submit(client, payload)
    assert response.status_code == 200
    assert response.json()['total'] == '77.60'
    order = db_session.query(Pedido).one()
    assert order.coste_entrega == Decimal('5.00')
    assert {str(item.producto_id): item.cantidad for item in order.items} == selection
    assert submit(client, payload).json() == response.json()
    assert db_session.query(Pedido).count() == 1


def test_cart_checkout_empty_and_invalid_selection(client, product):
    assert 'data-buy-cart' not in client.get('/carrito').text
    assert client.get('/compra/carrito').status_code == 409
    headers = {'X-CSRF-Token': client.cookies.get('csrf_token')}
    assert client.post('/api/compra/carrito', json={'cantidades': {str(product.id): 1}}, headers=headers).status_code == 409
    client.post(f'/api/carrito/productos/{product.id}', json={'cantidad': 1}, headers=headers)
    assert client.post('/api/compra/carrito', json={'cantidades': {str(product.id): 6}}, headers=headers).status_code == 409
    assert client.post('/api/compra/carrito', json={'cantidades': {str(product.id): 1.5}}, headers=headers).status_code == 422
    assert client.post('/api/compra/carrito', json={'cantidades': {str(product.id): 1}}).status_code == 403
