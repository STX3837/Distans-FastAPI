"""CRUD de pedidos reservado a administradores."""
from datetime import datetime
from math import ceil, isfinite

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import EstadoPedido, MetodoPago, Pedido, Producto, ProductoPedido, RolUsuario, Usuario
from app.routers.auth import _validar_csrf
from app.routers.users import _obtener_admin_actual
from app.routers.catalogo import pagina_publica

router = APIRouter(prefix="/admin/pedidos", tags=["administración de pedidos"])


class LineaDatos(BaseModel):
    producto_id: int = Field(ge=1)
    cantidad: int = Field(ge=1, le=1000000, strict=True)
    precio_unitario: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class PedidoDatos(BaseModel):
    codigo_pedido: str = Field(min_length=1, max_length=100)
    usuario_id: int = Field(ge=1)
    estado: EstadoPedido = EstadoPedido.PENDIENTE
    metodo_pago: MetodoPago = MetodoPago.EFECTIVO
    direccion_envio: str = Field(min_length=1, max_length=500)
    direccion_facturacion: str = Field(min_length=1, max_length=500)
    telefono: str = Field(default="", max_length=50)
    impuesto: float = Field(default=0, ge=0, allow_inf_nan=False)
    coste_entrega: float = Field(default=0, ge=0, allow_inf_nan=False)
    lineas: list[LineaDatos] = Field(min_length=1, max_length=100)

    @field_validator("codigo_pedido", "direccion_envio", "direccion_facturacion")
    @classmethod
    def requerido(cls, value):
        if not value.strip(): raise ValueError("Campo obligatorio")
        return value.strip()


def serializar(pedido):
    return {**{campo: getattr(pedido, campo) for campo in (
        "id", "codigo_pedido", "usuario_id", "fecha", "subtotal", "impuesto", "coste_entrega", "total",
        "direccion_envio", "direccion_facturacion", "telefono", "fecha_creacion", "fecha_actualizacion")},
        "estado": pedido.estado.value, "metodo_pago": pedido.metodo_pago.value,
        "comprador": {"nombre": pedido.usuario.nombre, "email": pedido.usuario.email},
        "lineas": [{"id": linea.id, "producto_id": linea.producto_id, "nombre": linea.producto.nombre,
                    "tienda_id": linea.producto.tienda_id, "cantidad": linea.cantidad,
                    "precio_unitario": linea.precio_unitario, "total": linea.total} for linea in pedido.items]}


def obtener(db, pedido_id):
    pedido = db.get(Pedido, pedido_id)
    if pedido is None: raise HTTPException(404, "Pedido no encontrado")
    return pedido


@router.get("/panel")
def panel(request: Request, db: Session = Depends(get_db)):
    _obtener_admin_actual(request, db)
    compradores = db.query(Usuario).filter(Usuario.rol == RolUsuario.COMPRADOR).order_by(Usuario.nombre).all()
    productos = db.query(Producto).order_by(Producto.nombre).all()
    return pagina_publica(request, db, "admin_pedidos.html", {
        "compradores": compradores, "productos_pedido": productos,
        "estados_pedido": list(EstadoPedido), "metodos_pago": list(MetodoPago),
    })


@router.get("/")
def listar(request: Request, q: str = Query("", max_length=100), estado: EstadoPedido | None = None,
           pagina: int = Query(1, ge=1), db: Session = Depends(get_db)):
    _obtener_admin_actual(request, db)
    query = db.query(Pedido)
    if q.strip(): query = query.filter(Pedido.codigo_pedido.icontains(q.strip(), autoescape=True))
    if estado: query = query.filter(Pedido.estado == estado)
    total = query.count()
    pedidos = query.options(joinedload(Pedido.usuario), joinedload(Pedido.items).joinedload(ProductoPedido.producto)).order_by(Pedido.id.desc()).offset((pagina - 1) * 20).limit(20).all()
    return {"pedidos": [serializar(p) for p in pedidos], "total": total, "pagina": pagina, "paginas": ceil(total / 20)}


@router.get("/{pedido_id}")
def leer(pedido_id: int, request: Request, db: Session = Depends(get_db)):
    _obtener_admin_actual(request, db)
    return serializar(obtener(db, pedido_id))


def guardar(db, pedido, datos):
    comprador = db.get(Usuario, datos.usuario_id)
    if comprador is None or comprador.rol != RolUsuario.COMPRADOR:
        raise HTTPException(422, "El pedido debe pertenecer a un comprador")
    if len({linea.producto_id for linea in datos.lineas}) != len(datos.lineas):
        raise HTTPException(422, "Cada producto debe aparecer una sola vez; ajusta su cantidad")
    lineas = []
    for linea in datos.lineas:
        producto = db.get(Producto, linea.producto_id)
        if producto is None: raise HTTPException(422, "Producto no encontrado")
        precio = linea.precio_unitario
        if precio is None:
            precio = producto.precio_oferta if producto.precio_oferta is not None and 0 <= producto.precio_oferta < producto.precio else producto.precio
        precio = round(precio, 2)
        total_linea = round(precio * linea.cantidad, 2)
        if precio < 0 or not isfinite(precio) or not isfinite(total_linea):
            raise HTTPException(422, "Precio o importe de línea no válido")
        lineas.append(ProductoPedido(producto_id=producto.id, cantidad=linea.cantidad, precio_unitario=precio, total=total_linea))
    subtotal = round(sum(linea.total for linea in lineas), 2)
    total = round(subtotal + datos.impuesto + datos.coste_entrega, 2)
    if not isfinite(total): raise HTTPException(422, "Importe total no válido")
    if pedido is None:
        pedido = Pedido()
        db.add(pedido)
    for campo, valor in datos.model_dump(exclude={"lineas"}).items(): setattr(pedido, campo, valor)
    pedido.items = lineas
    pedido.subtotal = subtotal
    pedido.total = total
    pedido.fecha_actualizacion = datetime.utcnow()
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "El código de pedido ya existe o hay datos relacionados incompatibles")
    return serializar(pedido)


@router.post("/", status_code=201)
def crear(datos: PedidoDatos, request: Request, db: Session = Depends(get_db)):
    _obtener_admin_actual(request, db)
    _validar_csrf(request)
    return guardar(db, None, datos)


@router.put("/{pedido_id}")
def editar(pedido_id: int, datos: PedidoDatos, request: Request, db: Session = Depends(get_db)):
    _obtener_admin_actual(request, db)
    _validar_csrf(request)
    return guardar(db, obtener(db, pedido_id), datos)


@router.delete("/{pedido_id}", status_code=204)
def eliminar(pedido_id: int, request: Request, db: Session = Depends(get_db)):
    _obtener_admin_actual(request, db)
    _validar_csrf(request)
    db.delete(obtener(db, pedido_id))
    db.commit()
