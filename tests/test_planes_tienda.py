from datetime import datetime, timedelta

from app.models import Categoria, PagoPlan, Producto, RolUsuario, Tienda


STORE = {"nombre": "Tienda del vendedor", "direccion": "Calle Uno", "horario": "9-18",
         "latitud": 37.4, "longitud": -5.9}


def login(client, user):
    response = client.post("/api/login", json={"email": user.email, "contrasena": "clave12345"})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def test_freemium_no_se_puede_comprar_y_el_filtro_alcanza_tiendas_y_productos(client, db_session, user_factory):
    vendedor_fisico = user_factory(email="fisico@example.com", rol=RolUsuario.VENDEDOR)
    vendedor_online = user_factory(email="online@example.com", rol=RolUsuario.VENDEDOR)
    fisica = Tienda(nombre="Tienda física", vendedor_id=vendedor_fisico.id, plan="Freemium",
                    direccion="Calle Mayor 1", horario="Lunes a viernes 9-18")
    online = Tienda(nombre="Tienda online", vendedor_id=vendedor_online.id, plan="Premium")
    db_session.add_all([fisica, online])
    db_session.flush()
    db_session.add_all([
        Producto(nombre="Producto físico", tienda_id=fisica.id, precio=10, stock=3,
                 disponible=True, categoria=Categoria.HOGAR_BRICOLAJE),
        Producto(nombre="Producto online", tienda_id=online.id, precio=10, stock=3,
                 disponible=True, categoria=Categoria.HOGAR_BRICOLAJE),
    ])
    db_session.commit()

    todos = client.get("/api/productos").json()
    assert todos["total"] == 2
    filtrados = client.get("/api/productos", params={"tipo_catalogo": "online"}).json()
    assert filtrados["total"] == 1
    assert filtrados["productos"][0]["nombre"] == "Producto online"
    assert [t["nombre"] for t in filtrados["tiendas"]] == ["Tienda online"]
    assert [t["nombre"] for t in client.get("/api/tiendas", params={"tipo_catalogo": "online"}).json()] == ["Tienda online"]
    producto_fisico = next(p for p in todos["productos"] if p["nombre"] == "Producto físico")
    ficha = client.get(f"/productos/{producto_fisico['id']}")
    assert "solo un cat&aacute;logo visual" in ficha.text
    assert "Calle Mayor 1" in ficha.text
    assert "Lunes a viernes 9-18" in ficha.text
    assert f'data-add-cart="{producto_fisico["id"]}"' not in ficha.text
    client.get("/inicio")
    token = client.cookies.get("csrf_token")
    bloqueo = client.post(f"/api/carrito/productos/{producto_fisico['id']}",
                          json={"cantidad": 1}, headers={"X-CSRF-Token": token})
    assert bloqueo.status_code == 409
    from fastapi import HTTPException
    from app.routers.compra import preparar_items
    try:
        preparar_items(db_session, {str(producto_fisico["id"]): 1})
    except HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("Una compra directa de Freemium debe quedar bloqueada")


def test_vendedor_paga_1499_y_activa_premium_un_mes(client, db_session, user_factory, stripe_gateway):
    vendedor = user_factory(email="planes@example.com", rol=RolUsuario.VENDEDOR)
    headers = login(client, vendedor)
    creada = client.post("/api/gestion/tiendas", json=STORE, headers=headers)
    assert creada.status_code == 201
    tienda_id = creada.json()["id"]
    tienda = db_session.get(Tienda, tienda_id)
    assert tienda.plan_efectivo == "Freemium"

    pagina = client.get("/gestion/plan")
    assert pagina.status_code == 200
    assert "14,99" in pagina.text
    assert "Pagar 14,99" in pagina.text

    pago = client.post("/api/gestion/plan/pagar", headers=headers)
    assert pago.status_code == 200
    assert pago.json()["url"].startswith("https://checkout.stripe.com/")
    assert len(stripe_gateway.creations) == 1
    sesion_creada = stripe_gateway.creations[0]
    assert sesion_creada["mode"] == "payment"
    assert sesion_creada["line_items"][0]["price_data"]["unit_amount"] == 1499
    intento = db_session.query(PagoPlan).filter_by(tienda_id=tienda_id).one()

    sesion = stripe_gateway.sessions["plan-" + str(intento.id)]
    sesion.update(status="complete", payment_status="paid")
    resultado = client.get("/gestion/plan/resultado")
    assert resultado.status_code == 200
    assert "Pago confirmado" in resultado.text
    db_session.expire_all()
    tienda = db_session.get(Tienda, tienda_id)
    assert tienda.plan_efectivo == "Premium"
    assert datetime.utcnow() + timedelta(days=27) < tienda.fecha_renovacion_plan < datetime.utcnow() + timedelta(days=32)
    assert db_session.get(PagoPlan, intento.id).estado == "pagado"
    assert client.post("/api/gestion/plan/pagar", headers=headers).status_code == 409


def test_vendedor_no_puede_activarse_premium_sin_pago(client, db_session, user_factory):
    vendedor = user_factory(email="sinpago@example.com", rol=RolUsuario.VENDEDOR)
    headers = login(client, vendedor)
    tienda_id = client.post("/api/gestion/tiendas", json={**STORE, "plan": "Premium",
        "suscripcion_activa": True, "pasarela_activa": True}, headers=headers).json()["id"]
    tienda = db_session.get(Tienda, tienda_id)
    assert tienda.plan_efectivo == "Freemium"
    editada = client.put(f"/api/gestion/tiendas/{tienda_id}", json={**STORE, "plan": "Premium",
        "suscripcion_activa": True, "pasarela_activa": True}, headers=headers)
    assert editada.status_code == 200
    db_session.expire_all()
    assert db_session.get(Tienda, tienda_id).plan_efectivo == "Freemium"
