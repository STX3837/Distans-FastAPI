"""Reconcilia reservas periódicamente sin bloquear el servidor ASGI."""
import asyncio
import logging
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Carrito
from app.stripe_payments import reconciliar_reservas

logger = logging.getLogger(__name__)


def eliminar_carritos_inactivos(db, ahora=None):
    limite = (ahora or datetime.utcnow()) - timedelta(hours=1)
    # El bloqueo se obtiene en la misma consulta que comprueba la antigüedad.
    # PostgreSQL vuelve a evaluar el predicado tras esperar por una actualización
    # concurrente; skip_locked evita que varios workers limpien el mismo carrito.
    carritos = db.query(Carrito).filter(Carrito.fecha_actualizacion < limite).with_for_update(
        skip_locked=True,
    ).all()
    for carrito in carritos:
        db.delete(carrito)
    db.commit()
    return len(carritos)


def ejecutar_reconciliacion():
    with SessionLocal() as db:
        reconciliar_reservas(db)
        eliminar_carritos_inactivos(db)


async def vigilar_reservas():
    while True:
        try:
            await asyncio.to_thread(ejecutar_reconciliacion)
        except Exception:
            logger.warning('No se pudo reconciliar las reservas de pago')
        await asyncio.sleep(60)
