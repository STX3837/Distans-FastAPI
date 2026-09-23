import json

import pytest
from fastapi.testclient import TestClient
from app.models import Categoria, CoordenadasTienda, Producto, Tienda
from app.schemas import RolUsuario


@pytest.fixture
def catalog(db_session, user_factory):
    seller = user_factory(rol=RolUsuario.VENDEDOR)
    shop = Tienda(nombre="Taller Centro", direccion="Calle Sol 1", ubicacion="Madrid", vendedor_id=seller.id)
    db_session.add(shop); db_session.flush()
    db_session.add(CoordenadasTienda(tienda_id=shop.id, latitud=40.4, longitud=-3.7))
    featured = Producto(nombre="Taza artesanal", descripcion="Cerámica local", marca="Marca Centro", precio=20, precio_oferta=0,
                        tienda_id=shop.id, categoria=Categoria.HOGAR_BRICOLAJE, destacado=True, disponible=True, stock=5)
    regular = Producto(nombre="Ramo de flores", precio=30, tienda_id=shop.id, categoria=Categoria.FLORISTERIAS_JARDINERIA, destacado=False, disponible=True)
    hidden = Producto(nombre="Producto oculto", precio=10, tienda_id=shop.id, categoria=Categoria.HOGAR_BRICOLAJE, destacado=True, disponible=False)
    db_session.add_all([featured, regular, hidden]); db_session.commit()
    return seller, shop, featured, regular, hidden


def test_home_renders_all_products_without_login(client, catalog):
    response = client.get("/inicio")
    assert response.status_code == 200
    assert "Taza artesanal" in response.text
    assert "Ramo de flores" in response.text
    assert "Producto oculto" in response.text
    assert "No disponible" in response.text
    assert 'id="productsMap"' in response.text
    assert 'id="mapProducts"' in response.text
    assert "0.00 €" in response.text


@pytest.mark.parametrize("term,expected", [("taza", "Taza artesanal"), ("cerámica", "Taza artesanal"), ("Marca Centro", "Taza artesanal"), ("Taller Centro", "Taza artesanal"), ("Madrid", "Taza artesanal"), ("flores", "Ramo de flores")])
def test_search_matches_product_brand_and_shop(client, catalog, term, expected):
    response = client.get("/api/productos", params={"q": term})
    assert response.status_code == 200
    assert expected in [p["nombre"] for p in response.json()["productos"]]
    assert all("disponible" in p for p in response.json()["productos"])


def test_filter_category_and_featured(client, catalog):
    response = client.get("/api/productos", params={"categoria": Categoria.FLORISTERIAS_JARDINERIA.value})
    assert [p["nombre"] for p in response.json()["productos"]] == ["Ramo de flores"]
    response = client.get("/api/productos", params={"destacados": "true"})
    assert [p["nombre"] for p in response.json()["productos"]] == ["Producto oculto", "Taza artesanal"]
    assert client.get("/api/productos", params={"categoria": "inventada"}).status_code == 422
    assert client.get("/inicio", params={"q": "flores", "categoria": ""}).status_code == 200


def test_rf06_rf22_filters_and_validation(client, catalog, db_session, user_factory):
    _, shop, featured, regular, _ = catalog
    other_seller = user_factory(email="filters@example.com", rol=RolUsuario.VENDEDOR)
    other_shop = Tienda(nombre="Tienda secundaria", vendedor_id=other_seller.id, valoracion_media=3.0)
    shop.valoracion_media = 4.5
    featured.valoracion_media = 4.2
    featured.modalidad_compra = "online"
    regular.valoracion_media = 2.0
    db_session.add(other_shop)
    db_session.flush()
    db_session.add(Producto(nombre="Taza ajena", precio=8, tienda_id=other_shop.id,
                            categoria=Categoria.HOGAR_BRICOLAJE, valoracion_media=5.0,
                            modalidad_compra="online"))
    db_session.commit()

    params = {"tienda_id": shop.id, "categoria": Categoria.HOGAR_BRICOLAJE.value,
              "precio_min": 0, "precio_max": 0, "valoracion_min": 4,
              "modalidad": "online"}
    result = client.get("/api/productos", params=params).json()
    assert [item["id"] for item in result["productos"]] == [featured.id]
    assert result["total"] == 1
    assert client.get("/inicio", params=params).status_code == 200
    assert client.get("/api/productos", params={"precio_min": 1, "precio_max": 0}).status_code == 422
    assert client.get("/api/productos", params={"modalidad": "ambas"}).status_code == 422
    assert client.get("/api/productos", params={"valoracion_min": 0}).json()["total"] == 4
    empty_form = {"tienda_id": "", "precio_min": "", "precio_max": "", "modalidad": "",
                  "tienda_valoracion_min": "1.5"}
    empty_response = client.get("/inicio", params=empty_form)
    assert empty_response.status_code == 200, empty_response.text
    assert client.get("/api/productos", params=empty_form).status_code == 200
    assert client.get("/api/productos", params={"tienda_id": "abc"}).status_code == 422
    assert client.get("/api/productos", params={"precio_min": "abc"}).status_code == 422
    html = client.get("/inicio").text
    assert 'id="filterRating" name="valoracion_min" type="range"' in html
    assert 'id="filterStoreRating" name="tienda_valoracion_min" type="range"' in html
    assert '>Filtros</button>' in html
    assert 'data-filters-panel hidden' in html
    assert 'name="tienda_id"' not in html

    shops = client.get("/api/tiendas", params={"categoria": Categoria.HOGAR_BRICOLAJE.value,
                                              "valoracion_min": 4}).json()
    assert [item["id"] for item in shops] == [shop.id]
    assert [item["id"] for item in client.get("/api/productos", params={
        "categoria": Categoria.HOGAR_BRICOLAJE.value, "tienda_valoracion_min": 4}).json()["tiendas"]] == [shop.id]


