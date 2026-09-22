"""Compra directa RF19–RF23. El carrito no participa en este flujo."""
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field, StrictInt, field_validator
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EstadoPedido, MetodoPago, Pedido, Producto, ProductoPedido
from app.routers.auth import _validar_csrf

router = APIRouter(tags=["compra"])
CENTIMO = Decimal("0.01")


def dinero(value):
    return Decimal(str(value)).quantize(CENTIMO, rounding=ROUND_HALF_UP)


def importes(producto, cantidad):
    tasa = Decimal(os.getenv("CHECKOUT_IVA", "0.21"))
    envio = dinero(os.getenv("CHECKOUT_ENVIO", "0"))
    if not tasa.is_finite() or tasa < 0 or not envio.is_finite() or envio < 0:
        raise RuntimeError("Configuración de importes no válida")
    real = dinero(producto.precio)
    oferta = producto.precio_oferta
    unitario = dinero(oferta) if oferta is not None and 0 <= oferta < producto.precio else real
    subtotal = dinero(real * cantidad)
    descuento = dinero((real - unitario) * cantidad)
    impuesto = dinero((subtotal - descuento) * tasa)
    return dict(subtotal=subtotal, descuento=descuento, impuesto=impuesto,
                coste_entrega=envio, total=dinero(subtotal - descuento + impuesto + envio),
                precio_unitario=unitario, total_item=dinero(unitario * cantidad), iva=tasa * 100)


class Direccion(BaseModel):
    direccion: str = Field(min_length=1, max_length=250)
    ciudad: str = Field(min_length=1, max_length=100)
    codigo_postal: str = Field(min_length=1, max_length=20)

    @field_validator("*", mode="before")
    @classmethod
    def limpiar(cls, value):
        return value.strip() if isinstance(value, str) else value


class Compra(BaseModel):
    token: str = Field(min_length=20, max_length=100)
    nombre: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=150)
    email: EmailStr
    telefono: str = Field(min_length=5, max_length=30, pattern=r"^[+0-9 ()-]+$")
    envio: Direccion
    facturacion: Direccion
    metodo: Literal["inmediato", "contrarrembolso"]

    @field_validator("nombre", "apellidos", "email", "telefono", mode="before")
    @classmethod
    def limpiar(cls, value):
        return value.strip() if isinstance(value, str) else value


def preparar_items(db, cantidades):
    from app.routers.catalogo import obtener_producto, producto_publico
    if not cantidades:
        raise HTTPException(409, "El carrito est? vac?o")
    items = []
    for producto_id, cantidad in sorted(cantidades.items(), key=lambda pair: int(pair[0])):
        producto = obtener_producto(db, int(producto_id))
        if not producto.tienda.compra_online:
            raise HTTPException(409, "Esta tienda es solo un catálogo visual; no se puede comprar: " + producto.nombre)
        if not producto.disponible or producto.stock < cantidad:
            raise HTTPException(409, "Producto no disponible o cantidad superior al stock: " + producto.nombre)
        items.append(dict(producto=producto_publico(producto), cantidad=cantidad,
                          importes=importes(producto, cantidad)))
    resumen = {key: sum((item["importes"][key] for item in items), Decimal(0))
               for key in ("subtotal", "descuento", "impuesto")}
    resumen["coste_entrega"] = items[0]["importes"]["coste_entrega"]
    resumen["iva"] = items[0]["importes"]["iva"]
    resumen["total"] = dinero(resumen["subtotal"] - resumen["descuento"] + resumen["impuesto"] + resumen["coste_entrega"])
    return items, resumen


def huella(items, resumen):
    values = [[item["producto"]["id"], item["cantidad"],
               {k: str(v) for k, v in item["importes"].items()}] for item in items]
    return hashlib.sha256(json.dumps([values, {k: str(v) for k, v in resumen.items()}], sort_keys=True).encode()).hexdigest()


def abrir_compra(request, db, usuario, cantidades, origen):
    from app.routers.catalogo import pagina_publica
    items, resumen = preparar_items(db, cantidades)
    token = secrets.token_urlsafe(32)
    request.session["compra_directa"] = dict(token=token, cantidades=cantidades, origen=origen,
        usuario_id=usuario.id if usuario else None, huella=huella(items, resumen))
    return pagina_publica(request, db, "compra.html", dict(items_compra=items,
        resumen=resumen, comprador=usuario, token_compra=token))


class SeleccionCarrito(BaseModel):
    cantidades: dict[str, StrictInt] = Field(min_length=1, max_length=50)

    @field_validator("cantidades")
    @classmethod
    def validar(cls, value):
        if any(not key.isdecimal() or str(int(key)) != key or not 1 <= cantidad <= 999 for key, cantidad in value.items()):
            raise ValueError("Cantidades o productos no v?lidos")
        return value


@router.post("/api/compra/carrito")
def seleccionar_carrito(datos: SeleccionCarrito, request: Request, db: Session = Depends(get_db)):
    from app.routers.catalogo import comprador, cantidades_carrito
    _validar_csrf(request)
    usuario = comprador(request, db)
    if datos.cantidades != cantidades_carrito(request, db, usuario):
        raise HTTPException(409, "Pulsa «Actualizar» para guardar las cantidades antes de comprar.")
    preparar_items(db, datos.cantidades)
    request.session["seleccion_compra_carrito"] = datos.cantidades
    return {"url": "/compra/carrito"}


