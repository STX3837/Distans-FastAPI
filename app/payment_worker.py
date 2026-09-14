"""Reconcilia reservas periódicamente sin bloquear el servidor ASGI."""
import asyncio
import logging
from app.database import SessionLocal
from app.stripe_payments import reconciliar_reservas

logger = logging.getLogger(__name__)


def ejecutar_reconciliacion():
    with SessionLocal() as db:
        reconciliar_reservas(db)


async def vigilar_reservas():
    while True:
        try:
            await asyncio.to_thread(ejecutar_reconciliacion)
        except Exception:
            logger.warning('No se pudo reconciliar las reservas de pago')
        await asyncio.sleep(60)
