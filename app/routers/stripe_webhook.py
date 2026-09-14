import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MetodoPago, Pedido
from app.stripe_payments import aplicar_sesion, configuracion, cliente

router = APIRouter(tags=['Stripe'])


@router.post('/api/stripe/webhook')
async def webhook_stripe(request: Request, db: Session = Depends(get_db)):
    _, secret, _ = configuracion()
    payload = await request.body()
    if len(payload) > 1024 * 1024:
        raise HTTPException(413, 'Evento demasiado grande')
    try:
        event = stripe.Webhook.construct_event(payload, request.headers.get('stripe-signature', ''), secret)
        event = event.to_dict()
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, 'Firma de Stripe no válida')
    if event['type'] not in {'checkout.session.completed', 'checkout.session.async_payment_succeeded', 'checkout.session.expired'}:
        return {'received': True}
    session = event['data']['object']
    reference = session.get('metadata', {}).get('pedido_id', '')
    if not str(reference).isdecimal():
        return {'received': True}
    pedido = db.query(Pedido).filter_by(id=int(reference)).with_for_update().first()
    if pedido is None or pedido.metodo_pago == MetodoPago.EFECTIVO:
        return {'received': True}
    try:
        aplicar_sesion(db, pedido, session)
        db.commit()
    except ValueError:
        db.rollback()
        raise HTTPException(400, 'El evento no corresponde al pago del pedido')
    return {'received': True}


@router.get('/pago/resultado')
def resultado_pago(request: Request, db: Session = Depends(get_db)):
    from app.routers.catalogo import pagina_publica
    pedido = consultar_pago(request, db)
    return pagina_publica(request, db, 'pago_resultado.html', {'pedido': pedido})


def consultar_pago(request, db):
    from app.routers.catalogo import comprador
    usuario = comprador(request, db)
    compra = request.session.get('compra_directa', {})
    pedido = db.query(Pedido).filter_by(codigo_pedido='DIS-' + compra.get('token', '')).first()
    if not pedido or pedido.usuario_id != (usuario.id if usuario else None):
        raise HTTPException(404, 'Pedido no encontrado en esta sesión')
    if pedido.stripe_session_id and not pedido.pago_completado and not pedido.reserva_liberada:
        try:
            session = cliente().v1.checkout.sessions.retrieve(pedido.stripe_session_id)
            session = session if isinstance(session, dict) else session.to_dict()
            pedido = db.query(Pedido).filter_by(id=pedido.id).populate_existing().with_for_update().one()
            aplicar_sesion(db, pedido, session)
            db.commit()
        except (stripe.StripeError, HTTPException, ValueError):
            db.rollback()
            # Conserva el estado pendiente si no se puede verificar Stripe.
    return pedido


@router.get('/api/pago/estado')
def estado_pago(request: Request, db: Session = Depends(get_db)):
    from fastapi.responses import JSONResponse
    pedido = consultar_pago(request, db)
    return JSONResponse({'completado': pedido.pago_completado, 'caducado': pedido.reserva_liberada},
                        headers={'Cache-Control': 'no-store'})
