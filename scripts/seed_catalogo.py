"""Catálogo de demostración local; ejecutar: python -m scripts.seed_catalogo."""
from app.database import SessionLocal
from app.models import Categoria, CoordenadasTienda, Producto, RolUsuario, Tienda, Usuario
from app.security import hash_password


def seed():
    with SessionLocal() as db:
        seller = db.query(Usuario).filter_by(email="catalogo-demo@distans.test").first()
        if not seller:
            import secrets
            seller = Usuario(nombre="Catálogo", apellidos="de demostración", email="catalogo-demo@distans.test",
                             contrasena_hash=hash_password(secrets.token_urlsafe(32)), rol=RolUsuario.VENDEDOR,
                             activo=True)
            db.add(seller); db.flush()
        stores = [
            ("Demo · Mercado de Lavapiés", "Calle de Lavapiés, Madrid", 40.4087, -3.7005, [
                ("Cesta de fruta de temporada", "Fruta variada para la semana.", 18.5, None, Categoria.ALIMENTACION_BEBIDAS),
                ("Aceite de oliva virgen extra", "Botella de 500 ml.", 12.9, 10.9, Categoria.ALIMENTACION_BEBIDAS)]),
            ("Demo · Taller de Malasaña", "Calle del Espíritu Santo, Madrid", 40.4254, -3.7045, [
                ("Taza de cerámica artesanal", "Cerámica hecha a mano.", 16.0, None, Categoria.HOGAR_BRICOLAJE),
                ("Lámina ilustrada de Madrid", "Ilustración decorativa en tamaño A4.", 22.0, 19.0, Categoria.CULTURA_OCIO)]),
            ("Demo · Jardín de Chamberí", "Calle de Ponzano, Madrid", 40.4382, -3.6994, [
                ("Planta de interior con maceta", "Una planta para dar vida a tu casa.", 24.0, None, Categoria.FLORISTERIAS_JARDINERIA),
                ("Ramo de flores de temporada", "Flores frescas de colores.", 29.5, 25.0, Categoria.FLORISTERIAS_JARDINERIA)]),
            ("Demo · Artesanía del Centro", "Zona Centro, Sevilla", 37.3906, -5.9845, [
                ("Abanico de artesanía sevillana", "Abanico decorativo de demostración.", 18.0, None, Categoria.MODA_COMPLEMENTOS)]),
            ("Demo · Mercado de Triana", "Zona Triana, Sevilla", 37.3831, -5.9965, [
                ("Cesta de verduras de Sevilla", "Verduras variadas de demostración.", 15.0, 12.0, Categoria.ALIMENTACION_BEBIDAS)]),
            ("Demo · Flores de Nervión", "Zona Nervión, Sevilla", 37.3820, -5.9630, [
                ("Ramo de flores de Sevilla", "Ramo de demostración para probar el mapa.", 25.0, None, Categoria.FLORISTERIAS_JARDINERIA)]),
            ("Demo · Librería Sevilla Este", "Zona Sevilla Este, Sevilla", 37.4040, -5.9185, [
                ("Cuaderno ilustrado de Sevilla", "Cuaderno de demostración.", 9.0, None, Categoria.PAPELERIA_OFICINA)]),
        ]
        added = 0
        for name, address, lat, lon, products in stores:
            store = db.query(Tienda).filter_by(nombre=name, vendedor_id=seller.id).first()
            if not store:
                store = Tienda(nombre=name, direccion=address, ubicacion=address.rsplit(",", 1)[-1].strip(), descripcion="Tienda ficticia para probar el catálogo y el mapa.", vendedor_id=seller.id)
                db.add(store); db.flush()
            if not db.get(CoordenadasTienda, store.id):
                db.add(CoordenadasTienda(tienda_id=store.id, latitud=lat, longitud=lon))
            for name, description, price, offer, category in products:
                if not db.query(Producto).filter_by(tienda_id=store.id, nombre=name).first():
                    db.add(Producto(nombre=name, descripcion=description + " Producto de demostración.", precio=price,
                                    precio_oferta=offer, categoria=category, tienda_id=store.id, stock=12,
                                    disponible=True, destacado=True, marca="Demo Distans"))
                    added += 1
        db.commit()
        print(f"Catálogo de demostración: {added} productos nuevos; {len(stores)} tiendas geolocalizadas.")


if __name__ == "__main__":
    seed()
