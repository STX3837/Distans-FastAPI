"""Reinicia los datos demo conservando las cuentas. Solo desarrollo/pruebas."""
import argparse
import os
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import SessionLocal
from app.models import (Categoria, ComentarioProducto, ComentarioTienda,
    CoordenadasTienda, EstadoPedido, EstadoSubpedido, MetodoPago, Pedido, Producto,
    ProductoFavorito, ProductoPedido, RolUsuario, Subpedido, Tienda, TiendaFavorita,
    Usuario, ValoracionProducto, ValoracionTienda)
from app.security import hash_password

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "DistansDemo2026!")
DEMO_ACCOUNTS = (
    ("Administrador", "Demo", "demo.admin@distans-demo.com", RolUsuario.ADMIN),
    ("Comprador", "Demo", "demo.comprador@distans-demo.com", RolUsuario.COMPRADOR),
    ("Vendedor", "Alimentación", "demo.vendedor1@distans-demo.com", RolUsuario.VENDEDOR),
    ("Vendedora", "Artesanía", "demo.vendedor2@distans-demo.com", RolUsuario.VENDEDOR),
    ("Vendedor", "Tecnología", "demo.vendedor3@distans-demo.com", RolUsuario.VENDEDOR),
    ("Vendedora", "Jardinería", "demo.vendedor4@distans-demo.com", RolUsuario.VENDEDOR),
    ("Vendedor", "Librería", "demo.vendedor5@distans-demo.com", RolUsuario.VENDEDOR),
    ("Vendedora", "Triana", "demo.vendedor6@distans-demo.com", RolUsuario.VENDEDOR),
    ("Vendedor", "Nervión", "demo.vendedor7@distans-demo.com", RolUsuario.VENDEDOR),
    ("Vendedora", "Macarena", "demo.vendedor8@distans-demo.com", RolUsuario.VENDEDOR),
    ("Vendedor", "Alameda", "demo.vendedor9@distans-demo.com", RolUsuario.VENDEDOR),
    ("Vendedora", "Sevilla Este", "demo.vendedor10@distans-demo.com", RolUsuario.VENDEDOR),
)
TIENDAS = [
    ("Comercio Carmona", "Alimentación y productos de cercanía.", "Calle San Pedro 12, Carmona", "Carmona", 37.4713, -5.6462),
    ("Artesanía Alcázar", "Regalos y piezas de artesanos locales.", "Calle Prim 8, Carmona", "Centro histórico", 37.4728, -5.6408),
    ("Tecno Campiña", "Tecnología y oficina de proximidad.", "Avenida de la Estación 24, Carmona", "Hytasa", 37.4688, -5.6512),
    ("Verde Alcores", "Flores y jardinería para el hogar.", "Paseo del Estatuto 5, Carmona", "Los Alcores", 37.4749, -5.6440),
    ("Librería Puerta Sevilla", "Libros, papelería y cultura.", "Plaza de San Fernando 3, Carmona", "Puerta Sevilla", 37.4706, -5.6429),
    ("Sabores de Triana", "Productos andaluces y alimentación artesanal.", "Calle San Jacinto 28, Sevilla", "Triana", 37.3837, -6.0032),
    ("Bienestar Nervión", "Cosmética natural y cuidado personal.", "Calle Luis de Morales 20, Sevilla", "Nervión", 37.3829, -5.9707),
    ("Flores de la Macarena", "Floristería de barrio y jardinería urbana.", "Calle San Luis 91, Sevilla", "Macarena", 37.4036, -5.9882),
    ("Cultura Alameda", "Libros, ilustración y ocio creativo.", "Alameda de Hércules 45, Sevilla", "Alameda", 37.3974, -5.9950),
    ("Tecnología Sevilla Este", "Accesorios electrónicos y material de oficina.", "Avenida de las Ciencias 34, Sevilla", "Sevilla Este", 37.4004, -5.9212),
]
PRODUCTOS = [
    [("Aceite de oliva virgen extra", "Botella local de 500 ml.", 12.90, 10.90, Categoria.ALIMENTACION_BEBIDAS, 24, True), ("Cesta de la campiña", "Conservas, miel y dulces.", 29.50, None, Categoria.ALIMENTACION_BEBIDAS, 9, True), ("Infusión andaluza", "Mezcla aromática de 100 g.", 6.75, None, Categoria.SALUD_BIENESTAR, 30, False)],
    [("Taza de cerámica artesanal", "Pieza esmaltada a mano.", 16.00, None, Categoria.HOGAR_BRICOLAJE, 14, True), ("Bolso de cuero artesanal", "Piel curtida vegetal.", 54.90, 44.90, Categoria.MODA_COMPLEMENTOS, 5, True), ("Lámina de Carmona", "Impresión artística A3.", 19.00, None, Categoria.CULTURA_OCIO, 18, False)],
    [("Auriculares inalámbricos", "Bluetooth con estuche de carga.", 39.95, 34.95, Categoria.TECNOLOGIA_ELECTRONICA, 11, True), ("Soporte para portátil", "Soporte plegable de aluminio.", 27.50, None, Categoria.PAPELERIA_OFICINA, 16, False), ("Cable USB-C reforzado", "Carga y datos, dos metros.", 9.90, None, Categoria.TECNOLOGIA_ELECTRONICA, 40, False)],
    [("Planta con maceta", "Planta resistente de interior.", 24.00, None, Categoria.FLORISTERIAS_JARDINERIA, 8, True), ("Ramo de temporada", "Flores frescas del día.", 29.50, 25.00, Categoria.FLORISTERIAS_JARDINERIA, 7, True), ("Kit de huerto urbano", "Semillas, sustrato y macetas.", 18.25, None, Categoria.FLORISTERIAS_JARDINERIA, 13, False)],
    [("Cuaderno ilustrado", "A5 de papel reciclado.", 9.00, None, Categoria.PAPELERIA_OFICINA, 25, True), ("Novela histórica local", "Ambientada en Los Alcores.", 21.90, 18.50, Categoria.CULTURA_OCIO, 12, True), ("Set de escritura sostenible", "Material reciclado.", 13.40, None, Categoria.PAPELERIA_OFICINA, 20, False)],
    [("Miel de azahar", "Tarro artesanal de 500 g.", 11.50, 9.95, Categoria.ALIMENTACION_BEBIDAS, 22, True), ("Tortas de aceite", "Dulce tradicional sevillano.", 5.80, None, Categoria.ALIMENTACION_BEBIDAS, 35, True), ("Selección de aceitunas", "Tres variedades aliñadas.", 8.40, None, Categoria.ALIMENTACION_BEBIDAS, 18, False)],
    [("Jabón natural de naranja", "Elaborado con aceites vegetales.", 6.90, None, Categoria.SALUD_BIENESTAR, 28, True), ("Aceite corporal de azahar", "Aceite hidratante de 100 ml.", 17.50, 14.90, Categoria.SALUD_BIENESTAR, 14, True), ("Vela aromática", "Cera vegetal y aroma suave.", 13.20, None, Categoria.HOGAR_BRICOLAJE, 19, False)],
    [("Ramo silvestre", "Flores de temporada preparadas a mano.", 27.00, 23.50, Categoria.FLORISTERIAS_JARDINERIA, 9, True), ("Maceta de hierbas aromáticas", "Romero, tomillo y albahaca.", 15.90, None, Categoria.FLORISTERIAS_JARDINERIA, 16, True), ("Regadera metálica", "Regadera compacta para interior.", 19.80, None, Categoria.HOGAR_BRICOLAJE, 11, False)],
    [("Guía ilustrada de Sevilla", "Recorrido cultural por sus barrios.", 18.90, 16.50, Categoria.CULTURA_OCIO, 17, True), ("Juego creativo de acuarelas", "Estuche para iniciarse en acuarela.", 24.50, None, Categoria.CULTURA_OCIO, 10, True), ("Marcapáginas artesanal", "Pieza de madera grabada.", 4.75, None, Categoria.PAPELERIA_OFICINA, 40, False)],
    [("Cargador USB-C compacto", "Carga rápida de 30 W.", 22.90, 19.90, Categoria.TECNOLOGIA_ELECTRONICA, 20, True), ("Ratón inalámbrico", "Diseño silencioso y ergonómico.", 18.50, None, Categoria.TECNOLOGIA_ELECTRONICA, 26, True), ("Organizador de escritorio", "Bandejas modulares recicladas.", 16.00, None, Categoria.PAPELERIA_OFICINA, 15, False)],
]

