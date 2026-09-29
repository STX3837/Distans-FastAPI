"""Fixture demo comparable con DISTANS-Django. Solo desarrollo/pruebas."""
import argparse
import os
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import SessionLocal
from app.models import (
    Carrito, Categoria, ComentarioProducto, ComentarioTienda, CoordenadasTienda,
    EstadoPedido, EstadoSubpedido, MetodoPago, PagoPlan, Pedido, Producto,
    ProductoCarrito, ProductoFavorito, ProductoPedido, RestablecimientoContrasena,
    RolUsuario, Subpedido, Tienda, TiendaFavorita, Usuario, ValoracionProducto,
    ValoracionTienda, VisitaProducto, VisitaTienda,
)
from app.security import hash_password

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "DemoDistans2026!")
COMPARABLE_ACCOUNTS = (
    ("Admin", "Demostración", "admin@demo.example.com", RolUsuario.ADMIN, "Madrid", "28001"),
    ("Ana", "Demostración", "comprador@demo.example.com", RolUsuario.COMPRADOR, "Madrid", "28001"),
    ("Luis", "Demostración", "comprador2@demo.example.com", RolUsuario.COMPRADOR, "Madrid", "28001"),
    ("Librería Horizonte Demo", "Demostración", "libreria@demo.example.com", RolUsuario.VENDEDOR, "Madrid", "28001"),
    ("Tecnología Centro Demo", "Demostración", "tecnologia@demo.example.com", RolUsuario.VENDEDOR, "Madrid", "28001"),
    ("Jardín del Barrio Demo", "Demostración", "jardin@demo.example.com", RolUsuario.VENDEDOR, "Madrid", "28001"),
    ("Mercado Artesano Demo", "Demostración", "mercado@demo.example.com", RolUsuario.VENDEDOR, "Madrid", "28001"),
    ("Hogar Alcalá Demo", "Demostración", "hogar@demo.example.com", RolUsuario.VENDEDOR, "Alcalá de Henares", "28001"),
    ("Artesanía Triana Demo", "Demostración", "sevilla-triana@demo.example.com", RolUsuario.VENDEDOR, "Sevilla", "41001"),
    ("Librería Sevilla Centro Demo", "Demostración", "sevilla-centro@demo.example.com", RolUsuario.VENDEDOR, "Sevilla", "41001"),
    ("Flores Nervión Demo", "Demostración", "sevilla-nervion@demo.example.com", RolUsuario.VENDEDOR, "Sevilla", "41001"),
)

COMPARABLE_STORES = (
    ("libreria", "Librería Horizonte Demo", "Calle Demo 1", "Madrid", 40.416800, -3.703800, True),
    ("tecnologia", "Tecnología Centro Demo", "Calle Demo 2", "Madrid", 40.420000, -3.700000, True),
    ("jardin", "Jardín del Barrio Demo", "Calle Demo 3", "Madrid", 40.430000, -3.710000, False),
    ("mercado", "Mercado Artesano Demo", "Calle Demo 4", "Madrid", 40.460000, -3.690000, True),
    ("hogar", "Hogar Alcalá Demo", "Calle Demo 5", "Alcalá de Henares", 40.481000, -3.364000, False),
    ("sevilla-triana", "Artesanía Triana Demo", "Calle Demo Triana 1", "Sevilla", 37.383000, -6.003000, True),
    ("sevilla-centro", "Librería Sevilla Centro Demo", "Calle Demo Centro 2", "Sevilla", 37.389100, -5.984500, True),
    ("sevilla-nervion", "Flores Nervión Demo", "Calle Demo Nervión 3", "Sevilla", 37.382500, -5.970000, False),
)

