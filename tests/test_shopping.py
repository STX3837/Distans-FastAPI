import pytest
from fastapi.testclient import TestClient
from app.models import Categoria, CoordenadasTienda, Producto, RolUsuario, Tienda, Carrito


@pytest.fixture
def product(db_session, user_factory):
    seller = user_factory(email="seller@example.com", rol=RolUsuario.VENDEDOR)
    shop = Tienda(nombre="Tienda Carmona", vendedor_id=seller.id, ubicacion="Carmona")
    db_session.add(shop)
    db_session.flush()
    db_session.add(CoordenadasTienda(tienda_id=shop.id, latitud=37.4712, longitud=-5.646))
    product = Producto(nombre="Producto Carmona", tienda_id=shop.id, precio=20, precio_oferta=15,
                       categoria=Categoria.HOGAR_BRICOLAJE, disponible=True, stock=5)
    db_session.add(product)
    db_session.commit()
    return product


def headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def test_buyer_header_on_shopping_pages_and_excluded_from_account_pages(client, product, user_factory):
    for path in ("/inicio", f"/productos/{product.id}", f"/tiendas/{product.tienda_id}", "/carrito"):
        response = client.get(path)
        assert response.status_code == 200
        assert 'class="market-header"' in response.text
        assert 'href="/inicio?tab=tiendas"' in response.text
        assert 'href="/inicio?q=&amp;tab=productos"' in response.text
    for path in ("/", "/login", "/registro", "/recuperar-contrasena"):
        assert 'class="market-header"' not in client.get(path).text
    buyer = user_factory(email="headerbuyer@example.com")
    client.post("/api/login", json={"email": buyer.email, "contrasena": "clave12345"})
    assert 'class="market-header"' in client.get(f"/productos/{product.id}").text
    assert 'class="market-header"' in client.get("/usuarios/cuenta").text


@pytest.mark.parametrize("role", [RolUsuario.VENDEDOR, RolUsuario.ADMIN])
def test_other_roles_do_not_use_buyer_header(client, product, user_factory, role):
    user = user_factory(email="headerrole@example.com", rol=role)
    client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"})
    for path in ("/inicio", f"/productos/{product.id}", f"/tiendas/{product.tienda_id}"):
        response = client.get(path)
        assert response.status_code == (404 if role == RolUsuario.VENDEDOR and path != "/inicio" else 200)
        assert 'class="market-header"' not in response.text


def test_header_navigation_opens_selected_home_tab(client):
    for tab in ("mapa", "productos", "tiendas"):
        assert f'data-default-tab="{tab}"' in client.get("/inicio", params={"tab": tab}).text


def test_public_detail_offer_and_unavailable(client, product, db_session):
    data = client.get(f"/api/productos/{product.id}").json()
    assert data["descuento"] == 25
    response = client.get(f"/productos/{product.id}")
    assert response.status_code == 200
    assert "25 % de descuento" in response.text
    assert "20.00 €" in response.text and "15.00 €" in response.text
    product.disponible = False
    db_session.commit()
    assert "No disponible" in client.get(f"/productos/{product.id}").text
    assert client.post(f"/api/carrito/productos/{product.id}", json={"cantidad": 1}, headers=headers(client)).status_code == 409
    assert client.get("/productos/99999").status_code == 404


def test_guest_cart_quantity_stock_csrf_and_isolation(client, app, product):
    client.get("/inicio")
    url = f"/api/carrito/productos/{product.id}"
    assert client.post(url, json={"cantidad": 1}).status_code == 403
    assert client.post(url, json={"cantidad": 0}, headers=headers(client)).status_code == 422
    added = client.post(url, json={"cantidad": 2}, headers=headers(client))
    assert added.status_code == 200 and added.json()["total"] == 30
    assert client.post(url, json={"cantidad": 4}, headers=headers(client)).status_code == 409
    assert client.get("/api/carrito").json()["cantidad"] == 2
    assert TestClient(app).get("/api/carrito").json()["cantidad"] == 0
    assert "25 % de descuento" in client.get("/carrito").text
    assert client.put(url, json={"cantidad": 3}, headers=headers(client)).json()["total"] == 45
    assert client.delete(url, headers=headers(client)).json()["cantidad"] == 0