def seed(reset=False):
    """Añade los datos demo que falten sin borrar ni sobrescribir registros."""
    if len(DEMO_PASSWORD) < 12:
        raise SystemExit("DEMO_PASSWORD debe tener al menos 12 caracteres.")
    with SessionLocal() as db:
        creados = {"cuentas": 0, "tiendas": 0, "productos": 0}
        demos = []
        for nombre, apellidos, email, rol in DEMO_ACCOUNTS:
            usuario = db.query(Usuario).filter_by(email=email).first()
            if usuario is None:
                usuario = Usuario(nombre=nombre, apellidos=apellidos, email=email, rol=rol,
                    contrasena_hash=hash_password(DEMO_PASSWORD), activo=True,
                    telefono="600123123", direccion="Calle Demo 1", ciudad="Carmona", codigo_postal="41410")
                db.add(usuario); db.flush(); creados["cuentas"] += 1
            demos.append(usuario)
        comprador = demos[1]
        vendedores = demos[2:]
        tiendas, productos = [], []
        tiendas_con_foto = {0, 2, 5, 7, 9}
        for indice_tienda, (vendedor, datos, catalogo) in enumerate(zip(vendedores, TIENDAS, PRODUCTOS)):
            nombre, descripcion, direccion, ubicacion, latitud, longitud = datos
            tienda = db.query(Tienda).filter_by(vendedor_id=vendedor.id).first()
            if tienda is None:
                tienda = Tienda(nombre=nombre, descripcion=descripcion, direccion=direccion, ubicacion=ubicacion,
                    horario="L-S 09:30-20:30", vendedor_id=vendedor.id, plan="Premium", suscripcion_activa=True,
                    pasarela_activa=True, fecha_renovacion_plan=datetime.utcnow() + timedelta(days=30),
                    imagen="/static/demo/tienda-demo.png" if indice_tienda in tiendas_con_foto else None)
                db.add(tienda); db.flush(); creados["tiendas"] += 1
            if tienda.coordenadas is None:
                db.add(CoordenadasTienda(tienda_id=tienda.id, latitud=latitud, longitud=longitud))
            tiendas.append(tienda)
            for indice_producto, (nombre_p, descripcion_p, precio, oferta, categoria, stock, destacado) in enumerate(catalogo):
                producto = db.query(Producto).filter_by(tienda_id=tienda.id, nombre=nombre_p).first()
                if producto is None:
                    producto = Producto(nombre=nombre_p, descripcion=descripcion_p, precio=precio, precio_oferta=oferta,
                        categoria=categoria, tienda_id=tienda.id, stock=stock, disponible=True, destacado=destacado,
                        modalidad_compra="online", marca="Comercio local",
                        imagen="/static/demo/producto-demo.png" if (indice_tienda + indice_producto) % 3 == 0 else None)
                    db.add(producto); db.flush(); creados["productos"] += 1
                productos.append(producto)
        db.flush()
        for i, producto in enumerate(productos[:5]):
            puntuacion = 5 if i < 3 else 4
            if db.get(ValoracionProducto, (comprador.id, producto.id)) is None:
                db.add(ValoracionProducto(usuario_id=comprador.id, producto_id=producto.id, puntuacion=puntuacion))
        for i, tienda in enumerate(tiendas[:3]):
            puntuacion = 5 if i == 0 else 4
            if db.get(ValoracionTienda, (comprador.id, tienda.id)) is None:
                db.add(ValoracionTienda(usuario_id=comprador.id, tienda_id=tienda.id, puntuacion=puntuacion))
        for modelo, clave, valores in (
            (ProductoFavorito, (comprador.id, productos[0].id), dict(usuario_id=comprador.id, producto_id=productos[0].id)),
            (ProductoFavorito, (comprador.id, productos[6].id), dict(usuario_id=comprador.id, producto_id=productos[6].id)),
            (TiendaFavorita, (comprador.id, tiendas[0].id), dict(usuario_id=comprador.id, tienda_id=tiendas[0].id)),
            (ComentarioProducto, (comprador.id, productos[0].id), dict(usuario_id=comprador.id, producto_id=productos[0].id, texto="Muy buena calidad y recogida rápida. Comentario de demostración.")),
            (ComentarioTienda, (comprador.id, tiendas[0].id), dict(usuario_id=comprador.id, tienda_id=tiendas[0].id, texto="Atención cercana y un catálogo muy completo.")),
        ):
            if db.get(modelo, clave) is None:
                db.add(modelo(**valores))
        if db.query(Pedido).filter_by(codigo_pedido="DIS-DEMO-ENTREGADO").first() is None:
            pedido = Pedido(codigo_pedido="DIS-DEMO-ENTREGADO", usuario_id=comprador.id, nombre_comprador=comprador.nombre,
                apellidos_comprador=comprador.apellidos, email_comprador=comprador.email, telefono=comprador.telefono or "600123123",
                subtotal=Decimal("43.60"), descuento=Decimal("0"), impuesto=Decimal("9.16"), coste_entrega=Decimal("0"),
                total=Decimal("52.76"), metodo_pago=MetodoPago.TARJETA_CREDITO, pago_completado=True,
                estado=EstadoPedido.ENTREGADO, direccion_envio="Calle Demo 1, Carmona", direccion_facturacion="Calle Demo 1, Carmona")
            db.add(pedido); db.flush()
            sub = Subpedido(pedido_id=pedido.id, tienda_id=tiendas[0].id, estado=EstadoSubpedido.RECOGIDO)
            db.add(sub); db.flush()
            db.add(ProductoPedido(pedido_id=pedido.id, subpedido_id=sub.id, producto_id=productos[0].id,
                cantidad=4, precio_unitario=Decimal("10.90"), total=Decimal("43.60")))
        db.commit()
        print("Seed aditivo completado: " + ", ".join(f"{cantidad} {tipo} nuevos" for tipo, cantidad in creados.items()) + ".")
        print("No se ha borrado ni sobrescrito ningún registro existente.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="alias obsoleto; ya no borra datos")
    seed(parser.parse_args().reset)
