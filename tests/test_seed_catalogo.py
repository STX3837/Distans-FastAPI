from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    Base, Carrito, EstadoPedido, EstadoSubpedido, Pedido, Producto, ProductoCarrito,
    ProductoFavorito, Subpedido, Tienda, TiendaFavorita, Usuario, VisitaProducto,
    VisitaTienda,
)
from app.security import verify_password
from scripts import seed_catalogo


def test_seed_es_repetible_y_equivalente_a_django(monkeypatch):
    engine = create_engine(
        'sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine, tables=[table for table in Base.metadata.sorted_tables if table.name != 'ubicaciones'],
    )
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(seed_catalogo, 'SessionLocal', factory)

    seed_catalogo.seed()
    seed_catalogo.seed()

    with factory() as db:
        assert db.query(Usuario).count() == 11
        assert db.query(Tienda).count() == 8
        assert db.query(Producto).count() == 24
        assert db.query(Pedido).count() == 5
        assert db.query(Subpedido).count() == 5
        assert db.query(Carrito).count() == 1
        assert db.query(ProductoCarrito).count() == 1
        assert db.query(ProductoFavorito).count() == 1
        assert db.query(TiendaFavorita).count() == 1
        assert db.query(VisitaProducto).count() == 72
        assert db.query(VisitaTienda).count() == 56

        buyer = db.query(Usuario).filter_by(email='comprador@demo.example.com').one()
        assert verify_password('DemoDistans2026!', buyer.contrasena_hash)
        assert db.query(Producto).filter_by(nombre='Novela de aventuras').one().stock == 22
        assert db.query(Producto).filter_by(nombre='Auriculares inalámbricos').one().stock == 19
        assert all(product.imagen is None for product in db.query(Producto))
        assert all(store.imagen is None for store in db.query(Tienda))

        cancelled = db.query(Pedido).filter_by(codigo_pedido='PED-DEMO-005').one()
        assert cancelled.estado == EstadoPedido.CANCELADO
        assert cancelled.subpedidos[0].estado == EstadoSubpedido.CANCELADO
        assert cancelled.items[0].cancelado is True
        assert cancelled.total == 0
