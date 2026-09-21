"""Gestión de tiendas y productos para vendedores y administradores."""
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Categoria, CoordenadasTienda, Pedido, Producto, ProductoPedido, RolUsuario, Tienda, Usuario
from app.routers.auth import _validar_csrf
from app.routers.users import _obtener_usuario_actual
from app.routers.catalogo import pagina_publica, producto_publico

router = APIRouter(tags=["gestión comercial"])
IMAGE_DIRECTORY = Path("static/uploads")


@router.post("/api/gestion/imagenes", status_code=201)
async def subir_imagen(request: Request, archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    gestor(request, db)
    _validar_csrf(request)
    contenido = await archivo.read(5 * 1024 * 1024 + 1)
    await archivo.close()
    if len(contenido) > 5 * 1024 * 1024:
        raise HTTPException(413, "La imagen no puede superar 5 MB")
    extension = None
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = "png"
    elif contenido.startswith(b"\xff\xd8\xff"):
        extension = "jpg"
    elif contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP":
        extension = "webp"
    if extension is None:
        raise HTTPException(422, "Selecciona una imagen JPG, PNG o WebP")
    IMAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid4().hex}.{extension}"
    (IMAGE_DIRECTORY / nombre).write_bytes(contenido)
    return {"imagen": f"/static/uploads/{nombre}"}


def gestor(request, db):
    usuario = _obtener_usuario_actual(request, db)
    if usuario.rol not in {RolUsuario.VENDEDOR, RolUsuario.ADMIN}:
        raise HTTPException(403, "Acceso exclusivo para vendedores y administradores")
    return usuario


def tiendas_permitidas(db, usuario):
    query = db.query(Tienda)
    return query if usuario.rol == RolUsuario.ADMIN else query.filter(Tienda.vendedor_id == usuario.id)


def tienda_permitida(db, usuario, tienda_id):
    tienda = tiendas_permitidas(db, usuario).filter(Tienda.id == tienda_id).first()
    if tienda is None:
        raise HTTPException(404, "Tienda no encontrada")
    return tienda


