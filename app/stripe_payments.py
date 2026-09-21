"""Stripe Checkout: datos bancarios exclusivamente en Stripe."""
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import update
from app.models import Carrito, ProductoCarrito, EstadoPedido, EstadoSubpedido, Pedido, Producto


def vaciar_carrito_pedido(db, pedido):
    if pedido.carrito_id is None or pedido.carrito_vaciado:
        return
    carrito = db.query(Carrito).filter_by(id=pedido.carrito_id).with_for_update().first()
    if carrito:
        db.query(ProductoCarrito).filter_by(carrito_id=carrito.id).delete(synchronize_session='fetch')
        carrito.fecha_actualizacion = datetime.utcnow()
    pedido.carrito_vaciado = True


def configuracion():
    key = os.getenv('STRIPE_SECRET_KEY', '')
    secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    base = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')
    parsed = urlparse(base)
    production = os.getenv('ENVIRONMENT', 'development').lower() in {'production', 'staging'}
    if not key or not secret or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(503, 'El pago con tarjeta no está configurado. Inténtalo más tarde.')
    if parsed.scheme != 'https' and (production or parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1'}):
        raise HTTPException(503, 'El pago requiere una URL pública segura.')
    return key, secret, base


def cliente():
    import stripe
    key, _, _ = configuracion()
    return stripe.StripeClient(key, max_network_retries=2)


def centimos(value):
    return int(value * 100)


def crear_sesion(pedido):
    _, _, base = configuracion()
    lines = [{'price_data': {'currency': 'eur', 'unit_amount': centimos(item.precio_unitario),
              'product_data': {'name': item.producto.nombre}}, 'quantity': item.cantidad} for item in pedido.items]
    for name, value in [('IVA', pedido.impuesto), ('Envío', pedido.coste_entrega)]:
        if value:
            lines.append({'price_data': {'currency': 'eur', 'unit_amount': centimos(value),
                          'product_data': {'name': name}}, 'quantity': 1})
    # No datos personales en metadata ni en URLs. Idempotencia incluso si se pierde la respuesta.
    return cliente().v1.checkout.sessions.create({
        'mode': 'payment', 'payment_method_types': ['card'], 'locale': 'es',
        'line_items': lines, 'customer_email': pedido.email_comprador,
        'client_reference_id': str(pedido.id), 'metadata': {'pedido_id': str(pedido.id)},
        'success_url': base + '/pago/resultado', 'cancel_url': base + '/pago/resultado?cancelado=1',
        'expires_at': int(pedido.reserva_expira.replace(tzinfo=timezone.utc).timestamp()),
    }, options={'idempotency_key': 'checkout-' + pedido.codigo_pedido})


def liberar_reserva(db, pedido):
    if pedido.reserva_liberada or pedido.pago_completado or pedido.estado != EstadoPedido.PREPARACION:
        return
    for item in sorted(pedido.items, key=lambda item: item.producto_id):
        db.execute(update(Producto).where(Producto.id == item.producto_id).values(stock=Producto.stock + item.cantidad))
    pedido.reserva_liberada = True
    pedido.estado = EstadoPedido.CANCELADO
    for subpedido in pedido.subpedidos:
        subpedido.estado = EstadoSubpedido.CANCELADO


def aplicar_sesion(db, pedido, session):
    if session.get('client_reference_id') != str(pedido.id) or session.get('metadata', {}).get('pedido_id') != str(pedido.id):
        raise ValueError('Referencia de pago incorrecta')
    if pedido.stripe_session_id and session['id'] != pedido.stripe_session_id:
        raise ValueError('Sesión de pago incorrecta')
    if session.get('currency') != 'eur' or session.get('amount_total') != centimos(pedido.importe_pago_original or pedido.total):
        raise ValueError('Importe de pago incorrecto')
    pedido.stripe_session_id = session['id']
    if session.get('payment_status') in {'paid', 'no_payment_required'} and session.get('status') == 'complete':
        if pedido.reserva_liberada or (pedido.estado == EstadoPedido.CANCELADO and not pedido.pago_completado):
            raise ValueError('Pago recibido para una reserva cancelada')
        pedido.pago_completado = True
        vaciar_carrito_pedido(db, pedido)
    elif session.get('status') == 'expired':
        liberar_reserva(db, pedido)


def abrir_pago(db, pedido):
    import stripe
    pedido = db.query(Pedido).filter_by(id=pedido.id).with_for_update().one()
    if pedido.estado == EstadoPedido.CANCELADO:
        raise HTTPException(409, 'La reserva ha caducado. Inicia otra compra.')
    try:
        session = (cliente().v1.checkout.sessions.retrieve(pedido.stripe_session_id)
                   if pedido.stripe_session_id else crear_sesion(pedido))
        session = session if isinstance(session, dict) else session.to_dict()
        aplicar_sesion(db, pedido, session)
        db.commit()
    except stripe.InvalidRequestError:
        db.rollback()
        pedido = db.query(Pedido).filter_by(id=pedido.id).with_for_update().one()
        if not pedido.stripe_session_id:
            liberar_reserva(db, pedido)
            db.commit()
        raise HTTPException(502, 'No se pudo iniciar el pago. Vuelve a iniciar la compra.')
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        # Una interrupción de red puede ocurrir después de crear la sesión. No liberar stock a ciegas.
        raise HTTPException(502, 'No se pudo conectar con Stripe. Reintenta la confirmación del pedido.')
    if pedido.estado == EstadoPedido.CANCELADO:
        raise HTTPException(409, 'La reserva ha caducado. Inicia otra compra.')
    if pedido.pago_completado:
        return None
    if not session.get('url'):
        raise HTTPException(502, 'Stripe no ha proporcionado la pasarela de pago. Reintenta la confirmación.')
    return session['url']


def reconciliar_reservas(db):
    """Ejecutar periódicamente; comprueba Stripe antes de devolver stock."""
    import stripe
    now = datetime.utcnow()
    ids = [row[0] for row in db.query(Pedido.id).filter(Pedido.estado == EstadoPedido.PREPARACION,
           Pedido.pago_completado.is_(False), Pedido.reserva_expira <= now,
           Pedido.reserva_liberada.is_(False)).all()]
    for pedido_id in ids:
        try:
            pedido = db.query(Pedido).filter_by(id=pedido_id).with_for_update().one()
            if pedido.estado != EstadoPedido.PREPARACION:
                db.rollback()
                continue
            if not pedido.stripe_session_id:
                # Recupera por la misma clave una creación cuya respuesta pudo perderse.
                session = crear_sesion(pedido)
            else:
                session = cliente().v1.checkout.sessions.retrieve(pedido.stripe_session_id)
            session = session if isinstance(session, dict) else session.to_dict()
            if session.get('status') == 'open':
                session = cliente().v1.checkout.sessions.expire(session['id'])
                session = session if isinstance(session, dict) else session.to_dict()
            aplicar_sesion(db, pedido, session)
            db.commit()
        except stripe.InvalidRequestError:
            db.rollback()
            pedido = db.query(Pedido).filter_by(id=pedido_id).with_for_update().one()
            if not pedido.stripe_session_id:
                liberar_reserva(db, pedido)
                db.commit()
        except Exception:
            db.rollback()
            # Conserva el stock reservado hasta poder verificar el estado externo.
