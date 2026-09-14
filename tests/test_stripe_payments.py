import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
import stripe
from app.models import EstadoPedido, Pedido
from app import stripe_payments
from test_compra_directa import product, start, submit

pytestmark = pytest.mark.usefixtures('stripe_gateway')


@pytest.mark.parametrize('registered', [False, True])
@pytest.mark.parametrize('confirmation', ['webhook', 'return', 'cash', 'expired'])
def test_cart_cleared_only_when_order_confirmed(client, db_session, product, stripe_gateway, user_factory, registered, confirmation):
    import re
    if registered:
        buyer = user_factory(email='cart-payment-buyer@example.com')
        client.post('/api/login', json={'email': buyer.email, 'contrasena': 'clave12345'})
    payload = start(client, product)
    headers = {'X-CSRF-Token': client.cookies.get('csrf_token')}
    assert client.post(f'/api/carrito/productos/{product.id}', json={'cantidad': 2}, headers=headers).status_code == 200
    page = client.get('/compra/carrito')
    payload['token'] = re.search(r'data-token="([^"]+)"', page.text)[1]
    if confirmation == 'cash':
        payload['metodo'] = 'contrarrembolso'
    response = submit(client, payload)
    assert response.status_code == 200
    if confirmation != 'cash':
        assert response.json()['checkout_url'].startswith('https://checkout.stripe.com/')
        assert client.get('/api/carrito').json()['cantidad'] == 2
        session = next(iter(stripe_gateway.sessions.values()))
        if confirmation == 'expired':
            session.update(status='expired')
            assert event(client, session, 'checkout.session.expired').status_code == 200
            assert client.get('/api/carrito').json()['cantidad'] == 2
            return
        session.update(status='complete', payment_status='paid')
        if confirmation == 'webhook':
            assert event(client, session).status_code == 200
        else:
            assert client.get('/pago/resultado').status_code == 200
    assert client.get('/api/carrito').json()['cantidad'] == 0
    assert db_session.query(Pedido).one().carrito_vaciado
    # Una notificación duplicada no elimina productos añadidos después de comprar.
    assert client.post(f'/api/carrito/productos/{product.id}', json={'cantidad': 1}, headers=headers).status_code == 200
    if confirmation == 'webhook':
        assert event(client, session).status_code == 200
    else:
        assert submit(client, payload).status_code == 200
    assert client.get('/api/carrito').json()['cantidad'] == 1


def event(client, session, event_type='checkout.session.completed', valid=True):
    payload = json.dumps({'id': 'evt_test', 'object': 'event', 'type': event_type, 'data': {'object': session}})
    stamp = int(time.time())
    signature = hmac.new(b'whsec_test', f'{stamp}.{payload}'.encode(), hashlib.sha256).hexdigest()
    if not valid: signature = 'wrong'
    return client.post('/api/stripe/webhook', content=payload,
        headers={'Stripe-Signature': f't={stamp},v1={signature}', 'Content-Type': 'application/json'})


def test_stripe_pending_until_signed_webhook(client, db_session, product, stripe_gateway):
    payload = start(client, product)
    response = submit(client, payload)
    assert response.status_code == 200
    assert response.json()['checkout_url'].startswith('https://checkout.stripe.com/')
    order = db_session.query(Pedido).one()
    assert order.estado == EstadoPedido.PENDIENTE and not order.pago_completado
    assert order.stripe_session_id
    assert order.reserva_expira > datetime.utcnow()
    assert len(stripe_gateway.creations) == 1
    assert submit(client, payload).status_code == 200
    assert len(stripe_gateway.creations) == 1
    assert 'Pago pendiente' in client.get('/pago/resultado').text
    session = next(iter(stripe_gateway.sessions.values())).copy()
    session.update(status='complete', payment_status='paid')
    assert event(client, session, valid=False).status_code == 400
    db_session.refresh(order)
    assert not order.pago_completado
    assert event(client, session).status_code == 200
    assert event(client, session).status_code == 200
    db_session.refresh(order)
    db_session.refresh(product)
    assert order.pago_completado and order.estado == EstadoPedido.CONFIRMADO
    assert product.stock == 3
    assert 'Pago completado' in client.get('/pago/resultado').text
    params = stripe_gateway.creations[0]
    assert params['payment_method_types'] == ['card']
    assert params['metadata'] == {'pedido_id': str(order.id)}
    assert 'localhost:8000' in params['success_url']
    assert all(line['price_data']['currency'] == 'eur' for line in params['line_items'])


