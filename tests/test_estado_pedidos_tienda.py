from decimal import Decimal

from app.estado_pedidos import cancelar_subpedido, recalcular_estado
from app.models import Categoria, EstadoPedido, EstadoSubpedido, MetodoPago, Pedido, Producto, ProductoPedido, RolUsuario, Subpedido, Tienda


def test_estado_publico_es_enviado_solo_si_todos_recogidos():
    pedido = Pedido(estado=EstadoPedido.PREPARACION)
    pedido.subpedidos = [Subpedido(tienda_id=1, estado=EstadoSubpedido.PREPARACION),
                        Subpedido(tienda_id=2, estado=EstadoSubpedido.LISTO_PARA_RECOGER)]
    pedido.subpedidos[0].estado = EstadoSubpedido.RECOGIDO
    assert recalcular_estado(pedido) == EstadoPedido.PREPARACION
    pedido.subpedidos[1].estado = EstadoSubpedido.RECOGIDO
    assert recalcular_estado(pedido) == EstadoPedido.ENVIADO
    pedido.estado = EstadoPedido.ENTREGADO
    assert recalcular_estado(pedido) == EstadoPedido.ENTREGADO


def test_cancelar_subpedido_conserva_linea_y_recalcula_importes(db_session, monkeypatch):
    pedido = Pedido(estado=EstadoPedido.PREPARACION, subtotal=Decimal('30.00'),
                    descuento=Decimal('0'), impuesto=Decimal('6.30'),
                    coste_entrega=Decimal('3.00'), total=Decimal('39.30'), pago_completado=False)
    sub1 = Subpedido(tienda_id=1, estado=EstadoSubpedido.PREPARACION)
    sub2 = Subpedido(tienda_id=2, estado=EstadoSubpedido.RECOGIDO)
    linea1 = ProductoPedido(producto_id=1, cantidad=1, precio_unitario=Decimal('10'), total=Decimal('10'))
    linea2 = ProductoPedido(producto_id=2, cantidad=1, precio_unitario=Decimal('20'), total=Decimal('20'))
    pedido.subpedidos = [sub1, sub2]
    pedido.items = [linea1, linea2]
    sub1.items = [linea1]
    sub2.items = [linea2]
    monkeypatch.setattr(db_session, 'execute', lambda *_args, **_kwargs: None)
    cancelar_subpedido(db_session, pedido, sub1)
    assert linea1.cancelado and not linea2.cancelado
    assert sub1.estado == EstadoSubpedido.CANCELADO
    assert pedido.subtotal == Decimal('20.00')
    assert pedido.impuesto == Decimal('4.20')
    assert pedido.total == Decimal('27.20')
    assert pedido.estado == EstadoPedido.ENVIADO


def test_vendedor_cancela_solo_su_subpedido(client, db_session, user_factory):
    vendedor1 = user_factory(email='vendedor1@example.com', rol=RolUsuario.VENDEDOR)
    vendedor2 = user_factory(email='vendedor2@example.com', rol=RolUsuario.VENDEDOR)
    admin = user_factory(email='admin-reparto@example.com', rol=RolUsuario.ADMIN)
    tienda1 = Tienda(nombre='Tienda uno', vendedor_id=vendedor1.id)
    tienda2 = Tienda(nombre='Tienda dos', vendedor_id=vendedor2.id)
    db_session.add_all([tienda1, tienda2]); db_session.flush()
    producto1 = Producto(nombre='Uno', precio=10, stock=2, categoria=Categoria.HOGAR_BRICOLAJE, tienda_id=tienda1.id)
    producto2 = Producto(nombre='Dos', precio=20, stock=2, categoria=Categoria.HOGAR_BRICOLAJE, tienda_id=tienda2.id)
    db_session.add_all([producto1, producto2]); db_session.flush()
    pedido = Pedido(codigo_pedido='MULTI-1', subtotal=Decimal('30'), descuento=Decimal('0'),
                    impuesto=Decimal('6.30'), coste_entrega=Decimal('3'), total=Decimal('39.30'),
                    nombre_comprador='María', apellidos_comprador='López García',
                    metodo_pago=MetodoPago.EFECTIVO, direccion_envio='Calle 1', direccion_facturacion='Calle 1')
    sub1 = Subpedido(tienda_id=tienda1.id, estado=EstadoSubpedido.PREPARACION)
    sub2 = Subpedido(tienda_id=tienda2.id, estado=EstadoSubpedido.RECOGIDO)
    pedido.subpedidos = [sub1, sub2]
    pedido.items = [ProductoPedido(producto=producto1, subpedido=sub1, cantidad=1, precio_unitario=10, total=10),
                    ProductoPedido(producto=producto2, subpedido=sub2, cantidad=1, precio_unitario=20, total=20)]
    db_session.add(pedido); db_session.commit()

    assert client.post('/api/login', json={'email': vendedor1.email, 'contrasena': 'clave12345'}).status_code == 200
    client.get(f'/gestion/tiendas/{tienda1.id}/pedidos')
    assert 'MULTI-1' in client.get(f'/gestion/tiendas/{tienda1.id}/pedidos', params={'comprador': 'maría lópez'}).text
    assert 'MULTI-1' not in client.get(f'/gestion/tiendas/{tienda1.id}/pedidos', params={'comprador': 'otra persona'}).text
    token = client.cookies.get('csrf_token')
    response = client.post(f'/gestion/tiendas/{tienda1.id}/pedidos/{pedido.id}/cancelar',
                           data={'csrf_token': token}, follow_redirects=False)
    assert response.status_code == 303
    db_session.refresh(pedido)
    assert pedido.estado == EstadoPedido.ENVIADO
    assert pedido.total == Decimal('27.20')
    assert sub1.estado == EstadoSubpedido.CANCELADO
    assert sub2.estado == EstadoSubpedido.RECOGIDO
    assert pedido.items[0].cancelado and not pedido.items[1].cancelado
    db_session.refresh(producto1); db_session.refresh(producto2)
    assert producto1.stock == 3 and producto2.stock == 2
    assert client.post(f'/gestion/tiendas/{tienda1.id}/pedidos/{pedido.id}/cancelar',
                       data={'csrf_token': token}, follow_redirects=False).status_code == 409
    assert client.post('/api/login', json={'email': admin.email, 'contrasena': 'clave12345'}).status_code == 200
    client.get('/admin/pedidos/panel')
    delivered = client.post(f'/admin/pedidos/{pedido.id}/entregar',
                            headers={'X-CSRF-Token': client.cookies.get('csrf_token')})
    assert delivered.status_code == 200
    assert delivered.json()['estado'] == 'entregado'
