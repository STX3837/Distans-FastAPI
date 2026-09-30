"""Reglas de agrupación, cancelación y estado público de los pedidos."""
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import update

from app.models import EstadoPedido, EstadoSubpedido, Producto, Subpedido

CENTIMO = Decimal("0.01")


def redondear(valor):
    return Decimal(valor).quantize(CENTIMO, rounding=ROUND_HALF_UP)


def sincronizar_subpedidos(db, pedido):
    """Agrupa las líneas activas por tienda; conserva los subpedidos cancelados."""
    with db.no_autoflush:
        existentes = {sub.tienda_id: sub for sub in pedido.subpedidos}
        tiendas_activas = set()
        for linea in pedido.items:
            if linea.cancelado:
                continue
            producto = linea.producto or db.get(Producto, linea.producto_id)
            tienda_id = producto.tienda_id
            tiendas_activas.add(tienda_id)
            sub = existentes.get(tienda_id)
            if sub is None:
                sub = Subpedido(pedido=pedido, tienda_id=tienda_id)
                db.add(sub)
                existentes[tienda_id] = sub
            linea.subpedido = sub
    db.flush()
    for sub in list(pedido.subpedidos):
        if sub.tienda_id not in tiendas_activas and sub.estado != EstadoSubpedido.CANCELADO:
            db.delete(sub)
    db.flush()


def recalcular_estado(pedido):
    activos = [sub for sub in pedido.subpedidos if sub.estado != EstadoSubpedido.CANCELADO]
    if not activos:
        pedido.estado = EstadoPedido.CANCELADO
    elif pedido.estado == EstadoPedido.ENTREGADO:
        pass  # Solo el administrador puede declarar la entrega.
    elif all(sub.estado == EstadoSubpedido.RECOGIDO for sub in activos):
        pedido.estado = EstadoPedido.ENVIADO
    else:
        pedido.estado = EstadoPedido.PREPARACION
    return pedido.estado


def cancelar_subpedido(db, pedido, subpedido):
    """Conserva las líneas canceladas para el historial y libera su stock."""
    activos = [linea for linea in pedido.items if not linea.cancelado]
    cancelados = [linea for linea in subpedido.items if not linea.cancelado]
    neto_anterior = sum((linea.total for linea in activos), Decimal(0))
    neto_cancelado = sum((linea.total for linea in cancelados), Decimal(0))
    if not cancelados or not neto_anterior:
        return
    fraccion = (neto_anterior - neto_cancelado) / neto_anterior
    for linea in cancelados:
        linea.cancelado = True
        db.execute(update(Producto).where(Producto.id == linea.producto_id).values(
            stock=Producto.stock + linea.cantidad))
    subpedido.estado = EstadoSubpedido.CANCELADO
    total_anterior = pedido.total
    pedido.descuento = redondear(pedido.descuento * fraccion)
    pedido.subtotal = redondear(neto_anterior - neto_cancelado + pedido.descuento)
    pedido.impuesto = redondear(pedido.impuesto * fraccion)
    if fraccion == 0:
        pedido.coste_entrega = Decimal(0)
    pedido.total = redondear(pedido.subtotal - pedido.descuento + pedido.impuesto + pedido.coste_entrega)
    if pedido.pago_completado:
        pedido.reembolso_pendiente = redondear((pedido.reembolso_pendiente or 0) + total_anterior - pedido.total)
    recalcular_estado(pedido)