def test_expired_reservation_released_once(client, db_session, product, stripe_gateway):
    payload = start(client, product)
    submit(client, payload)
    session = next(iter(stripe_gateway.sessions.values())).copy()
    session['status'] = 'expired'
    assert event(client, session, 'checkout.session.expired').status_code == 200
    assert event(client, session, 'checkout.session.expired').status_code == 200
    db_session.refresh(product)
    order = db_session.query(Pedido).one()
    assert product.stock == 5 and order.reserva_liberada
    assert order.estado == EstadoPedido.CANCELADO
    assert submit(client, payload).status_code == 409


@pytest.mark.parametrize('field,value', [('amount_total', 1), ('currency', 'usd'), ('client_reference_id', '999')])
def test_mismatched_webhook_cannot_complete(client, db_session, product, stripe_gateway, field, value):
    submit(client, start(client, product))
    session = next(iter(stripe_gateway.sessions.values())).copy()
    session.update(status='complete', payment_status='paid')
    session[field] = value
    assert event(client, session).status_code == 400
    assert not db_session.query(Pedido).one().pago_completado


def test_network_failure_preserves_stock_and_retry(client, db_session, product, stripe_gateway, monkeypatch):
    create = stripe_gateway.api.create
    def lost_response(*args, **kwargs):
        create(*args, **kwargs)
        raise stripe.APIConnectionError('secret details must not leak')
    monkeypatch.setattr(stripe_gateway.api, 'create', lost_response)
    payload = start(client, product)
    response = submit(client, payload)
    assert response.status_code == 502 and 'secret details' not in response.text
    db_session.refresh(product)
    assert product.stock == 3 and db_session.query(Pedido).count() == 1
    monkeypatch.setattr(stripe_gateway.api, 'create', create)
    assert submit(client, payload).status_code == 200
    assert len(stripe_gateway.creations) == 1


def test_reconciliation_checks_stripe_before_release(client, db_session, product, stripe_gateway):
    submit(client, start(client, product))
    order = db_session.query(Pedido).one()
    order.reserva_expira = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    stripe_payments.reconciliar_reservas(db_session)
    stripe_payments.reconciliar_reservas(db_session)
    db_session.refresh(product)
    assert product.stock == 5
    assert db_session.query(Pedido).one().reserva_liberada


def test_missing_configuration_does_not_reserve(client, db_session, product, monkeypatch):
    payload = start(client, product)
    monkeypatch.delenv('STRIPE_SECRET_KEY')
    assert submit(client, payload).status_code == 503
    assert db_session.query(Pedido).count() == 0
    db_session.refresh(product)
    assert product.stock == 5


def test_result_cannot_be_read_from_another_session(client, app, product):
    from fastapi.testclient import TestClient
    submit(client, start(client, product))
    with TestClient(app) as other:
        assert other.get('/pago/resultado').status_code == 404


def test_return_confirms_paid_session_without_webhook(client, db_session, product, stripe_gateway):
    submit(client, start(client, product))
    session = next(iter(stripe_gateway.sessions.values()))
    session.update(status='complete', payment_status='paid')
    response = client.get('/pago/resultado')
    assert response.status_code == 200 and 'Pago completado' in response.text
    order = db_session.query(Pedido).one()
    assert order.pago_completado and order.estado == EstadoPedido.CONFIRMADO
    assert client.get('/api/pago/estado').json() == {'completado': True, 'caducado': False}
    db_session.refresh(product)
    assert product.stock == 3


def test_poll_confirms_payment_and_network_failure_stays_pending(client, db_session, product, stripe_gateway, monkeypatch):
    submit(client, start(client, product))
    retrieve = stripe_gateway.api.retrieve
    def failure(*args):
        raise stripe.APIConnectionError('private error')
    monkeypatch.setattr(stripe_gateway.api, 'retrieve', failure)
    response = client.get('/pago/resultado')
    assert response.status_code == 200 and 'Pago pendiente' in response.text
    assert 'private error' not in response.text
    assert 'pago_resultado.js' in response.text
    monkeypatch.setattr(stripe_gateway.api, 'retrieve', retrieve)
    session = next(iter(stripe_gateway.sessions.values()))
    session.update(status='complete', payment_status='paid')
    assert client.get('/api/pago/estado').json()['completado']
    assert db_session.query(Pedido).one().pago_completado