def test_buyer_cart_persists_and_other_user_cannot_see_it(client, app, product, user_factory, db_session):
    buyer = user_factory(email="buyer@example.com")
    client.post("/api/login", json={"email": buyer.email, "contrasena": "clave12345"})
    url = f"/api/carrito/productos/{product.id}"
    assert client.post(url, json={"cantidad": 2}, headers=headers(client)).status_code == 200
    assert db_session.query(Carrito).filter_by(usuario_id=buyer.id).one().items[0].cantidad == 2
    fresh = TestClient(app)
    fresh.post("/api/login", json={"email": buyer.email, "contrasena": "clave12345"})
    assert fresh.get("/api/carrito").json()["cantidad"] == 2
    other = user_factory(email="other@example.com")
    fresh.post("/api/login", json={"email": other.email, "contrasena": "clave12345"})
    assert fresh.get("/api/carrito").json()["cantidad"] == 0


def test_seller_cannot_add_to_cart(client, product, db_session):
    seller = product.tienda.vendedor
    client.post("/api/login", json={"email": seller.email, "contrasena": "clave12345"})
    assert client.post(f"/api/carrito/productos/{product.id}", json={"cantidad": 1}, headers=headers(client)).status_code == 403


def test_radius_filters_before_pagination_and_returns_all_stores(client, product, db_session, user_factory):
    seller = user_factory(email="madridseller@example.com", rol=RolUsuario.VENDEDOR)
    far = Tienda(nombre="Tienda Madrid", vendedor_id=seller.id)
    db_session.add(far)
    db_session.flush()
    db_session.add(CoordenadasTienda(tienda_id=far.id, latitud=40.4, longitud=-3.7))
    for i in range(30):
        db_session.add(Producto(nombre=f"Lejano {i}", tienda_id=far.id, precio=10,
                               categoria=Categoria.HOGAR_BRICOLAJE, disponible=True, stock=2))
    db_session.commit()
    params = {"latitud": 37.4712, "longitud": -5.646, "radio": 2000}
    response = client.get("/api/productos", params=params)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["productos"][0]["id"] == product.id
    assert len(client.get("/api/productos").json()["tiendas"]) == 2
    page = client.get("/inicio", params=params)
    assert "Producto Carmona" in page.text and "Lejano" not in page.text
    assert client.get("/api/productos", params={"radio": 2000}).status_code == 422
    assert client.get("/api/productos", params={**params, "latitud": 91}).status_code == 422


@pytest.mark.parametrize("offer,discount", [(0, 100), (20, None), (25, None), (-1, None)])
def test_only_valid_offers_are_published(client, product, db_session, offer, discount):
    product.precio_oferta = offer
    db_session.commit()
    data = client.get(f"/api/productos/{product.id}").json()
    assert data["descuento"] == discount
    assert data["precio_oferta"] == (offer if discount is not None else None)


def test_shop_search_includes_shops_without_products(client, product, db_session, user_factory):
    seller = user_factory(email="emptyseller@example.com", rol=RolUsuario.VENDEDOR)
    shop = Tienda(nombre="Tienda vacía Carmona", vendedor_id=seller.id)
    db_session.add(shop)
    db_session.flush()
    db_session.add(CoordenadasTienda(tienda_id=shop.id, latitud=37.4712, longitud=-5.646))
    db_session.commit()
    data = client.get("/api/productos", params={"q": "vacía", "latitud": 37.4712, "longitud": -5.646, "radio": 2000}).json()
    assert data["total"] == 0
    assert [t["id"] for t in data["tiendas"]] == [shop.id]
