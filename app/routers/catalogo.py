"""Inicio con productos y búsqueda geográfica: RF11 y RF05."""
from math import ceil, radians, sin, cos, asin, sqrt, isfinite
from typing import Literal
import secrets
from datetime import datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_, case, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Carrito, ProductoCarrito, Categoria, CoordenadasTienda, Producto, RolUsuario, Tienda, Usuario, ValoracionProducto, ValoracionTienda, ComentarioProducto, ComentarioTienda
from app.routers.auth import templates, _validar_csrf
from app.routers.users import _obtener_usuario_actual

router = APIRouter(tags=["catálogo"])
PAGE_SIZE = 24


def filtros_opcionales(tienda_id: str | None = Query(None), precio_min: str | None = Query(None),
                      precio_max: str | None = Query(None), modalidad: str | None = Query(None)):
    def numero(nombre, valor, convertir, minimo):
        if valor is None or valor == "":
            return None
        try:
            resultado = convertir(valor)
        except ValueError:
            raise HTTPException(422, f"{nombre} no válido")
        if not isfinite(resultado) or resultado < minimo:
            raise HTTPException(422, f"{nombre} no válido")
        return resultado

    if modalidad == "":
        modalidad = None
    if modalidad not in (None, "online", "presencial"):
        raise HTTPException(422, "Modalidad no válida")
    return (numero("tienda_id", tienda_id, int, 1),
            numero("precio_min", precio_min, float, 0),
            numero("precio_max", precio_max, float, 0), modalidad)


def categoria_filtrada(categoria: str = Query("", max_length=80)):
    if not categoria:
        return None
    try:
        return Categoria(categoria)
    except ValueError:
        raise HTTPException(status_code=422, detail="Categoría no válida")


