"""Migraciones idempotentes para PostgreSQL."""
from pathlib import Path
from sqlalchemy import inspect, text


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


def actualizar_filtros(engine):
    if engine.dialect.name != 'postgresql':
        return
    with engine.begin() as connection:
        for table, columns in {
            'tiendas': {'valoracion_media': 'DOUBLE PRECISION'},
            'productos': {'valoracion_media': 'DOUBLE PRECISION', 'modalidad_compra': "VARCHAR(10) NOT NULL DEFAULT 'presencial'"},
        }.items():
            for name, definition in columns.items():
                connection.exec_driver_sql(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {definition}')
        connection.exec_driver_sql(
            'UPDATE productos SET valoracion_media = NULL WHERE NOT EXISTS '
            '(SELECT 1 FROM valoraciones_productos WHERE valoraciones_productos.producto_id = productos.id)'
        )
        connection.exec_driver_sql(
            'UPDATE tiendas SET valoracion_media = NULL WHERE NOT EXISTS '
            '(SELECT 1 FROM valoraciones_tiendas WHERE valoraciones_tiendas.tienda_id = tiendas.id)'
        )


def actualizar_pedidos(engine):
    if engine.dialect.name != 'postgresql':
        return
    columns = {column['name']: column for column in inspect(engine).get_columns('pedidos')}
    expected = {'descuento', 'nombre_comprador', 'apellidos_comprador', 'email_comprador', 'moneda', 'pago_completado'}
    if not (expected <= columns.keys() and columns['usuario_id']['nullable'] and str(columns['total']['type']).startswith('NUMERIC')):
        ejecutar(engine, '20260914_compra_directa.sql')
    if not {'stripe_session_id', 'reserva_expira', 'reserva_liberada'} <= columns.keys():
        ejecutar(engine, '20260914_stripe.sql')
    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TYPE estadopedido ADD VALUE IF NOT EXISTS 'PREPARACION'")
    with engine.begin() as connection:
        connection.exec_driver_sql("UPDATE pedidos SET estado = 'PREPARACION' WHERE estado::text IN ('PENDIENTE', 'CONFIRMADO')")
        connection.exec_driver_sql("UPDATE pedidos SET estado = 'CANCELADO' WHERE estado::text = 'DEVUELTO'")
        connection.exec_driver_sql("ALTER TABLE productos_pedido ADD COLUMN IF NOT EXISTS subpedido_id INTEGER")
        connection.exec_driver_sql("ALTER TABLE productos_pedido ADD COLUMN IF NOT EXISTS cancelado BOOLEAN NOT NULL DEFAULT FALSE")
        connection.exec_driver_sql("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS importe_pago_original NUMERIC(12,2)")
        connection.exec_driver_sql("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS reembolso_pendiente NUMERIC(12,2) NOT NULL DEFAULT 0")
        connection.exec_driver_sql("UPDATE pedidos SET importe_pago_original = total WHERE importe_pago_original IS NULL")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_productos_pedido_subpedido_id ON productos_pedido (subpedido_id)")
        nuevos = connection.exec_driver_sql("""
            INSERT INTO subpedidos (pedido_id, tienda_id, estado, fecha_actualizacion)
            SELECT DISTINCT p.id, pr.tienda_id,
                CASE WHEN p.estado::text = 'CANCELADO' THEN 'CANCELADO'::estadosubpedido
                     WHEN p.estado::text IN ('ENVIADO', 'ENTREGADO') THEN 'RECOGIDO'::estadosubpedido
                     ELSE 'PREPARACION'::estadosubpedido END, CURRENT_TIMESTAMP
            FROM pedidos p JOIN productos_pedido pp ON pp.pedido_id = p.id
            JOIN productos pr ON pr.id = pp.producto_id
            ON CONFLICT (pedido_id, tienda_id) DO NOTHING
            RETURNING id
        """).scalars().all()
        if inspect(connection).has_table('estados_pedido_tienda'):
            for subpedido_id in nuevos:
                connection.execute(text("""
                    UPDATE subpedidos s SET estado = CASE
                    WHEN antiguo.estado::text = 'CANCELADO' THEN 'CANCELADO'::estadosubpedido
                    WHEN antiguo.estado::text IN ('ENVIADO', 'ENTREGADO') THEN 'RECOGIDO'::estadosubpedido
                    ELSE 'PREPARACION'::estadosubpedido END
                    FROM estados_pedido_tienda antiguo
                    WHERE antiguo.pedido_id = s.pedido_id AND antiguo.tienda_id = s.tienda_id
                    AND s.id = :subpedido_id
                """), {"subpedido_id": subpedido_id})
        connection.exec_driver_sql("""
            UPDATE productos_pedido pp SET subpedido_id = s.id
            FROM subpedidos s JOIN productos pr ON pr.tienda_id = s.tienda_id
            WHERE pp.pedido_id = s.pedido_id AND pp.producto_id = pr.id AND pp.subpedido_id IS NULL
        """)
        connection.exec_driver_sql("ALTER TABLE productos_pedido ALTER COLUMN subpedido_id SET NOT NULL")
        connection.exec_driver_sql("""
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_productos_pedido_subpedido') THEN
                ALTER TABLE productos_pedido ADD CONSTRAINT fk_productos_pedido_subpedido
                FOREIGN KEY (subpedido_id) REFERENCES subpedidos(id);
              END IF;
            END $$
        """)
