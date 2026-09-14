"""Migraciones idempotentes para PostgreSQL."""
from pathlib import Path
from sqlalchemy import inspect


def ejecutar(engine, filename):
    sql = (Path(__file__).resolve().parents[1] / 'migrations' / filename).read_text(encoding='utf-8-sig')
    sql = '\n'.join(line for line in sql.splitlines() if not line.strip().startswith('--'))
    with engine.begin() as connection:
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement and statement not in {'BEGIN', 'COMMIT'}:
                connection.exec_driver_sql(statement)


def actualizar_cesta(engine):
    if engine.dialect.name == 'postgresql':
        ejecutar(engine, '20260914_cesta.sql')


def actualizar_pedidos(engine):
    if engine.dialect.name != 'postgresql':
        return
    columns = {column['name']: column for column in inspect(engine).get_columns('pedidos')}
    expected = {'descuento', 'nombre_comprador', 'apellidos_comprador', 'email_comprador', 'moneda', 'pago_completado'}
    if not (expected <= columns.keys() and columns['usuario_id']['nullable'] and str(columns['total']['type']).startswith('NUMERIC')):
        ejecutar(engine, '20260914_compra_directa.sql')
    if not {'stripe_session_id', 'reserva_expira', 'reserva_liberada'} <= columns.keys():
        ejecutar(engine, '20260914_stripe.sql')