COMPARABLE_PRODUCTS = (
    ("libreria", "Novela de aventuras", Categoria.CULTURA_OCIO, 18.00, 14.00, 22),
    ("libreria", "Juego de mesa familiar", Categoria.CULTURA_OCIO, 32.00, None, 12),
    ("libreria", "Cuaderno de notas", Categoria.PAPELERIA_OFICINA, 6.50, None, 40),
    ("tecnologia", "Auriculares inalámbricos", Categoria.TECNOLOGIA_ELECTRONICA, 49.90, 39.90, 19),
    ("tecnologia", "Teclado compacto", Categoria.TECNOLOGIA_ELECTRONICA, 29.90, None, 10),
    ("tecnologia", "Ratón agotado", Categoria.TECNOLOGIA_ELECTRONICA, 15.00, None, 0),
    ("jardin", "Planta de interior", Categoria.FLORISTERIAS_JARDINERIA, 12.00, None, 18),
    ("jardin", "Ramo de flores", Categoria.FLORISTERIAS_JARDINERIA, 25.00, 20.00, 8),
    ("jardin", "Maceta de cerámica", Categoria.HOGAR_BRICOLAJE, 9.50, None, 15),
    ("mercado", "Cesta de productos artesanos", Categoria.ALIMENTACION_BEBIDAS, 24.00, 21.00, 20),
    ("mercado", "Bolsa de tela", Categoria.MODA_COMPLEMENTOS, 8.00, None, 30),
    ("mercado", "Jabón artesanal", Categoria.SALUD_BIENESTAR, 5.00, None, 35),
    ("hogar", "Lámpara de escritorio", Categoria.HOGAR_BRICOLAJE, 35.00, None, 10),
    ("hogar", "Kit de herramientas", Categoria.HOGAR_BRICOLAJE, 42.00, None, 7),
    ("hogar", "Organizador no disponible", Categoria.PAPELERIA_OFICINA, 11.00, None, 5),
    ("sevilla-triana", "Azulejo decorativo", Categoria.HOGAR_BRICOLAJE, 18.00, 15.00, 20),
    ("sevilla-triana", "Abanico artesanal", Categoria.MODA_COMPLEMENTOS, 22.00, None, 15),
    ("sevilla-triana", "Taza de cerámica sevillana", Categoria.HOGAR_BRICOLAJE, 12.00, None, 25),
    ("sevilla-centro", "Guía de paseos por Sevilla", Categoria.CULTURA_OCIO, 16.50, 13.50, 30),
    ("sevilla-centro", "Cuaderno ilustrado", Categoria.PAPELERIA_OFICINA, 7.50, None, 40),
    ("sevilla-centro", "Juego de cartas", Categoria.CULTURA_OCIO, 9.00, None, 18),
    ("sevilla-nervion", "Ramo de temporada", Categoria.FLORISTERIAS_JARDINERIA, 28.00, 24.00, 12),
    ("sevilla-nervion", "Planta aromática", Categoria.FLORISTERIAS_JARDINERIA, 6.00, None, 20),
    ("sevilla-nervion", "Jardinera de balcón", Categoria.HOGAR_BRICOLAJE, 19.00, None, 10),
)


