"""Inicio con productos y búsqueda geográfica: RF11 y RF05."""
from math import ceil
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Categoria, CoordenadasTienda, Producto, RolUsuario, Tienda, Usuario
from app.routers.auth import templates, _validar_csrf
from app.routers.users import _obtener_usuario_actual

router = APIRouter(tags=["catálogo"])
PAGE_SIZE = 24


def categoria_filtrada(categoria: str = Query("", max_length=80)):
    if not categoria:
        return None
    try:
        return Categoria(categoria)
    except ValueError:
        raise HTTPException(status_code=422, detail="Categoría no válida")


def seleccionar(db, q, categoria, destacados):
    query = db.query(Producto).join(Tienda).join(Usuario, Tienda.vendedor_id == Usuario.id).filter(
        Producto.disponible.is_(True), Usuario.activo.is_(True),
    )
    if q:
        # contains(autoescape=True) trata % y _ como texto de búsqueda, no como comodines SQL.
        query = query.filter(or_(*[field.icontains(q, autoescape=True) for field in (
            Producto.nombre, Producto.descripcion, Producto.marca, Tienda.nombre, Tienda.ubicacion, Tienda.direccion,
        )]))
    if categoria:
        query = query.filter(Producto.categoria == categoria)
    if destacados:
        query = query.filter(Producto.destacado.is_(True))
    return query


def producto_publico(producto):
    tienda = producto.tienda
    coordenadas = tienda.coordenadas
    imagen = producto.imagen or ""
    if not (imagen.startswith(("https://", "http://")) or (imagen.startswith("/") and not imagen.startswith("//"))):
        imagen = None
    return {
        "id": producto.id, "nombre": producto.nombre, "descripcion": producto.descripcion,
        "precio": producto.precio, "precio_oferta": producto.precio_oferta, "imagen": imagen,
        "destacado": producto.destacado, "marca": producto.marca, "stock": producto.stock,
        "categoria": producto.categoria.value,
        "tienda": {"id": tienda.id, "nombre": tienda.nombre, "direccion": tienda.direccion,
                   "ubicacion": tienda.ubicacion, "latitud": coordenadas.latitud if coordenadas else None,
                   "longitud": coordenadas.longitud if coordenadas else None},
    }


def buscar(db, q, categoria, destacados, pagina):
    query = seleccionar(db, q, categoria, destacados)
    total = query.count()
    productos = query.options(joinedload(Producto.tienda).joinedload(Tienda.coordenadas)).order_by(
        Producto.destacado.desc(), Producto.id.desc(),
    ).offset((pagina - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    return {"productos": [producto_publico(p) for p in productos], "total": total,
            "pagina": pagina, "paginas": ceil(total / PAGE_SIZE), "por_pagina": PAGE_SIZE}


@router.get("/api/productos")
def api_productos(q: str = Query("", max_length=120), categoria: Categoria | None = Depends(categoria_filtrada),
                  destacados: bool = False, pagina: int = Query(1, ge=1), db: Session = Depends(get_db)):
    return buscar(db, q.strip(), categoria, destacados, pagina)


@router.get("/inicio", response_class=HTMLResponse)
def inicio(request: Request, q: str = Query("", max_length=120), categoria: Categoria | None = Depends(categoria_filtrada),
           destacados: bool = False, pagina: int = Query(1, ge=1), db: Session = Depends(get_db)):
    q = q.strip()
    es_busqueda = bool(q or categoria or destacados or "q" in request.query_params or "categoria" in request.query_params)
    destacados_inicio = not es_busqueda and seleccionar(db, "", None, True).count() > 0
    datos = buscar(db, q, categoria, destacados or destacados_inicio, pagina)
    user_name, es_admin = None, False
    if request.session.get("usuario"):
        try:
            usuario = _obtener_usuario_actual(request, db)
            user_name, es_admin = usuario.nombre, usuario.rol == RolUsuario.ADMIN
        except HTTPException as error:
            if error.status_code not in {401, 403, 404}:
                raise
            request.session.clear()
    def pagina_url(numero):
        params = {"pagina": numero}
        if es_busqueda: params["q"] = q
        if q: params["q"] = q
        if categoria: params["categoria"] = categoria.value
        if destacados: params["destacados"] = "true"
        return "/inicio?" + urlencode(params)
    return templates.TemplateResponse(request=request, name="inicio.html", context={
        **datos, "q": q, "categoria_seleccionada": categoria.value if categoria else "",
        "categorias": list(Categoria), "destacados": destacados, "es_busqueda": es_busqueda,
        "titulo_productos": "Resultados de búsqueda" if es_busqueda else "Productos destacados" if destacados_inicio else "Productos",
        "anterior": pagina_url(pagina - 1) if pagina > 1 else None,
        "siguiente": pagina_url(pagina + 1) if pagina < datos["paginas"] else None,
        "sin_ubicacion": sum(1 for p in datos["productos"] if p["tienda"]["latitud"] is None),
        "user_name": user_name, "es_admin": es_admin,
    })


class CoordenadasRequest(BaseModel):
    latitud: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitud: float = Field(ge=-180, le=180, allow_inf_nan=False)


@router.put("/api/tiendas/{tienda_id}/ubicacion")
def guardar_ubicacion(tienda_id: int, datos: CoordenadasRequest, request: Request, db: Session = Depends(get_db)):
    usuario = _obtener_usuario_actual(request, db)
    _validar_csrf(request)
    tienda = db.get(Tienda, tienda_id)
    if not tienda:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")
    if usuario.rol != RolUsuario.ADMIN and not (usuario.rol == RolUsuario.VENDEDOR and tienda.vendedor_id == usuario.id):
        raise HTTPException(status_code=403, detail="No puedes modificar esta tienda")
    coordenadas = db.get(CoordenadasTienda, tienda_id)
    if not coordenadas:
        coordenadas = CoordenadasTienda(tienda_id=tienda_id)
        db.add(coordenadas)
    coordenadas.latitud, coordenadas.longitud = datos.latitud, datos.longitud
    db.commit()
    return {"tienda_id": tienda_id, "latitud": coordenadas.latitud, "longitud": coordenadas.longitud}
