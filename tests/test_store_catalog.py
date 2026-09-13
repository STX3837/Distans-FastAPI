from app.models import Categoria, Producto, RolUsuario, Tienda


def test_store_catalog_is_public_and_keeps_filters_and_pagination(client, db_session, user_factory):
    seller = user_factory(rol=RolUsuario.VENDEDOR)
    shop = Tienda(nombre="Tienda Uno", vendedor_id=seller.id)
    other = Tienda(nombre="Tienda Dos", vendedor_id=seller.id)
    db_session.add_all([shop, other])
    db_session.flush()
    for i in range(26):
        db_session.add(Producto(nombre=f"Producto propio {i}", precio=20, precio_oferta=15,
                               tienda_id=shop.id, categoria=Categoria.HOGAR_BRICOLAJE, stock=5, disponible=True))
    db_session.add(Producto(nombre="Producto ajeno", precio=10, tienda_id=other.id,
                           categoria=Categoria.HOGAR_BRICOLAJE, stock=5, disponible=True))
    db_session.commit()
    url = f"/tiendas/{shop.id}"
    page = client.get(url, params={"q": "Producto", "categoria": Categoria.HOGAR_BRICOLAJE.value})
    assert page.status_code == 200
    assert "Producto ajeno" not in page.text
    assert "26 productos" in page.text
    assert "25 % de descuento" in page.text
    assert f'action="{url}"' in page.text
    assert f'href="{url}?pagina=2' in page.text
    assert "categoria=" in page.text
    assert "data-add-cart=" in page.text
    second = client.get(url, params={"pagina": 2, "q": "Producto"})
    assert second.status_code == 200
    assert second.text.count('class="product-card"') == 2
    assert "Producto ajeno" not in second.text
    assert "No hay productos para mostrar" in client.get(url, params={"q": "ajeno"}).text
    assert f'href="{url}"' in client.get("/inicio").text


def test_empty_and_inactive_store_catalog(client, db_session, user_factory):
    seller = user_factory(rol=RolUsuario.VENDEDOR)
    shop = Tienda(nombre="Tienda vacía", vendedor_id=seller.id)
    db_session.add(shop)
    db_session.commit()
    assert client.get(f"/tiendas/{shop.id}").status_code == 200
    assert "No hay productos para mostrar" in client.get(f"/tiendas/{shop.id}").text
    seller.activo = False
    db_session.commit()
    assert client.get(f"/tiendas/{shop.id}").status_code == 404
    assert client.get("/tiendas/99999").status_code == 404
