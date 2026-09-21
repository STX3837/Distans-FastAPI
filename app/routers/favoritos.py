"""Favoritos persistentes de compradores (RF30)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Producto, ProductoFavorito, RolUsuario, Tienda, TiendaFavorita, Usuario
from app.routers.auth import _validar_csrf
from app.routers.catalogo import pagina_publica, producto_publico
from app.routers.users import _obtener_usuario_actual

router = APIRouter(tags=["favoritos"])


def comprador(request: Request, db: Session):
    usuario = _obtener_usuario_actual(request, db)
    if usuario.rol != RolUsuario.COMPRADOR:
        raise HTTPException(403, "Los favoritos son exclusivos de compradores")
    return usuario


def visibles(db):
    return db.query(Tienda.id).join(Usuario, Tienda.vendedor_id == Usuario.id).filter(Usuario.activo.is_(True))


def resumen(db, usuario):
    tiendas = (db.query(Tienda).join(TiendaFavorita, Tienda.id == TiendaFavorita.tienda_id)
               .join(Usuario, Tienda.vendedor_id == Usuario.id)
               .filter(TiendaFavorita.usuario_id == usuario.id, Usuario.activo.is_(True))
               .order_by(TiendaFavorita.fecha_creacion.desc(), Tienda.id.desc()).all())
    productos = (db.query(Producto).join(ProductoFavorito, Producto.id == ProductoFavorito.producto_id)
                 .filter(ProductoFavorito.usuario_id == usuario.id, Producto.tienda_id.in_(visibles(db)))
                 .options(joinedload(Producto.tienda).joinedload(Tienda.coordenadas))
                 .order_by(ProductoFavorito.fecha_creacion.desc(), Producto.id.desc()).all())
    return {
        "productos": [producto_publico(p) for p in productos],
        "tiendas": [{"id": t.id, "nombre": t.nombre, "direccion": t.direccion,
                     "ubicacion": t.ubicacion, "imagen": t.imagen if t.imagen and
                     (t.imagen.startswith(("https://", "http://")) or
                      (t.imagen.startswith("/") and not t.imagen.startswith("//"))) else None}
                    for t in tiendas],
    }


@router.get("/api/favoritos")
def listar(request: Request, db: Session = Depends(get_db)):
    return resumen(db, comprador(request, db))


@router.get("/favoritos", response_class=HTMLResponse)
def pagina(request: Request, db: Session = Depends(get_db)):
    return pagina_publica(request, db, "favoritos.html", resumen(db, comprador(request, db)))


def cambiar(request, db, modelo, clave, entidad, id_objeto, guardar):
    usuario = comprador(request, db)
    _validar_csrf(request)
    if guardar and not db.query(entidad).filter(entidad.id == id_objeto).filter(
            entidad.tienda_id.in_(visibles(db)) if entidad is Producto else entidad.id.in_(visibles(db))).first():
        raise HTTPException(404, "Elemento no encontrado")
    favorito = db.get(modelo, (usuario.id, id_objeto))
    if guardar and favorito is None:
        db.add(modelo(usuario_id=usuario.id, **{clave: id_objeto}))
    elif not guardar and favorito is not None:
        db.delete(favorito)
    db.commit()
    return {"favorito": guardar, "tipo": "producto" if entidad is Producto else "tienda", "id": id_objeto}


@router.put("/api/favoritos/productos/{producto_id}")
def guardar_producto(producto_id: int, request: Request, db: Session = Depends(get_db)):
    return cambiar(request, db, ProductoFavorito, "producto_id", Producto, producto_id, True)


@router.delete("/api/favoritos/productos/{producto_id}")
def quitar_producto(producto_id: int, request: Request, db: Session = Depends(get_db)):
    return cambiar(request, db, ProductoFavorito, "producto_id", Producto, producto_id, False)


@router.put("/api/favoritos/tiendas/{tienda_id}")
def guardar_tienda(tienda_id: int, request: Request, db: Session = Depends(get_db)):
    return cambiar(request, db, TiendaFavorita, "tienda_id", Tienda, tienda_id, True)


@router.delete("/api/favoritos/tiendas/{tienda_id}")
def quitar_tienda(tienda_id: int, request: Request, db: Session = Depends(get_db)):
    return cambiar(request, db, TiendaFavorita, "tienda_id", Tienda, tienda_id, False)