@router.get("/compra/carrito")
def pagina_compra_carrito(request: Request, db: Session = Depends(get_db)):
    from app.routers.catalogo import comprador, cantidades_carrito
    usuario = comprador(request, db)
    actuales = cantidades_carrito(request, db, usuario)
    seleccion = request.session.get("seleccion_compra_carrito")
    if seleccion is not None and seleccion != actuales:
        raise HTTPException(409, "El carrito ha cambiado. Vuelve al carrito para revisar los productos.")
    return abrir_compra(request, db, usuario, seleccion if seleccion is not None else actuales, "carrito")


@router.get("/compra/{producto_id}")
def pagina_compra(producto_id: int, request: Request, cantidad: int = Query(1, ge=1, le=999),
                  db: Session = Depends(get_db)):
    from app.routers.catalogo import comprador
    return abrir_compra(request, db, comprador(request, db), {str(producto_id): cantidad}, "directa")


@router.post("/api/compra")
def finalizar_compra(datos: Compra, request: Request, db: Session = Depends(get_db)):
    from app.routers.catalogo import comprador
    _validar_csrf(request)
    usuario = comprador(request, db)
    sesion = request.session.get("compra_directa")
    if not sesion or not secrets.compare_digest(sesion["token"], datos.token):
        raise HTTPException(409, "La compra ha caducado. Vuelve a seleccionar el producto.")
    if sesion["usuario_id"] != (usuario.id if usuario else None):
        raise HTTPException(409, "La sesión ha cambiado. Vuelve a iniciar la compra.")
    from app.stripe_payments import configuracion, abrir_pago
    if datos.metodo == "inmediato":
        configuracion()
    codigo = "DIS-" + datos.token
    pedido = db.query(Pedido).filter_by(codigo_pedido=codigo).with_for_update().first()
    if pedido is None:
        from app.routers.catalogo import obtener_carrito
        carrito = obtener_carrito(request, db, usuario) if sesion["origen"] == "carrito" else None
        items, resumen = preparar_items(db, sesion["cantidades"])
        if huella(items, resumen) != sesion["huella"]:
            raise HTTPException(409, "El precio ha cambiado. Recarga la compra para revisar el importe.")
        try:
            for item in items:
                reservado = db.execute(update(Producto).where(Producto.id == item["producto"]["id"],
                    Producto.disponible.is_(True), Producto.stock >= item["cantidad"]).values(stock=Producto.stock - item["cantidad"]))
                if reservado.rowcount != 1:
                    db.rollback()
                    raise HTTPException(409, "No hay stock suficiente para esta compra.")
            pedido = Pedido(codigo_pedido=codigo, usuario_id=usuario.id if usuario else None,
                carrito_id=carrito.id if carrito else None,
                nombre_comprador=datos.nombre, apellidos_comprador=datos.apellidos, email_comprador=str(datos.email),
                telefono=datos.telefono, direccion_envio=json.dumps(datos.envio.model_dump(), ensure_ascii=False),
                direccion_facturacion=json.dumps(datos.facturacion.model_dump(), ensure_ascii=False),
                metodo_pago=MetodoPago.EFECTIVO if datos.metodo == "contrarrembolso" else MetodoPago.TARJETA_CREDITO,
                estado=EstadoPedido.PREPARACION, moneda="EUR", pago_completado=False,
                importe_pago_original=resumen["total"],
                reserva_expira=datetime.utcnow() + timedelta(minutes=31) if datos.metodo == "inmediato" else None,
                **{k: resumen[k] for k in ("subtotal", "descuento", "impuesto", "coste_entrega", "total")})
            for item in items:
                pedido.items.append(ProductoPedido(producto_id=item["producto"]["id"], cantidad=item["cantidad"],
                    precio_unitario=item["importes"]["precio_unitario"], total=item["importes"]["total_item"]))
            db.add(pedido)
            from app.estado_pedidos import sincronizar_subpedidos
            sincronizar_subpedidos(db, pedido)
            db.commit()  # RI03: pedido persistido antes de llamar al pago.
        except IntegrityError:
            db.rollback()
            pedido = db.query(Pedido).filter_by(codigo_pedido=codigo).one()
    checkout_url = None
    if pedido.metodo_pago != MetodoPago.EFECTIVO:
        checkout_url = abrir_pago(db, pedido)
    elif pedido.estado == EstadoPedido.PREPARACION:
        from app.stripe_payments import vaciar_carrito_pedido
        pedido.estado = EstadoPedido.PREPARACION
        vaciar_carrito_pedido(db, pedido)
        db.commit()
    return dict(codigo=pedido.codigo_pedido, estado=pedido.estado.value,
                pago_completado=pedido.pago_completado, total=f"{pedido.total:.2f}", moneda="EUR", checkout_url=checkout_url,
                carrito_vaciado=pedido.carrito_vaciado)