class TiendaDatos(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    descripcion: str = Field(default="", max_length=5000)
    direccion: str = Field(min_length=1, max_length=300)
    ubicacion: str = Field(default="", max_length=200)
    horario: str = Field(default="", max_length=300)
    imagen: str = Field(default="", max_length=1000)
    latitud: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitud: float = Field(ge=-180, le=180, allow_inf_nan=False)
    vendedor_id: int | None = Field(default=None, ge=1)

    @field_validator("nombre", "direccion")
    @classmethod
    def texto_requerido(cls, value):
        if not value.strip(): raise ValueError("Campo obligatorio")
        return value.strip()

    @field_validator("imagen")
    @classmethod
    def imagen_segura(cls, value):
        if value and not (value.startswith(("https://", "http://")) or (value.startswith("/") and not value.startswith("//"))):
            raise ValueError("Usa una URL http(s) o una ruta local absoluta")
        return value


class ProductoDatos(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    descripcion: str = Field(default="", max_length=5000)
    precio: float = Field(gt=0, allow_inf_nan=False)
    precio_oferta: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    modalidad_compra: str = Field(default="presencial", pattern="^(online|presencial)$")
    marca: str = Field(default="", max_length=160)
    categoria: Categoria
    imagen: str = Field(default="", max_length=1000)
    disponible: bool = True
    destacado: bool = False
    stock: int = Field(ge=0, le=1000000, strict=True)

    validar_nombre = field_validator("nombre")(TiendaDatos.texto_requerido.__func__)
    validar_imagen = field_validator("imagen")(TiendaDatos.imagen_segura.__func__)

    @model_validator(mode="after")
    def oferta_valida(self):
        if self.precio_oferta is not None and self.precio_oferta >= self.precio:
            raise ValueError("El precio de oferta debe ser inferior al precio normal")
        return self


def datos_tienda(tienda):
    coords = tienda.coordenadas
    categorias = {categoria.value for categoria in tienda.categorias}
    return {**{k: getattr(tienda, k) for k in ("id", "nombre", "descripcion", "direccion", "ubicacion", "horario", "imagen", "vendedor_id", "valoracion_media")},
            "categorias": sorted(categorias), "latitud": coords.latitud if coords else None,
            "longitud": coords.longitud if coords else None,
            "fecha_creacion": tienda.fecha_creacion, "fecha_actualizacion": tienda.fecha_actualizacion}


def guardar_tienda(db, usuario, tienda, datos):
    vendedor_id = datos.vendedor_id or (tienda.vendedor_id if tienda else usuario.id)
    if usuario.rol == RolUsuario.VENDEDOR and vendedor_id != usuario.id:
        raise HTTPException(403, "No puedes asignar tiendas a otro vendedor")
    vendedor = db.get(Usuario, vendedor_id)
    if vendedor is None or vendedor.rol != RolUsuario.VENDEDOR:
        raise HTTPException(422, "Selecciona un vendedor válido")
    if tienda is None or vendedor_id != tienda.vendedor_id:
        db.query(Usuario).filter_by(id=vendedor_id).with_for_update().one()
        existente = db.query(Tienda).filter_by(vendedor_id=vendedor_id).first()
        if existente is not None:
            raise HTTPException(409, "Este vendedor ya tiene una tienda")
    if tienda is None:
        tienda = Tienda(vendedor_id=vendedor_id)
        db.add(tienda)
    for key, value in datos.model_dump(exclude={"latitud", "longitud", "vendedor_id"}).items():
        setattr(tienda, key, value)
    tienda.vendedor_id = vendedor_id
    tienda.fecha_actualizacion = datetime.utcnow()
    db.flush()
    if tienda.coordenadas is None:
        tienda.coordenadas = CoordenadasTienda(latitud=datos.latitud, longitud=datos.longitud)
    else:
        tienda.coordenadas.latitud, tienda.coordenadas.longitud = datos.latitud, datos.longitud
    db.commit()
    return datos_tienda(tienda)


@router.get("/api/gestion/tiendas")
def listar_tiendas(request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    return [datos_tienda(t) for t in tiendas_permitidas(db, usuario).order_by(Tienda.nombre).all()]


@router.post("/api/gestion/tiendas", status_code=201)
def crear_tienda(datos: TiendaDatos, request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    _validar_csrf(request)
    return guardar_tienda(db, usuario, None, datos)


@router.get("/api/gestion/tiendas/{tienda_id}")
def leer_tienda(tienda_id: int, request: Request, db: Session = Depends(get_db)):
    return datos_tienda(tienda_permitida(db, gestor(request, db), tienda_id))


@router.get("/api/gestion/tiendas/{tienda_id}/productos")
def leer_productos(tienda_id: int, request: Request, pagina: int = Query(1, ge=1), db: Session = Depends(get_db)):
    tienda = tienda_permitida(db, gestor(request, db), tienda_id)
    query = db.query(Producto).filter_by(tienda_id=tienda.id)
    return {"total": query.count(), "pagina": pagina, "productos": [
        {**producto_publico(p), "disponible": p.disponible, "fecha_creacion": p.fecha_creacion, "fecha_actualizacion": p.fecha_actualizacion}
        for p in query.order_by(Producto.id).offset((pagina - 1) * 24).limit(24).all()]}


@router.put("/api/gestion/tiendas/{tienda_id}")
def editar_tienda(tienda_id: int, datos: TiendaDatos, request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    _validar_csrf(request)
    return guardar_tienda(db, usuario, tienda_permitida(db, usuario, tienda_id), datos)


def borrar_producto_seguro(db, producto):
    if db.query(ProductoPedido).filter_by(producto_id=producto.id).first():
        raise HTTPException(409, "El producto tiene pedidos: márcalo como no disponible para conservar el historial")
    db.delete(producto)


@router.delete("/api/gestion/tiendas/{tienda_id}")
def borrar_tienda(tienda_id: int, request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    _validar_csrf(request)
    tienda = tienda_permitida(db, usuario, tienda_id)
    if db.query(ProductoPedido).join(Producto).filter(Producto.tienda_id == tienda.id).first():
        raise HTTPException(409, "La tienda tiene productos con pedidos y debe conservarse su historial")
    db.delete(tienda)
    db.commit()
    return {"mensaje": "Tienda eliminada"}


def guardar_producto(db, tienda, producto, datos):
    if producto is None:
        producto = Producto(tienda_id=tienda.id)
        db.add(producto)
    for key, value in datos.model_dump().items(): setattr(producto, key, value)
    producto.fecha_actualizacion = datetime.utcnow()
    db.commit()
    return producto_publico(producto)


@router.post("/api/gestion/tiendas/{tienda_id}/productos", status_code=201)
def crear_producto(tienda_id: int, datos: ProductoDatos, request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    _validar_csrf(request)
    return guardar_producto(db, tienda_permitida(db, usuario, tienda_id), None, datos)


def producto_permitido(db, usuario, producto_id):
    producto = db.get(Producto, producto_id)
    if producto is None: raise HTTPException(404, "Producto no encontrado")
    tienda_permitida(db, usuario, producto.tienda_id)
    return producto


@router.get("/api/gestion/productos/{producto_id}")
def leer_producto(producto_id: int, request: Request, db: Session = Depends(get_db)):
    producto = producto_permitido(db, gestor(request, db), producto_id)
    return {**producto_publico(producto), "disponible": producto.disponible,
            "fecha_creacion": producto.fecha_creacion, "fecha_actualizacion": producto.fecha_actualizacion}


@router.put("/api/gestion/productos/{producto_id}")
def editar_producto(producto_id: int, datos: ProductoDatos, request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    _validar_csrf(request)
    producto = producto_permitido(db, usuario, producto_id)
    return guardar_producto(db, producto.tienda, producto, datos)


@router.delete("/api/gestion/productos/{producto_id}")
def borrar_producto(producto_id: int, request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    _validar_csrf(request)
    borrar_producto_seguro(db, producto_permitido(db, usuario, producto_id))
    db.commit()
    return {"mensaje": "Producto eliminado"}


@router.get("/mi-tienda")
@router.get("/admin/tiendas")
def mis_tiendas(request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    if request.url.path == "/admin/tiendas" and usuario.rol != RolUsuario.ADMIN:
        raise HTTPException(403, "Acceso exclusivo para administradores")
    tiendas = tiendas_permitidas(db, usuario).order_by(Tienda.nombre).all()
    return pagina_publica(request, db, "gestion_tiendas.html", {"tiendas_gestion": [datos_tienda(t) for t in tiendas],
        "tienda_activa": tiendas[0].id if tiendas and usuario.rol == RolUsuario.VENDEDOR else None})


@router.get("/gestion/tiendas/nueva")
def nueva_tienda(request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    if usuario.rol == RolUsuario.VENDEDOR and db.query(Tienda).filter_by(vendedor_id=usuario.id).first():
        return RedirectResponse("/mi-tienda", status_code=303)
    return pagina_publica(request, db, "gestion_tienda_form.html", {
        "tienda_gestion": None, "vendedores": db.query(Usuario).filter(Usuario.rol == RolUsuario.VENDEDOR).all() if usuario.rol == RolUsuario.ADMIN else [],
    })


class StockDatos(BaseModel):
    stock: int = Field(ge=0, le=1000000, strict=True)


class StockProductoDatos(StockDatos):
    producto_id: int = Field(ge=1)


class StocksDatos(BaseModel):
    productos: list[StockProductoDatos] = Field(min_length=1, max_length=100)


@router.patch("/api/gestion/tiendas/{tienda_id}/stock")
def editar_stocks(tienda_id: int, datos: StocksDatos, request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    _validar_csrf(request)
    tienda_permitida(db, usuario, tienda_id)
    ids = [item.producto_id for item in datos.productos]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, "Hay productos repetidos")
    productos = db.query(Producto).filter(Producto.tienda_id == tienda_id, Producto.id.in_(ids)).all()
    if len(productos) != len(ids):
        raise HTTPException(404, "Producto no encontrado en esta tienda")
    stocks = {item.producto_id: item.stock for item in datos.productos}
    for producto in productos:
        producto.stock = stocks[producto.id]
        producto.fecha_actualizacion = datetime.utcnow()
    db.commit()
    return {"productos": [{"id": producto.id, "stock": producto.stock} for producto in productos]}


@router.patch("/api/gestion/productos/{producto_id}/stock")
def editar_stock(producto_id: int, datos: StockDatos, request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    _validar_csrf(request)
    producto = producto_permitido(db, usuario, producto_id)
    producto.stock = datos.stock
    producto.fecha_actualizacion = datetime.utcnow()
    db.commit()
    return {"id": producto.id, "stock": producto.stock}


@router.get("/gestion/tiendas/{tienda_id}/editar")
def formulario_tienda(tienda_id: int, request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    tienda = tienda_permitida(db, usuario, tienda_id)
    return pagina_publica(request, db, "gestion_tienda_form.html", {
        "tienda_gestion": datos_tienda(tienda), "tienda_activa": tienda.id,
        "vendedores": db.query(Usuario).filter(Usuario.rol == RolUsuario.VENDEDOR).all() if usuario.rol == RolUsuario.ADMIN else [],
    })


@router.get("/gestion/tiendas/{tienda_id}/productos")
def panel_productos(tienda_id: int, request: Request, q: str = Query("", max_length=120),
                    pagina: int = Query(1, ge=1), db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    tienda = tienda_permitida(db, usuario, tienda_id)
    query = db.query(Producto).filter_by(tienda_id=tienda.id)
    if q.strip(): query = query.filter(Producto.nombre.icontains(q.strip(), autoescape=True))
    total = query.count()
    productos = query.order_by(Producto.id.desc()).offset((pagina - 1) * 24).limit(24).all()
    base = f"/gestion/tiendas/{tienda.id}/productos?"
    return pagina_publica(request, db, "gestion_productos.html", {
        "tienda_gestion": datos_tienda(tienda), "tienda_activa": tienda.id, "productos_gestion": [{**producto_publico(p), "disponible": p.disponible} for p in productos],
        "q": q, "total": total, "pagina": pagina,
        "anterior": base + urlencode({"pagina": pagina - 1, "q": q}) if pagina > 1 else None,
        "siguiente": base + urlencode({"pagina": pagina + 1, "q": q}) if pagina * 24 < total else None,
    })


@router.get("/gestion/tiendas/{tienda_id}")
def dashboard(tienda_id: int, request: Request, db: Session = Depends(get_db)):
    usuario = gestor(request, db)
    tienda = tienda_permitida(db, usuario, tienda_id)
    # Solo las líneas de esta tienda, incluso en pedidos que contienen varias tiendas.
    lineas = db.query(ProductoPedido).join(Producto).filter(Producto.tienda_id == tienda.id).options(joinedload(ProductoPedido.pedido), joinedload(ProductoPedido.producto)).order_by(ProductoPedido.id.desc()).all()
    pedidos = {}
    for linea in lineas:
        pedido = linea.pedido
        entrada = pedidos.setdefault(pedido.id, {"codigo": pedido.codigo_pedido, "estado": pedido.estado.value, "fecha": pedido.fecha, "total": 0, "lineas": []})
        entrada["total"] += linea.total
        entrada["lineas"].append({"nombre": linea.producto.nombre, "cantidad": linea.cantidad})
    return pagina_publica(request, db, "gestion_dashboard.html", {
        "tienda_gestion": datos_tienda(tienda), "tienda_activa": tienda.id,
        "pedidos_tienda": list(pedidos.values()), "stock_tienda": tienda.productos,
    })
