"""Prepara diez pedidos aislados para el escenario Locust de escritura."""

from datetime import datetime
from decimal import Decimal

from app.database import SessionLocal
from app.models import (
    EstadoPedido, EstadoSubpedido, MetodoPago, Pedido, Producto, ProductoPedido,
    Subpedido, Tienda, Usuario,
)


def prepare():
    with SessionLocal() as db:
        buyer = db.query(Usuario).filter_by(email="comprador@demo.example.com").first()
        seller = db.query(Usuario).filter_by(email="libreria@demo.example.com").first()
        if buyer is None or seller is None:
            raise SystemExit("Faltan las cuentas demo; ejecuta primero python -m scripts.seed_catalogo")
        store = db.query(Tienda).filter_by(vendedor_id=seller.id).first()
        product = db.query(Producto).filter_by(tienda_id=store.id, nombre="Novela de aventuras").first() if store else None
        if store is None or product is None:
            raise SystemExit("Faltan la tienda o el producto demo del vendedor de carga")

        existing = db.query(Pedido).filter(Pedido.codigo_pedido.startswith("LOAD-WRITE-")).all()
        for order in existing:
            db.delete(order)
        db.flush()

        unit_price = Decimal(str(product.precio_oferta or product.precio))
        tax = (unit_price * Decimal("0.21")).quantize(Decimal("0.01"))
        for index in range(1, 11):
            order = Pedido(
                codigo_pedido=f"LOAD-WRITE-{index:03d}", usuario_id=buyer.id, fecha=datetime.utcnow(),
                nombre_comprador=buyer.nombre, apellidos_comprador=buyer.apellidos,
                email_comprador=buyer.email, telefono=buyer.telefono,
                subtotal=unit_price, descuento=Decimal("0"), impuesto=tax,
                coste_entrega=Decimal("0"), total=unit_price + tax,
                metodo_pago=MetodoPago.EFECTIVO, pago_completado=False,
                estado=EstadoPedido.PREPARACION, moneda="EUR", carrito_vaciado=True,
                reserva_liberada=False, importe_pago_original=unit_price + tax,
                direccion_envio=buyer.direccion or "Calle Demo 10",
                direccion_facturacion=buyer.direccion or "Calle Demo 10",
            )
            db.add(order)
            db.flush()
            suborder = Subpedido(pedido_id=order.id, tienda_id=store.id, estado=EstadoSubpedido.PREPARACION)
            db.add(suborder)
            db.flush()
            db.add(ProductoPedido(
                pedido_id=order.id, subpedido_id=suborder.id, producto_id=product.id,
                cantidad=1, precio_unitario=unit_price, total=unit_price, cancelado=False,
            ))
        db.commit()
        print("Carga de escritura preparada: 10 pedidos LOAD-WRITE en estado de preparación.")


if __name__ == "__main__":
    prepare()
