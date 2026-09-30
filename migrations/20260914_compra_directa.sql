-- Ejecutar una vez sobre la base PostgreSQL existente antes de desplegar el checkout.
BEGIN;
ALTER TABLE pedidos ALTER COLUMN usuario_id DROP NOT NULL;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS descuento NUMERIC(12,2) NOT NULL DEFAULT 0;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS nombre_comprador VARCHAR NOT NULL DEFAULT '';
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS apellidos_comprador VARCHAR NOT NULL DEFAULT '';
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS email_comprador VARCHAR NOT NULL DEFAULT '';
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS moneda VARCHAR(3) NOT NULL DEFAULT 'EUR';
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS pago_completado BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE pedidos ALTER COLUMN subtotal TYPE NUMERIC(12,2) USING round(subtotal::numeric,2);
ALTER TABLE pedidos ALTER COLUMN impuesto TYPE NUMERIC(12,2) USING round(impuesto::numeric,2);
ALTER TABLE pedidos ALTER COLUMN coste_entrega TYPE NUMERIC(12,2) USING round(coste_entrega::numeric,2);
ALTER TABLE pedidos ALTER COLUMN total TYPE NUMERIC(12,2) USING round(total::numeric,2);
ALTER TABLE productos_pedido ALTER COLUMN precio_unitario TYPE NUMERIC(12,2) USING round(precio_unitario::numeric,2);
ALTER TABLE productos_pedido ALTER COLUMN total TYPE NUMERIC(12,2) USING round(total::numeric,2);
COMMIT;
