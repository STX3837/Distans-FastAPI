"""Cobro único de 14,99 € por un mes natural de Premium."""
import calendar
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.models import PagoPlan, Tienda
from app.stripe_payments import cliente, configuracion


IMPORTE_CENTIMOS = 1499


def un_mes_despues(fecha):
    mes = fecha.month + 1
    anio = fecha.year + (mes > 12)
    mes = (mes - 1) % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return fecha.replace(year=anio, month=mes, day=dia)


def aplicar_pago_plan(db, pago, sesion):
    """Solo una sesión de Stripe pagada y con importe exacto activa el plan."""
    if (sesion.get('client_reference_id') != str(pago.id) or
        sesion.get('metadata', {}).get('pago_plan_id') != str(pago.id) or
        sesion.get('metadata', {}).get('tienda_id') != str(pago.tienda_id) or
        sesion.get('mode') != 'payment' or sesion.get('currency') != 'eur' or
        sesion.get('amount_total') != IMPORTE_CENTIMOS or
        (pago.stripe_session_id and sesion.get('id') != pago.stripe_session_id)):
        raise ValueError('La sesión no corresponde al pago del plan')
    pago.stripe_session_id = sesion['id']
    if pago.estado == 'pagado':
        return
    if sesion.get('status') == 'expired':
        pago.estado = 'caducado'
        return
    if sesion.get('status') != 'complete' or sesion.get('payment_status') != 'paid':
        return
    tienda = db.query(Tienda).filter_by(id=pago.tienda_id).with_for_update().one()
    inicio = datetime.utcnow()
    # Un pago posterior añade un mes a la vigencia que aún quede.
    if tienda.plan_efectivo == 'Premium' and tienda.fecha_renovacion_plan:
        inicio = max(inicio, tienda.fecha_renovacion_plan)
    fin = un_mes_despues(inicio)
    era_premium = tienda.plan_efectivo == 'Premium'
    tienda.plan = 'Premium'
    tienda.suscripcion_activa = True
    tienda.pasarela_activa = True
    if not era_premium or tienda.fecha_alta_plan is None:
        tienda.fecha_alta_plan = datetime.utcnow()
    tienda.fecha_renovacion_plan = fin
    pago.estado = 'pagado'
    pago.fecha_pago = datetime.utcnow()
    pago.fecha_fin = fin


def iniciar_pago_plan(db, tienda, vendedor):
    """Reutiliza un intento pendiente con clave idempotente de Stripe."""
    import stripe

    _, _, base = configuracion()
    tienda = db.query(Tienda).filter_by(id=tienda.id, vendedor_id=vendedor.id).with_for_update().one()
    if tienda.plan_efectivo == 'Premium':
        raise HTTPException(409, 'La tienda ya tiene Premium activo')
    pago = db.query(PagoPlan).filter_by(tienda_id=tienda.id, estado='pendiente').order_by(PagoPlan.id.desc()).first()
    if pago is None:
        pago = PagoPlan(tienda_id=tienda.id, vendedor_id=vendedor.id, importe_centimos=IMPORTE_CENTIMOS)
        db.add(pago)
        db.flush()
    db.commit()
    try:
        if pago.stripe_session_id:
            sesion = cliente().v1.checkout.sessions.retrieve(pago.stripe_session_id)
        else:
            sesion = cliente().v1.checkout.sessions.create({
                'mode': 'payment', 'payment_method_types': ['card'], 'locale': 'es',
                'line_items': [{'price_data': {'currency': 'eur', 'unit_amount': IMPORTE_CENTIMOS,
                    'product_data': {'name': 'Distans Premium - un mes'}}, 'quantity': 1}],
                'customer_email': vendedor.email,
                'client_reference_id': str(pago.id),
                'metadata': {'pago_plan_id': str(pago.id), 'tienda_id': str(tienda.id)},
                'success_url': base + '/gestion/plan/resultado',
                'cancel_url': base + '/gestion/plan?cancelado=1',
                'expires_at': int((datetime.now(timezone.utc) + timedelta(minutes=31)).timestamp()),
            }, options={'idempotency_key': 'plan-' + str(pago.id)})
        sesion = sesion if isinstance(sesion, dict) else sesion.to_dict()
        pago = db.query(PagoPlan).filter_by(id=pago.id).with_for_update().one()
        aplicar_pago_plan(db, pago, sesion)
        db.commit()
    except (stripe.StripeError, ValueError, KeyError):
        db.rollback()
        raise HTTPException(502, 'No se pudo iniciar el pago. Inténtalo de nuevo.')
    if pago.estado == 'caducado':
        return iniciar_pago_plan(db, tienda, vendedor)
    if pago.estado == 'pagado':
        return base + '/gestion/plan/resultado'
    if not sesion.get('url'):
        raise HTTPException(502, 'Stripe no ha proporcionado la página de pago.')
    return sesion['url']