def seed(reset=False):
    """Restablece únicamente la fixture demo para obtener mediciones comparables."""
    if len(DEMO_PASSWORD) < 12:
        raise SystemExit("DEMO_PASSWORD debe tener al menos 12 caracteres.")
    with SessionLocal() as db:
        demo_emails = {row[2] for row in COMPARABLE_ACCOUNTS}
        demo_users = db.query(Usuario).filter(
            (Usuario.email.in_(demo_emails)) | Usuario.email.endswith('@distans-demo.com')
        ).all()
        user_ids = [user.id for user in demo_users]
        store_ids = [row[0] for row in db.query(Tienda.id).filter(Tienda.vendedor_id.in_(user_ids)).all()] if user_ids else []
        product_ids = [row[0] for row in db.query(Producto.id).filter(Producto.tienda_id.in_(store_ids)).all()] if store_ids else []
        order_ids = [row[0] for row in db.query(Pedido.id).filter(
            (Pedido.usuario_id.in_(user_ids)) | Pedido.codigo_pedido.in_([f'PED-DEMO-{i:03d}' for i in range(1, 6)] + ['DIS-DEMO-ENTREGADO'])
        ).all()] if user_ids else []
        cart_ids = [row[0] for row in db.query(Carrito.id).filter(Carrito.usuario_id.in_(user_ids)).all()] if user_ids else []

        if order_ids:
            db.query(ProductoPedido).filter(ProductoPedido.pedido_id.in_(order_ids)).delete(synchronize_session=False)
            db.query(Subpedido).filter(Subpedido.pedido_id.in_(order_ids)).delete(synchronize_session=False)
            db.query(Pedido).filter(Pedido.id.in_(order_ids)).delete(synchronize_session=False)
        if cart_ids:
            db.query(ProductoCarrito).filter(ProductoCarrito.carrito_id.in_(cart_ids)).delete(synchronize_session=False)
        if product_ids:
            for model in (ProductoFavorito, ValoracionProducto, ComentarioProducto, VisitaProducto):
                db.query(model).filter(model.producto_id.in_(product_ids)).delete(synchronize_session=False)
            db.query(ProductoCarrito).filter(ProductoCarrito.producto_id.in_(product_ids)).delete(synchronize_session=False)
            db.query(Producto).filter(Producto.id.in_(product_ids)).delete(synchronize_session=False)
        if store_ids:
            for model in (TiendaFavorita, ValoracionTienda, ComentarioTienda, VisitaTienda):
                db.query(model).filter(model.tienda_id.in_(store_ids)).delete(synchronize_session=False)
            db.query(PagoPlan).filter(PagoPlan.tienda_id.in_(store_ids)).delete(synchronize_session=False)
            db.query(CoordenadasTienda).filter(CoordenadasTienda.tienda_id.in_(store_ids)).delete(synchronize_session=False)
            db.query(Tienda).filter(Tienda.id.in_(store_ids)).delete(synchronize_session=False)
        if user_ids:
            db.query(Carrito).filter(Carrito.usuario_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(RestablecimientoContrasena).filter(RestablecimientoContrasena.usuario_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(Usuario).filter(Usuario.id.in_(user_ids)).delete(synchronize_session=False)
        db.flush()
        db.expunge_all()

        users = {}
        for nombre, apellidos, email, rol, ciudad, postal in COMPARABLE_ACCOUNTS:
            user = Usuario(
                nombre=nombre, apellidos=apellidos, email=email, rol=rol,
                contrasena_hash=hash_password(DEMO_PASSWORD), activo=True,
                telefono='600123123', direccion='Calle Demo 10', ciudad=ciudad,
                codigo_postal=postal,
            )
            db.add(user); db.flush(); users[email] = user

        stores = {}
        seller_emails = [row[2] for row in COMPARABLE_ACCOUNTS if row[3] == RolUsuario.VENDEDOR]
        for index, ((slug, name, address, city, lat, lng, premium), email) in enumerate(zip(COMPARABLE_STORES, seller_emails)):
            store = Tienda(
                nombre=name, descripcion='Comercio ficticio para probar DISTANS.',
                direccion=address, ubicacion=city, horario='Lunes a viernes, 09:00-20:00',
                vendedor_id=users[email].id, plan='Premium' if premium else 'Freemium',
                suscripcion_activa=premium, pasarela_activa=premium,
                fecha_renovacion_plan=None, imagen=None,
            )
            db.add(store); db.flush()
            db.add(CoordenadasTienda(tienda_id=store.id, latitud=lat, longitud=lng))
            stores[slug] = store

        products = []
        by_name = {}
        for index, (slug, name, category, price, offer, stock) in enumerate(COMPARABLE_PRODUCTS):
            store = stores[slug]
            product = Producto(
                nombre=name, descripcion=f'{name}. Producto ficticio para la demostración.',
                precio=price, precio_oferta=offer, categoria=category, tienda_id=store.id,
                stock=stock, disponible=name != 'Organizador no disponible',
                destacado=index % 3 == 0, modalidad_compra='online' if store.plan == 'Premium' else 'presencial',
                marca='DISTANS Demo', imagen=None,
            )
            db.add(product); db.flush(); products.append(product); by_name[name] = product

        buyer = users['comprador@demo.example.com']
        second_buyer = users['comprador2@demo.example.com']
        cart = Carrito(usuario_id=buyer.id, sesion=None)
        db.add(cart); db.flush()
        db.add(ProductoCarrito(carrito_id=cart.id, producto_id=by_name['Juego de mesa familiar'].id, cantidad=2))
        db.add(ProductoFavorito(usuario_id=buyer.id, producto_id=by_name['Novela de aventuras'].id))
        db.add(TiendaFavorita(usuario_id=buyer.id, tienda_id=stores['jardin'].id))

        now = datetime.utcnow()
        for product_index, product in enumerate(products):
            for visit in range(3):
                db.add(VisitaProducto(producto_id=product.id,
                    visitante_hash=f'demo-product-{product_index}-{visit}'.ljust(64, '0'),
                    fecha=now - timedelta(days=visit)))
        for store_index, store in enumerate(stores.values()):
            for visit in range(7):
                db.add(VisitaTienda(tienda_id=store.id,
                    visitante_hash=f'demo-store-{store_index}-{visit}'.ljust(64, '0'),
                    fecha=now - timedelta(days=visit)))

        order_specs = (
            ('PED-DEMO-001', buyer, by_name['Novela de aventuras'], EstadoPedido.PREPARACION, EstadoSubpedido.PREPARACION, MetodoPago.EFECTIVO, False, False),
            ('PED-DEMO-002', second_buyer, by_name['Novela de aventuras'], EstadoPedido.ENVIADO, EstadoSubpedido.RECOGIDO, MetodoPago.EFECTIVO, False, False),
            ('PED-DEMO-003', buyer, by_name['Novela de aventuras'], EstadoPedido.ENTREGADO, EstadoSubpedido.RECOGIDO, MetodoPago.EFECTIVO, False, False),
            ('PED-DEMO-004', second_buyer, by_name['Auriculares inalámbricos'], EstadoPedido.PREPARACION, EstadoSubpedido.PREPARACION, MetodoPago.TARJETA_CREDITO, True, False),
            ('PED-DEMO-005', buyer, by_name['Auriculares inalámbricos'], EstadoPedido.CANCELADO, EstadoSubpedido.CANCELADO, MetodoPago.TARJETA_CREDITO, False, True),
        )
        for index, (code, customer, product, state, substate, method, paid, cancelled) in enumerate(order_specs):
            list_price = Decimal(str(product.precio))
            unit_price = Decimal(str(product.precio_oferta if product.precio_oferta is not None else product.precio))
            subtotal = Decimal('0') if cancelled else list_price
            discount = Decimal('0') if cancelled else list_price - unit_price
            tax = Decimal('0') if cancelled else (unit_price * Decimal('0.21')).quantize(Decimal('0.01'))
            total = Decimal('0') if cancelled else unit_price + tax
            order = Pedido(
                codigo_pedido=code, usuario_id=customer.id, fecha=now - timedelta(days=index),
                nombre_comprador=customer.nombre, apellidos_comprador=customer.apellidos,
                email_comprador=customer.email, telefono=customer.telefono,
                subtotal=subtotal, descuento=discount, impuesto=tax, coste_entrega=Decimal('0'), total=total,
                metodo_pago=method, pago_completado=paid, estado=state, moneda='EUR',
                carrito_vaciado=True, reserva_liberada=cancelled,
                importe_pago_original=unit_price + (unit_price * Decimal('0.21')).quantize(Decimal('0.01')),
                direccion_envio=f'{customer.direccion}, {customer.ciudad} ({customer.codigo_postal})',
                direccion_facturacion=f'{customer.direccion}, {customer.ciudad} ({customer.codigo_postal})',
            )
            db.add(order); db.flush()
            suborder = Subpedido(pedido_id=order.id, tienda_id=product.tienda_id, estado=substate)
            db.add(suborder); db.flush()
            db.add(ProductoPedido(pedido_id=order.id, subpedido_id=suborder.id,
                producto_id=product.id, cantidad=1, precio_unitario=unit_price,
                total=unit_price, cancelado=cancelled))
        db.commit()
        print('Fixture comparable preparada: 11 usuarios, 8 tiendas, 24 productos y 5 pedidos.')
        print('Se han restablecido exclusivamente las cuentas y datos de demostración.')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="alias obsoleto; ya no borra datos")
    seed(parser.parse_args().reset)
