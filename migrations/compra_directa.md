La compra directa y la compra del carrito usan ahora Stripe Checkout. Consulta la sección «Pagos con Stripe» de README.md para configurar las claves, el webhook y las pruebas.

El formulario local reúne datos y direcciones en el primer paso; el segundo muestra la revisión y el tercero es el pago alojado en Stripe. El contrarrembolso conserva el pago pendiente.

Los pedidos se guardan y el stock se reserva antes de abrir Stripe. La firma del webhook y las referencias e importes se verifican antes de marcar el pedido pagado. Las reservas vencidas se liberan al verificar su caducidad en Stripe, mediante webhook o reconciliación periódica. No se solicitan ni guardan datos de tarjeta en Distans.

Los importes se calculan en Decimal y se guardan en NUMERIC(12,2), en EUR. Los precios del catálogo se interpretan antes de impuestos: subtotal − descuento + impuesto + envío = total. CHECKOUT_IVA configura el impuesto (0.21 por defecto) y CHECKOUT_ENVIO el coste de entrega (0 por defecto).

Las migraciones de pedidos y Stripe se aplican automáticamente al arrancar PostgreSQL. Las pruebas automatizadas usan SQLite y un cliente Stripe simulado; falta validar con una cuenta Stripe de prueba y una base PostgreSQL real.
