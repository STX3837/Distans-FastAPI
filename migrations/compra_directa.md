La compra directa se abre desde «Comprar ya» con un único producto y la cantidad elegida; el carrito conserva sus artículos.

El proceso pregunta datos del comprador y direcciones de envío y facturación antes de permitir revisar y confirmar el pago. Los datos de la cuenta se usan como valores iniciales, y el pedido conserva una copia de los datos indicados en la compra.

Importes: subtotal a precio original − descuento + impuesto + envío = total, siempre en EUR. Los precios del catálogo se interpretan como precios antes de impuestos. CHECKOUT_IVA configura la tasa decimal (por defecto 0.21) y CHECKOUT_ENVIO el coste en euros (por defecto 0). Los cálculos usan Decimal con redondeo a céntimos; los importes del pedido se guardan como NUMERIC(12,2).

El pedido y sus líneas se guardan con estado pendiente y se reserva el stock antes de llamar a procesar_pago_simulado, que siempre devuelve True. El pago inmediato confirma el pedido y marca pago_completado=True. El contrarrembolso confirma el pedido y conserva pago_completado=False hasta el cobro en la entrega. No se piden datos bancarios y la interfaz identifica el pago como simulado.

La confirmación usa un código único por intento de compra para evitar pedidos duplicados en reintentos. El servidor valida CSRF, rol, identidad de sesión, stock e importes. Los datos personales del formulario no se almacenan en la cookie de sesión. En producción se debe servir la aplicación por HTTPS; el middleware existente configura las cookies de sesión como Secure en ese entorno.

Al iniciar la aplicación se aplica automáticamente la actualización idempotente del esquema PostgreSQL definida en migrations/20260914_compra_directa.sql. También se puede ejecutar ese archivo antes del despliegue. No se ha ejecutado contra una base PostgreSQL real durante las pruebas locales.
