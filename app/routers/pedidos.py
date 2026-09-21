"""Seguimiento, historial y subpedidos de cada tienda."""
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.estado_pedidos import cancelar_subpedido, recalcular_estado
from app.models import EstadoPedido, EstadoSubpedido, Pedido, ProductoPedido, RolUsuario, Subpedido, Tienda, Usuario
from app.routers.auth import _validar_csrf
from app.routers.catalogo import pagina_publica
from app.routers.users import _obtener_usuario_actual

router = APIRouter(tags=["pedidos"])


@router.get("/pedidos/seguimiento")
def seguimiento(request: Request, codigo: str = Query("", max_length=100), db: Session = Depends(get_db)):
    pedido = None
    if codigo.strip():
        pedido = db.query(Pedido).options(joinedload(Pedido.items).joinedload(ProductoPedido.producto)).filter(
            Pedido.codigo_pedido == codigo.strip()).first()
    return pagina_publica(request, db, "seguimiento.html", {"pedido": pedido, "codigo": codigo.strip()})


@router.get("/pedidos/historial")
def historial(request: Request, db: Session = Depends(get_db)):
    usuario = _obtener_usuario_actual(request, db)
    if usuario.rol != RolUsuario.COMPRADOR:
        raise HTTPException(403, "Acceso exclusivo para compradores")
    pedidos = db.query(Pedido).filter(Pedido.usuario_id == usuario.id).order_by(Pedido.fecha.desc(), Pedido.id.desc()).all()
    return pagina_publica(request, db, "historial_pedidos.html", {"pedidos": pedidos})


def tienda_del_vendedor(request, db, tienda_id):
    usuario = _obtener_usuario_actual(request, db)
    if usuario.rol not in {RolUsuario.VENDEDOR, RolUsuario.ADMIN}:
        raise HTTPException(403, "Acceso exclusivo para vendedores")
    query = db.query(Tienda).filter(Tienda.id == tienda_id)
    if usuario.rol != RolUsuario.ADMIN:
        query = query.filter(Tienda.vendedor_id == usuario.id)
    tienda = query.first()
    if tienda is None:
        raise HTTPException(404, "Tienda no encontrada")
    return tienda


@router.get("/gestion/tiendas/{tienda_id}/pedidos")
def pedidos_tienda(tienda_id: int, request: Request, q: str = Query("", max_length=100),
                   comprador: str = Query("", max_length=200), db: Session = Depends(get_db)):
    tienda = tienda_del_vendedor(request, db, tienda_id)
    query = db.query(Subpedido).join(Pedido).outerjoin(Usuario, Pedido.usuario_id == Usuario.id).filter(Subpedido.tienda_id == tienda.id)
    if q.strip():
        query = query.filter(Pedido.codigo_pedido.icontains(q.strip(), autoescape=True))
    if comprador.strip():
        nombre = comprador.strip()
        query = query.filter(or_(
            (Pedido.nombre_comprador + " " + Pedido.apellidos_comprador).icontains(nombre, autoescape=True),
            (Usuario.nombre + " " + Usuario.apellidos).icontains(nombre, autoescape=True),
        ))
    subpedidos = query.options(joinedload(Subpedido.pedido).joinedload(Pedido.usuario),
        joinedload(Subpedido.items).joinedload(ProductoPedido.producto)).order_by(Pedido.fecha.desc()).all()
    pedidos = []
    for sub in subpedidos:
        pedido = sub.pedido
        pedidos.append({"id": pedido.id, "codigo": pedido.codigo_pedido, "fecha": pedido.fecha,
            "estado": pedido.estado, "estado_tienda": sub.estado, "usuario_id": pedido.usuario_id,
            "pago_pendiente": pedido.metodo_pago.value != "efectivo" and not pedido.pago_completado,
            "comprador": (pedido.nombre_comprador + " " + pedido.apellidos_comprador).strip() or
                ((pedido.usuario.nombre + " " + pedido.usuario.apellidos) if pedido.usuario else pedido.email_comprador),
            "total_tienda": sum(linea.total for linea in sub.items if not linea.cancelado), "lineas": sub.items})
    return pagina_publica(request, db, "pedidos_tienda.html", {"tienda_activa": tienda.id,
        "tienda_gestion": tienda, "pedidos": pedidos, "q": q, "comprador_filtro": comprador,
        "estados": [EstadoSubpedido.PREPARACION, EstadoSubpedido.LISTO_PARA_RECOGER, EstadoSubpedido.RECOGIDO]})


def pedido_y_subpedido(db, pedido_id, tienda_id):
    pedido = db.query(Pedido).filter_by(id=pedido_id).with_for_update().first()
    sub = db.query(Subpedido).filter_by(pedido_id=pedido_id, tienda_id=tienda_id).first()
    if pedido is None or sub is None:
        raise HTTPException(404, "Subpedido no encontrado")
    return pedido, sub


@router.post("/gestion/tiendas/{tienda_id}/pedidos/{pedido_id}/estado")
def cambiar_estado(tienda_id: int, pedido_id: int, request: Request, estado: EstadoSubpedido = Form(...),
                   csrf_token: str = Form(...), db: Session = Depends(get_db)):
    tienda_del_vendedor(request, db, tienda_id)
    _validar_csrf(request, csrf_token)
    pedido, sub = pedido_y_subpedido(db, pedido_id, tienda_id)
    if pedido.metodo_pago.value != "efectivo" and not pedido.pago_completado:
        raise HTTPException(409, "No se puede modificar un pedido pendiente de pago")
    if estado == EstadoSubpedido.CANCELADO:
        raise HTTPException(422, "Usa la acción de cancelar subpedido")
    if pedido.estado in {EstadoPedido.CANCELADO, EstadoPedido.ENTREGADO} or sub.estado == EstadoSubpedido.CANCELADO:
        raise HTTPException(409, "El pedido ya está finalizado")
    sub.estado = estado
    recalcular_estado(pedido)
    db.commit()
    return RedirectResponse(f"/gestion/tiendas/{tienda_id}/pedidos", status_code=303)


@router.post("/gestion/tiendas/{tienda_id}/pedidos/{pedido_id}/cancelar")
def cancelar(tienda_id: int, pedido_id: int, request: Request, csrf_token: str = Form(...),
             db: Session = Depends(get_db)):
    tienda_del_vendedor(request, db, tienda_id)
    _validar_csrf(request, csrf_token)
    pedido, sub = pedido_y_subpedido(db, pedido_id, tienda_id)
    if pedido.estado in {EstadoPedido.ENTREGADO, EstadoPedido.CANCELADO} or sub.estado in {EstadoSubpedido.RECOGIDO, EstadoSubpedido.CANCELADO}:
        raise HTTPException(409, "Este subpedido ya no se puede cancelar")
    if pedido.metodo_pago.value != "efectivo" and not pedido.pago_completado:
        raise HTTPException(409, "Espera a la confirmación del pago")
    cancelar_subpedido(db, pedido, sub)
    db.commit()
    return RedirectResponse(f"/gestion/tiendas/{tienda_id}/pedidos", status_code=303)
