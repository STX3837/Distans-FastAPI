from datetime import datetime, timedelta

from app.models import Carrito
from app.payment_worker import eliminar_carritos_inactivos


def test_elimina_solo_carritos_inactivos_durante_una_hora(db_session):
    ahora = datetime.utcnow()
    antiguo = Carrito(sesion='antiguo', fecha_actualizacion=ahora - timedelta(hours=1, seconds=1))
    reciente = Carrito(sesion='reciente', fecha_actualizacion=ahora - timedelta(minutes=59))
    db_session.add_all([antiguo, reciente]); db_session.commit()
    assert eliminar_carritos_inactivos(db_session, ahora) == 1
    assert db_session.query(Carrito.sesion).all() == [('reciente',)]
