"""Actualización idempotente del esquema existente de pedidos."""
from pathlib import Path
from sqlalchemy import inspect


def actualizar_pedidos(engine):
    if engine.dialect.name != "postgresql":
        return
    columns = {column["name"]: column for column in inspect(engine).get_columns("pedidos")}
    expected = {"descuento", "nombre_comprador", "apellidos_comprador", "email_comprador", "moneda", "pago_completado"}
    if expected <= columns.keys() and columns["usuario_id"]["nullable"] and str(columns["total"]["type"]).startswith("NUMERIC"):
        return
    migration = Path(__file__).resolve().parents[1] / "migrations" / "20260914_compra_directa.sql"
    sql = migration.read_text(encoding="utf-8-sig")
    sql = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    with engine.begin() as connection:
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement and statement not in {"BEGIN", "COMMIT"}:
                connection.exec_driver_sql(statement)
