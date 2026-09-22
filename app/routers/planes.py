"""Planes de vendedores y pago de una mensualidad Premium."""
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PagoPlan, RolUsuario, Tienda
from app.routers.auth import _validar_csrf
from app.routers.catalogo import pagina_publica
from app.routers.users import _obtener_usuario_actual
from app.plan_payments import aplicar_pago_plan, iniciar_pago_plan
from app.stripe_payments import cliente

router = APIRouter(tags=['planes'])


def vendedor_y_tienda(request, db):
    vendedor = _obtener_usuario_actual(request, db)
    if vendedor.rol != RolUsuario.VENDEDOR:
        raise HTTPException(403, 'Acceso exclusivo para vendedores')
    tienda = db.query(Tienda).filter_by(vendedor_id=vendedor.id).first()
    return vendedor, tienda


def pagina_plan(request, db, resultado=False):
    vendedor, tienda = vendedor_y_tienda(request, db)
    pago = (db.query(PagoPlan).filter_by(tienda_id=tienda.id).order_by(PagoPlan.id.desc()).first()
            if tienda else None)
    if resultado and pago and pago.estado == 'pendiente' and pago.stripe_session_id:
        try:
            sesion = cliente().v1.checkout.sessions.retrieve(pago.stripe_session_id)
            sesion = sesion if isinstance(sesion, dict) else sesion.to_dict()
            pago = db.query(PagoPlan).filter_by(id=pago.id).with_for_update().one()
            aplicar_pago_plan(db, pago, sesion)
            db.commit()
        except (stripe.StripeError, ValueError):
            db.rollback()
    return pagina_publica(request, db, 'planes.html', {
        'tienda_activa': tienda.id if tienda else None, 'tienda_plan': tienda,
        'pago_plan': pago, 'resultado_plan': resultado,
    })


@router.get('/gestion/plan')
def mostrar_planes(request: Request, db: Session = Depends(get_db)):
    return pagina_plan(request, db)


@router.get('/gestion/plan/resultado')
def resultado_plan(request: Request, db: Session = Depends(get_db)):
    return pagina_plan(request, db, resultado=True)


@router.post('/api/gestion/plan/pagar')
def pagar_plan(request: Request, db: Session = Depends(get_db)):
    _validar_csrf(request)
    vendedor, tienda = vendedor_y_tienda(request, db)
    if tienda is None:
        raise HTTPException(409, 'Registra una tienda antes de contratar Premium')
    return {'url': iniciar_pago_plan(db, tienda, vendedor)}