def seleccionar(db, q, categoria, destacados):
    query = db.query(Producto).join(Tienda).join(Usuario, Tienda.vendedor_id == Usuario.id).filter(
        Usuario.activo.is_(True),
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
    oferta = producto.precio_oferta is not None and 0 <= producto.precio_oferta < producto.precio
    return {
        "id": producto.id, "nombre": producto.nombre, "descripcion": producto.descripcion,
        "precio": producto.precio, "precio_oferta": producto.precio_oferta if oferta else None, "imagen": imagen,
        "descuento": round((1 - producto.precio_oferta / producto.precio) * 100, 2) if oferta else None,
        "disponible": producto.disponible and producto.stock > 0,
        "destacado": producto.destacado, "marca": producto.marca, "stock": producto.stock,
        "categoria": producto.categoria.value,
        "valoracion_media": producto.valoracion_media, "modalidad_compra": producto.modalidad_compra,
        "tienda": {"id": tienda.id, "nombre": tienda.nombre, "direccion": tienda.direccion,
                   "ubicacion": tienda.ubicacion, "horario": tienda.horario, "latitud": coordenadas.latitud if coordenadas else None,
                   "longitud": coordenadas.longitud if coordenadas else None},
    }


def geografia(latitud: float | None = Query(None, ge=-90, le=90, allow_inf_nan=False),
              longitud: float | None = Query(None, ge=-180, le=180, allow_inf_nan=False),
              radio: int = Query(0, ge=0, le=100000)):
    if (latitud is None) != (longitud is None) or (radio and latitud is None):
        raise HTTPException(422, "Selecciona una ubicación para buscar por radio")
    return latitud, longitud, radio


def filtrar_radio(query, db, geo, columna=Producto.tienda_id):
    lat, lon, radio = geo
    if not radio:
        return query
    ids = []
    for coords in db.query(CoordenadasTienda).all():
        a = sin(radians(coords.latitud - lat) / 2) ** 2 + cos(radians(lat)) * cos(radians(coords.latitud)) * sin(radians(coords.longitud - lon) / 2) ** 2
        if 6371000 * 2 * asin(sqrt(min(1, a))) <= radio:
            ids.append(coords.tienda_id)
    return query.filter(columna.in_(ids))


def contexto_publico(request, db):
    contexto = {"user_name": None, "es_admin": False, "es_vendedor": False, "es_comprador": False, "puede_comprar": True}
    if request.session.get("usuario"):
        try:
            usuario = _obtener_usuario_actual(request, db)
            contexto.update(user_name=usuario.nombre, es_admin=usuario.rol == RolUsuario.ADMIN,
                            es_comprador=usuario.rol == RolUsuario.COMPRADOR,
                            es_vendedor=usuario.rol == RolUsuario.VENDEDOR,
                            puede_comprar=usuario.rol == RolUsuario.COMPRADOR)
            if usuario.rol == RolUsuario.VENDEDOR:
                tienda_propia = db.query(Tienda).filter_by(vendedor_id=usuario.id).order_by(Tienda.id).first()
                contexto["tienda_activa"] = tienda_propia.id if tienda_propia else None
        except HTTPException as error:
            if error.status_code not in {401, 403, 404}: raise
            request.session.clear()
    token = request.session.setdefault("csrf_token", secrets.token_urlsafe(32))
    contexto["csrf_token"] = token
    contexto["cabecera_comprador"] = contexto["puede_comprar"]
    contexto["cabecera_gestion"] = contexto["es_vendedor"] or contexto["es_admin"]
    contexto["es_inicio"] = request.url.path == "/inicio"
    contexto["categorias"] = list(Categoria)
    return contexto


def pagina_publica(request, db, name, contexto):
    contexto = {**contexto, **contexto_publico(request, db)}
    response = templates.TemplateResponse(request=request, name=name, context=contexto)
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie("csrf_token", contexto["csrf_token"], samesite="lax", secure=request.url.scheme == "https")
    return response


def buscar(db, q, categoria, destacados, pagina, geo=(None, None, 0), tienda_id=None,
           precio_min=None, precio_max=None, valoracion_min=None, modalidad=None,
           tienda_valoracion_min=None):
    query = seleccionar(db, q, categoria, destacados)
    if tienda_id is not None:
        query = query.filter(Producto.tienda_id == tienda_id)
    precio_final = case((Producto.precio_oferta.isnot(None), Producto.precio_oferta), else_=Producto.precio)
    if precio_min is not None:
        query = query.filter(precio_final >= precio_min)
    if precio_max is not None:
        query = query.filter(precio_final <= precio_max)
    if valoracion_min is not None and valoracion_min > 0:
        query = query.filter(Producto.valoracion_media >= valoracion_min)
    if modalidad:
        query = query.filter(Producto.modalidad_compra == modalidad)
    query = filtrar_radio(query, db, geo)
    total = query.count()
    productos = query.options(joinedload(Producto.tienda).joinedload(Tienda.coordenadas)).order_by(
        Producto.destacado.desc(), Producto.id.desc(),
    ).offset((pagina - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    tiendas_query = db.query(Tienda).join(Usuario, Tienda.vendedor_id == Usuario.id).filter(Usuario.activo.is_(True))
    if tienda_id is not None:
        tiendas_query = tiendas_query.filter(Tienda.id == tienda_id)
    if tienda_valoracion_min is not None and tienda_valoracion_min > 0:
        tiendas_query = tiendas_query.filter(Tienda.valoracion_media >= tienda_valoracion_min)
    if categoria or destacados:
        tiendas_query = tiendas_query.filter(Tienda.id.in_(query.with_entities(Producto.tienda_id)))
    elif q:
        tiendas_query = tiendas_query.filter(or_(
            Tienda.id.in_(query.with_entities(Producto.tienda_id)),
            *[field.icontains(q, autoescape=True) for field in (Tienda.nombre, Tienda.descripcion, Tienda.ubicacion, Tienda.direccion)],
        ))
    tiendas = filtrar_radio(tiendas_query, db, geo, Tienda.id).options(joinedload(Tienda.coordenadas)).order_by(Tienda.nombre).all()
    return {"productos": [producto_publico(p) for p in productos], "tiendas": [
        {"id": t.id, "nombre": t.nombre, "direccion": t.direccion, "ubicacion": t.ubicacion,
         "imagen": t.imagen if t.imagen and (t.imagen.startswith(("https://", "http://")) or (t.imagen.startswith("/") and not t.imagen.startswith("//"))) else None,
         "latitud": t.coordenadas.latitud if t.coordenadas else None,
         "longitud": t.coordenadas.longitud if t.coordenadas else None,
         "valoracion_media": t.valoracion_media} for t in tiendas], "total": total,
            "pagina": pagina, "paginas": ceil(total / PAGE_SIZE), "por_pagina": PAGE_SIZE}


@router.get("/api/productos")
def api_productos(request: Request, q: str = Query("", max_length=120), categoria: Categoria | None = Depends(categoria_filtrada),
                  destacados: bool = False, pagina: int = Query(1, ge=1), geo=Depends(geografia),
                  filtros=Depends(filtros_opcionales),
                  valoracion_min: float | None = Query(None, ge=0, le=5, allow_inf_nan=False),
                  tienda_valoracion_min: float | None = Query(None, ge=0, le=5, allow_inf_nan=False),
                  db: Session = Depends(get_db)):
    tienda_id, precio_min, precio_max, modalidad = filtros
    validar_precios(precio_min, precio_max)
    vendedor = vendedor_actual(request, db)
    if vendedor:
        tienda = db.query(Tienda).filter_by(vendedor_id=vendedor.id).first()
        if tienda is None:
            return {"productos": [], "tiendas": [], "total": 0, "pagina": pagina, "paginas": 0, "por_pagina": PAGE_SIZE}
        if tienda_id is not None and tienda_id != tienda.id:
            return {"productos": [], "tiendas": [], "total": 0, "pagina": pagina, "paginas": 0, "por_pagina": PAGE_SIZE}
        tienda_id = tienda.id
    return buscar(db, q.strip(), categoria, destacados, pagina, geo, tienda_id,
                  precio_min, precio_max, valoracion_min, modalidad, tienda_valoracion_min)


def validar_precios(precio_min, precio_max):
    if precio_min is not None and precio_max is not None and precio_min > precio_max:
        raise HTTPException(422, "El precio mínimo no puede superar el máximo")


@router.get("/api/tiendas")
def api_tiendas(categoria: Categoria | None = Depends(categoria_filtrada),
                valoracion_min: float | None = Query(None, ge=0, le=5, allow_inf_nan=False),
                db: Session = Depends(get_db)):
    query = db.query(Tienda).join(Usuario, Tienda.vendedor_id == Usuario.id).filter(Usuario.activo.is_(True))
    if categoria:
        query = query.filter(Tienda.productos.any(Producto.categoria == categoria))
    if valoracion_min is not None and valoracion_min > 0:
        query = query.filter(Tienda.valoracion_media >= valoracion_min)
    return [{"id": tienda.id, "nombre": tienda.nombre,
             "categorias": [item.value for item in tienda.categorias],
             "valoracion_media": tienda.valoracion_media} for tienda in query.order_by(Tienda.nombre).all()]


def vendedor_actual(request, db):
    if not request.session.get("usuario"): return None
    usuario = _obtener_usuario_actual(request, db)
    return usuario if usuario.rol == RolUsuario.VENDEDOR else None


def limitar_tienda_vendedor(request, db, tienda_id):
    vendedor = vendedor_actual(request, db)
    if vendedor and not db.query(Tienda).filter_by(id=tienda_id, vendedor_id=vendedor.id).first():
        raise HTTPException(404, "Tienda no encontrada")
    return vendedor


@router.get("/inicio", response_class=HTMLResponse)
def inicio(request: Request, q: str = Query("", max_length=120), categoria: Categoria | None = Depends(categoria_filtrada),
           destacados: bool = False, pagina: int = Query(1, ge=1), geo=Depends(geografia),
           filtros=Depends(filtros_opcionales),
           valoracion_min: float | None = Query(None, ge=0, le=5, allow_inf_nan=False),
           tienda_valoracion_min: float | None = Query(None, ge=0, le=5, allow_inf_nan=False),
           db: Session = Depends(get_db)):
    tienda_id, precio_min, precio_max, modalidad = filtros
    validar_precios(precio_min, precio_max)
    if vendedor_actual(request, db):
        return RedirectResponse("/mi-tienda", status_code=303)
    q = q.strip()
    es_busqueda = bool(q or categoria or destacados or "q" in request.query_params or "categoria" in request.query_params)
    es_busqueda = es_busqueda or bool(geo[2]) or any(value is not None for value in (
        tienda_id, precio_min, precio_max, valoracion_min, tienda_valoracion_min, modalidad))
    datos = buscar(db, q, categoria, destacados, pagina, geo, tienda_id,
                   precio_min, precio_max, valoracion_min, modalidad, tienda_valoracion_min)
    def pagina_url(numero):
        params = {"pagina": numero}
        if request.query_params.get("tab") in {"mapa", "productos", "tiendas"}:
            params["tab"] = request.query_params["tab"]
        if es_busqueda: params["q"] = q
        if q: params["q"] = q
        if categoria: params["categoria"] = categoria.value
        if destacados: params["destacados"] = "true"
        for key, value in (("tienda_id", tienda_id), ("precio_min", precio_min), ("precio_max", precio_max),
                           ("valoracion_min", valoracion_min), ("tienda_valoracion_min", tienda_valoracion_min),
                           ("modalidad", modalidad)):
            if value is not None: params[key] = value
        if geo[0] is not None: params.update(latitud=geo[0], longitud=geo[1], radio=geo[2])
        return "/inicio?" + urlencode(params)
    return pagina_publica(request, db, "inicio.html", {
        "vista_inicio": request.query_params.get("tab") if request.query_params.get("tab") in {"mapa", "productos", "tiendas"} else ("productos" if es_busqueda else "mapa"),
        "latitud": geo[0], "longitud": geo[1], "radio": geo[2],
        "precio_min": precio_min, "precio_max": precio_max,
        "valoracion_min": valoracion_min, "tienda_valoracion_min": tienda_valoracion_min,
        "modalidad": modalidad,
        **datos, "q": q, "categoria_seleccionada": categoria.value if categoria else "",
        "categorias": list(Categoria), "destacados": destacados, "es_busqueda": es_busqueda,
        "titulo_productos": "Resultados de búsqueda" if es_busqueda else "Catálogo de productos",
        "anterior": pagina_url(pagina - 1) if pagina > 1 else None,
        "siguiente": pagina_url(pagina + 1) if pagina < datos["paginas"] else None,
        "sin_ubicacion": sum(1 for p in datos["productos"] if p["tienda"]["latitud"] is None),
    })


class CoordenadasRequest(BaseModel):
    latitud: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitud: float = Field(ge=-180, le=180, allow_inf_nan=False)


@router.get("/tiendas/{tienda_id}", response_class=HTMLResponse)
def catalogo_tienda(request: Request, tienda_id: int, q: str = Query("", max_length=120),
                    categoria: Categoria | None = Depends(categoria_filtrada), destacados: bool = False,
                    pagina: int = Query(1, ge=1), db: Session = Depends(get_db)):
    if limitar_tienda_vendedor(request, db, tienda_id):
        return RedirectResponse(f"/gestion/tiendas/{tienda_id}/productos", status_code=303)
    tienda = db.query(Tienda).join(Usuario, Tienda.vendedor_id == Usuario.id).filter(
        Tienda.id == tienda_id, Usuario.activo.is_(True),
    ).first()
    if tienda is None:
        raise HTTPException(404, "Tienda no encontrada")
    q = q.strip()
    datos = buscar(db, q, categoria, destacados, pagina, tienda_id=tienda.id)
    def pagina_url(numero):
        params = {"pagina": numero, "q": q}
        if categoria: params["categoria"] = categoria.value
        if destacados: params["destacados"] = "true"
        return f"/tiendas/{tienda.id}?" + urlencode(params)
    return pagina_publica(request, db, "tienda.html", {
        "tienda_activa": tienda.id,
        "tienda_categorias": [categoria.value for categoria in tienda.categorias],
        "tienda_imagen": tienda.imagen if tienda.imagen and (tienda.imagen.startswith(("http://", "https://")) or (tienda.imagen.startswith("/") and not tienda.imagen.startswith("//"))) else None,
        **datos, "tienda": tienda, "q": q, "categorias": list(Categoria),
        "categoria_seleccionada": categoria.value if categoria else "", "destacados": destacados,
        "valoracion_usuario": puntuacion_usuario(request, db, ValoracionTienda, tienda.id),
        "comentarios": comentarios_publicos(db, ComentarioTienda, "tienda_id", tienda.id),
        "comentario_usuario": comentario_usuario(request, db, ComentarioTienda, "tienda_id", tienda.id),
        "tipo_comentario": "tiendas", "id_comentario": tienda.id,
        "anterior": pagina_url(pagina - 1) if pagina > 1 else None,
        "siguiente": pagina_url(pagina + 1) if pagina < datos["paginas"] else None,
    })


def obtener_producto(db, producto_id):
    producto = seleccionar(db, "", None, False).filter(Producto.id == producto_id).first()
    if producto is None:
        raise HTTPException(404, "Producto no encontrado")
    return producto


@router.get("/api/productos/{producto_id}")
def ficha_api(producto_id: int, request: Request, db: Session = Depends(get_db)):
    producto = obtener_producto(db, producto_id)
    limitar_tienda_vendedor(request, db, producto.tienda_id)
    return producto_publico(producto)


@router.get("/productos/{producto_id}", response_class=HTMLResponse)
def ficha(request: Request, producto_id: int, db: Session = Depends(get_db)):
    registro = obtener_producto(db, producto_id)
    limitar_tienda_vendedor(request, db, registro.tienda_id)
    producto = producto_publico(registro)
    return pagina_publica(request, db, "producto.html", {"producto": producto, "tienda_activa": producto["tienda"]["id"],
                                                   "valoracion_usuario": puntuacion_usuario(request, db, ValoracionProducto, producto_id),
                                                   "comentarios": comentarios_publicos(db, ComentarioProducto, "producto_id", producto_id),
                                                   "comentario_usuario": comentario_usuario(request, db, ComentarioProducto, "producto_id", producto_id),
                                                   "tipo_comentario": "productos", "id_comentario": producto_id})


def puntuacion_usuario(request, db, modelo, entidad_id):
    if not request.session.get("usuario"):
        return None
    usuario = _obtener_usuario_actual(request, db)
    if usuario.rol != RolUsuario.COMPRADOR:
        return None
    clave = "producto_id" if modelo is ValoracionProducto else "tienda_id"
    valoracion = db.query(modelo).filter_by(usuario_id=usuario.id, **{clave: entidad_id}).first()
    return valoracion.puntuacion if valoracion else None


class Puntuacion(BaseModel):
    puntuacion: int = Field(ge=1, le=5, strict=True)


def valorar(request, db, modelo, entidad, clave, entidad_id, puntuacion):
    usuario = _obtener_usuario_actual(request, db)
    if usuario.rol != RolUsuario.COMPRADOR:
        raise HTTPException(403, "Solo los compradores pueden valorar")
    _validar_csrf(request)
    db.query(Usuario).filter_by(id=usuario.id).with_for_update().one()
    registro = db.query(entidad).filter(entidad.id == entidad_id).with_for_update().first()
    if registro is None:
        raise HTTPException(404, "Elemento no encontrado")
    vendedor = registro.vendedor if entidad is Tienda else registro.tienda.vendedor
    if not vendedor.activo:
        raise HTTPException(404, "Elemento no encontrado")
    valoracion = db.query(modelo).filter_by(usuario_id=usuario.id, **{clave: entidad_id}).first()
    if valoracion is None:
        db.add(modelo(usuario_id=usuario.id, **{clave: entidad_id}, puntuacion=puntuacion))
    else:
        valoracion.puntuacion = puntuacion
        valoracion.fecha_actualizacion = datetime.utcnow()
    db.flush()
    media, total = db.query(func.avg(modelo.puntuacion), func.count()).filter(getattr(modelo, clave) == entidad_id).one()
    registro.valoracion_media = float(media)
    db.commit()
    return {"id": entidad_id, "valoracion_usuario": puntuacion, "valoracion_media": registro.valoracion_media,
            "total_valoraciones": total}


@router.put("/api/valoraciones/productos/{producto_id}")
def valorar_producto(producto_id: int, datos: Puntuacion, request: Request, db: Session = Depends(get_db)):
    return valorar(request, db, ValoracionProducto, Producto, "producto_id", producto_id, datos.puntuacion)


@router.put("/api/valoraciones/tiendas/{tienda_id}")
def valorar_tienda(tienda_id: int, datos: Puntuacion, request: Request, db: Session = Depends(get_db)):
    return valorar(request, db, ValoracionTienda, Tienda, "tienda_id", tienda_id, datos.puntuacion)


def comentarios_publicos(db, modelo, clave, entidad_id):
    registros = db.query(modelo).join(Usuario, modelo.usuario_id == Usuario.id).filter(
        getattr(modelo, clave) == entidad_id, Usuario.activo.is_(True)
    ).order_by(modelo.fecha_actualizacion.desc(), modelo.usuario_id.desc()).all()
    return [{"usuario_id": c.usuario_id, "autor": c.autor.nombre, "texto": c.texto,
             "fecha_actualizacion": c.fecha_actualizacion} for c in registros]


def comentario_usuario(request, db, modelo, clave, entidad_id):
    if not request.session.get("usuario"):
        return None
    usuario = _obtener_usuario_actual(request, db)
    if usuario.rol != RolUsuario.COMPRADOR:
        return None
    registro = db.query(modelo).filter_by(usuario_id=usuario.id, **{clave: entidad_id}).first()
    return registro.texto if registro else None


class TextoComentario(BaseModel):
    texto: str = Field(min_length=1, max_length=1000)

    @field_validator("texto")
    @classmethod
    def no_vacio(cls, texto):
        if not texto.strip():
            raise ValueError("Escribe un comentario")
        return texto.strip()


def cambiar_comentario(request, db, modelo, entidad, clave, entidad_id, texto):
    usuario = _obtener_usuario_actual(request, db)
    if usuario.rol != RolUsuario.COMPRADOR:
        raise HTTPException(403, "Solo los compradores pueden comentar")
    _validar_csrf(request)
    db.query(Usuario).filter_by(id=usuario.id).with_for_update().one()
    registro = db.get(entidad, entidad_id)
    if registro is None:
        raise HTTPException(404, "Elemento no encontrado")
    vendedor = registro.vendedor if entidad is Tienda else registro.tienda.vendedor
    if not vendedor.activo:
        raise HTTPException(404, "Elemento no encontrado")
    comentario = db.query(modelo).filter_by(usuario_id=usuario.id, **{clave: entidad_id}).first()
    if texto is None:
        if comentario is not None:
            db.delete(comentario)
    elif comentario is None:
        db.add(modelo(usuario_id=usuario.id, **{clave: entidad_id}, texto=texto))
    else:
        comentario.texto = texto
        comentario.fecha_actualizacion = datetime.utcnow()
    db.commit()
    return {"id": entidad_id, "comentario": texto}


@router.put("/api/comentarios/productos/{producto_id}")
def comentar_producto(producto_id: int, datos: TextoComentario, request: Request, db: Session = Depends(get_db)):
    return cambiar_comentario(request, db, ComentarioProducto, Producto, "producto_id", producto_id, datos.texto)


@router.delete("/api/comentarios/productos/{producto_id}")
def borrar_comentario_producto(producto_id: int, request: Request, db: Session = Depends(get_db)):
    return cambiar_comentario(request, db, ComentarioProducto, Producto, "producto_id", producto_id, None)


@router.put("/api/comentarios/tiendas/{tienda_id}")
def comentar_tienda(tienda_id: int, datos: TextoComentario, request: Request, db: Session = Depends(get_db)):
    return cambiar_comentario(request, db, ComentarioTienda, Tienda, "tienda_id", tienda_id, datos.texto)


@router.delete("/api/comentarios/tiendas/{tienda_id}")
def borrar_comentario_tienda(tienda_id: int, request: Request, db: Session = Depends(get_db)):
    return cambiar_comentario(request, db, ComentarioTienda, Tienda, "tienda_id", tienda_id, None)


def moderar_comentario(request, db, tipo, entidad_id, usuario_id, texto):
    admin = _obtener_usuario_actual(request, db)
    if admin.rol != RolUsuario.ADMIN:
        raise HTTPException(403, "Acceso exclusivo para administradores")
    _validar_csrf(request)
    modelo, clave = (ComentarioProducto, "producto_id") if tipo == "productos" else (ComentarioTienda, "tienda_id")
    comentario = db.query(modelo).filter_by(usuario_id=usuario_id, **{clave: entidad_id}).with_for_update().first()
    if comentario is None:
        raise HTTPException(404, "Comentario no encontrado")
    if texto is None:
        db.delete(comentario)
    else:
        comentario.texto = texto
        comentario.fecha_actualizacion = datetime.utcnow()
    db.commit()
    return {"id": entidad_id, "usuario_id": usuario_id, "comentario": texto}


@router.put("/api/admin/comentarios/{tipo}/{entidad_id}/{usuario_id}")
def editar_comentario_admin(tipo: Literal["productos", "tiendas"], entidad_id: int, usuario_id: int,
                           datos: TextoComentario, request: Request, db: Session = Depends(get_db)):
    return moderar_comentario(request, db, tipo, entidad_id, usuario_id, datos.texto)


@router.delete("/api/admin/comentarios/{tipo}/{entidad_id}/{usuario_id}")
def borrar_comentario_admin(tipo: Literal["productos", "tiendas"], entidad_id: int, usuario_id: int,
                           request: Request, db: Session = Depends(get_db)):
    return moderar_comentario(request, db, tipo, entidad_id, usuario_id, None)


def comprador(request, db):
    if not request.session.get("usuario"):
        return None
    usuario = _obtener_usuario_actual(request, db)
    if usuario.rol != RolUsuario.COMPRADOR:
        raise HTTPException(403, "El carrito está disponible para compradores e invitados")
    return usuario


def obtener_carrito(request, db, usuario):
    if usuario:
        return db.query(Carrito).filter_by(usuario_id=usuario.id).first()
    sesion = request.session.get("carrito_sesion")
    return db.query(Carrito).filter_by(usuario_id=None, sesion=sesion).first() if sesion else None


def cantidades_carrito(request, db, usuario):
    carrito = obtener_carrito(request, db, usuario)
    if carrito:
        return {str(item.producto_id): item.cantidad for item in carrito.items}
    return dict(request.session.get("carrito", {})) if not usuario else {}


def resumen_carrito(request, db, usuario):
    items = []
    for id_producto, cantidad in cantidades_carrito(request, db, usuario).items():
        producto = seleccionar(db, "", None, False).filter(Producto.id == int(id_producto)).first()
        if producto is None:
            items.append({"producto": {"id": int(id_producto), "nombre": "Producto retirado", "disponible": False,
                                     "precio": 0, "precio_oferta": None, "descuento": None},
                          "cantidad": cantidad, "subtotal": 0, "disponible": False})
            continue
        datos = producto_publico(producto)
        precio = datos["precio_oferta"] if datos["precio_oferta"] is not None else datos["precio"]
        items.append({"producto": datos, "cantidad": cantidad, "subtotal": round(precio * cantidad, 2),
                      "disponible": datos["disponible"] and cantidad <= producto.stock})
    return {"items": items, "total": round(sum(i["subtotal"] for i in items), 2),
            "cantidad": sum(i["cantidad"] for i in items)}


@router.get("/api/carrito")
def carrito_api(request: Request, db: Session = Depends(get_db)):
    return resumen_carrito(request, db, comprador(request, db))


@router.get("/carrito", response_class=HTMLResponse)
def pagina_carrito(request: Request, db: Session = Depends(get_db)):
    return pagina_publica(request, db, "carrito.html", resumen_carrito(request, db, comprador(request, db)))


class CantidadCarrito(BaseModel):
    cantidad: int = Field(ge=1, le=999, strict=True)


def cambiar_carrito(request, db, producto_id, cantidad, sumar=False):
    _validar_csrf(request)
    usuario = comprador(request, db)
    if usuario:
        # Serializa cambios del mismo comprador, incluida la creación del primer carrito.
        db.query(Usuario).filter_by(id=usuario.id).with_for_update().one()
    carrito = obtener_carrito(request, db, usuario)
    if carrito:
        db.query(Carrito).filter_by(id=carrito.id).with_for_update().one()
    cantidades = cantidades_carrito(request, db, usuario)
    nueva = cantidad + cantidades.get(str(producto_id), 0) if sumar else cantidad
    if nueva > 999:
        raise HTTPException(409, "La cantidad máxima por producto es 999")
    if nueva:
        producto = obtener_producto(db, producto_id)
        if not producto.disponible or nueva > producto.stock:
            raise HTTPException(409, "Producto no disponible o cantidad superior al stock")
        if str(producto_id) not in cantidades and len(cantidades) >= 50:
            raise HTTPException(409, "El carrito admite hasta 50 productos distintos")
    if carrito is None:
        sesion = None if usuario else secrets.token_urlsafe(32)
        carrito = Carrito(usuario_id=usuario.id if usuario else None, sesion=sesion)
        db.add(carrito)
        db.flush()
        if not usuario:
            request.session["carrito_sesion"] = sesion
            # Conserva los productos de las antiguas cestas almacenadas en la cookie.
            for anterior, unidades in cantidades.items():
                if db.get(Producto, int(anterior)):
                    db.add(ProductoCarrito(carrito_id=carrito.id, producto_id=int(anterior), cantidad=unidades))
            db.flush()
            request.session.pop("carrito", None)
    item = db.query(ProductoCarrito).filter_by(carrito_id=carrito.id, producto_id=producto_id).first()
    if not nueva:
        if item: db.delete(item)
    elif item:
        item.cantidad = nueva
    else:
        db.add(ProductoCarrito(carrito_id=carrito.id, producto_id=producto_id, cantidad=nueva))
    carrito.fecha_actualizacion = datetime.utcnow()
    db.commit()
    db.expire_all()
    return resumen_carrito(request, db, usuario)


@router.post("/api/carrito/productos/{producto_id}")
def agregar_carrito(producto_id: int, datos: CantidadCarrito, request: Request, db: Session = Depends(get_db)):
    return cambiar_carrito(request, db, producto_id, datos.cantidad, sumar=True)


@router.put("/api/carrito/productos/{producto_id}")
def actualizar_carrito(producto_id: int, datos: CantidadCarrito, request: Request, db: Session = Depends(get_db)):
    return cambiar_carrito(request, db, producto_id, datos.cantidad)


@router.delete("/api/carrito/productos/{producto_id}")
def quitar_carrito(producto_id: int, request: Request, db: Session = Depends(get_db)):
    return cambiar_carrito(request, db, producto_id, 0)


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


from app.routers.compra import router as compra_router
router.include_router(compra_router)
from app.routers.stripe_webhook import router as stripe_router
router.include_router(stripe_router)