def test_empty_search_browses_whole_catalog(client, catalog):
    response = client.get("/inicio", params={"q": "", "categoria": ""})
    assert response.status_code == 200
    assert "Ramo de flores" in response.text
    assert "Taza artesanal" in response.text


def test_store_tab_is_preserved_by_search_form(client, catalog):
    response = client.get('/inicio', params={'tab': 'tiendas', 'tienda_valoracion_min': '1.5'})
    assert response.status_code == 200
    assert 'data-default-tab="tiendas"' in response.text
    assert 'name="tab" value="tiendas" data-current-tab' in response.text
    assert 'href="/inicio?q=&amp;tab=tiendas"' in response.text


def test_search_wildcards_are_literal(client, catalog):
    assert client.get("/api/productos", params={"q": "%"}).json()["total"] == 0
    assert client.get("/api/productos", params={"q": "_"}).json()["total"] == 0


def test_public_results_contain_coordinates_without_user_credentials(client, catalog):
    seller, _, _, _, _ = catalog
    response = client.get("/api/productos")
    products = response.json()["productos"]
    assert len(products) == 3
    assert products[0]["tienda"]["latitud"] == 40.4
    assert products[0]["tienda"]["longitud"] == -3.7
    assert seller.email not in response.text
    assert seller.contrasena_hash not in response.text


def test_shops_without_coordinates_still_appear(client, catalog, db_session):
    _, shop, _, _, _ = catalog
    db_session.delete(shop.coordenadas); db_session.commit()
    response = client.get("/api/productos")
    assert response.json()["total"] == 3
    assert response.json()["productos"][0]["tienda"]["latitud"] is None
    assert "Ubicación de la tienda pendiente" in client.get("/inicio").text


def test_inactive_seller_products_not_public(client, catalog, db_session):
    seller, _, _, _, _ = catalog
    seller.activo = False; db_session.commit()
    assert client.get("/api/productos").json()["total"] == 0


def test_pagination_consistent_with_map_data(client, catalog, db_session):
    _, shop, _, _, _ = catalog
    for i in range(28):
        db_session.add(Producto(nombre=f"Producto {i}", precio=10, categoria=Categoria.HOGAR_BRICOLAJE, tienda_id=shop.id, disponible=True))
    db_session.commit()
    first = client.get("/api/productos").json()
    second = client.get("/api/productos", params={"pagina": 2}).json()
    assert first["total"] == 31 and first["paginas"] == 2
    assert len(first["productos"]) == 24 and len(second["productos"]) == 7
    assert not set(p["id"] for p in first["productos"]) & set(p["id"] for p in second["productos"])
    assert client.get("/api/productos", params={"pagina": 0}).status_code == 422
    page = client.get("/inicio")
    assert "pagina=2&amp;tab=productos" in page.text


def test_unsafe_images_and_names_are_escaped(client, catalog, db_session):
    _, _, featured, _, _ = catalog
    featured.nombre = '<script>alert("x")</script>'
    featured.imagen = 'javascript:alert(1)'
    db_session.commit()
    response = client.get("/inicio")
    assert '<script>alert("x")</script>' not in response.text
    assert 'javascript:alert(1)' not in response.text
    assert client.get(f"/api/productos/{featured.id}").json()["imagen"] is None


def test_coordinate_update_requires_owner_role_and_csrf(app, client, catalog, user_factory):
    seller, shop, _, _, _ = catalog
    payload = {"latitud": 41.0, "longitud": 2.0}
    url = f"/api/tiendas/{shop.id}/ubicacion"
    assert client.put(url, json=payload).status_code == 401
    client.post("/api/login", json={"email": seller.email, "contrasena": "clave12345"})
    assert client.put(url, json=payload).status_code == 403
    headers = {"X-CSRF-Token": client.cookies.get("csrf_token")}
    assert client.put(url, json=payload, headers=headers).status_code == 200
    assert client.get("/api/productos").json()["productos"][0]["tienda"]["latitud"] == 41.0
    other = user_factory(email="otro@example.com", rol=RolUsuario.VENDEDOR)
    client.post("/api/login", json={"email": other.email, "contrasena": "clave12345"})
    assert client.put(url, json=payload, headers={"X-CSRF-Token": client.cookies.get("csrf_token")}).status_code == 403
    assert client.put(url, json={"latitud": 91, "longitud": 0}).status_code == 422


def test_empty_catalog_has_visible_message_and_map(client):
    response = client.get("/inicio")
    assert response.status_code == 200
    assert "Todavía no hay productos publicados" in response.text
    assert 'id="productsMap"' in response.text
