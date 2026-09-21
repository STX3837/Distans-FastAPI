
from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, Float, Numeric, ForeignKey, Text, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from geoalchemy2 import Geometry
from enum import Enum as PyEnum

Base = declarative_base()


class RolUsuario(PyEnum):
    """Roles disponibles para los usuarios"""
    COMPRADOR = "comprador"
    VENDEDOR = "vendedor"
    ADMIN = "admin"


class Categoria(PyEnum):
    """Categorías de productos disponibles"""
    CULTURA_OCIO = "Cultura y ocio"
    HOGAR_BRICOLAJE = "Hogar y bricolaje"
    SALUD_BIENESTAR = "Salud y bienestar"
    TECNOLOGIA_ELECTRONICA = "Tecnología y electrónica"
    FLORISTERIAS_JARDINERIA = "Floristerías y jardinería"
    ALIMENTACION_BEBIDAS = "Alimentación y bebidas"
    MODA_COMPLEMENTOS = "Moda y complementos"
    PAPELERIA_OFICINA = "Papelería y oficina"


class EstadoPedido(PyEnum):
    """Estados posibles de un pedido"""
    PREPARACION = "en preparacion"
    ENVIADO = "enviado"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"


class EstadoSubpedido(PyEnum):
    PREPARACION = "en preparacion"
    LISTO_PARA_RECOGER = "listo para recoger"
    RECOGIDO = "recogido"
    CANCELADO = "cancelado"


class MetodoPago(PyEnum):
    """Métodos de pago disponibles"""
    TARJETA_CREDITO = "tarjeta_credito"
    TARJETA_DEBITO = "tarjeta_debito"
    PAYPAL = "paypal"
    TRANSFERENCIA = "transferencia"
    EFECTIVO = "efectivo"


class Usuario(Base):
    """
    Entidad de Usuario según RI01
    Almacena los datos de los usuarios registrados:
    nombre, apellidos, email, teléfono, fecha de creación, 
    fecha de actualización, dirección, ciudad, código postal y contraseña.
    """
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    apellidos = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    telefono = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    ciudad = Column(String, nullable=True)
    codigo_postal = Column(String, nullable=True)
    
    # Contraseña cifrada según RNF02
    contrasena_hash = Column(String, nullable=False)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Rol del usuario (Comprador, Vendedor, Admin)
    rol = Column(Enum(RolUsuario), default=RolUsuario.COMPRADOR, nullable=False)
    
    # Campos administrativos
    activo = Column(Boolean, default=True, nullable=False)
    
    # Relaciones
    tiendas = relationship("Tienda", back_populates="vendedor", foreign_keys="Tienda.vendedor_id")
    carrito = relationship("Carrito", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="usuario", cascade="all, delete-orphan")


class RestablecimientoContrasena(Base):
    __tablename__ = "restablecimientos_contrasena"

    token_hash = Column(String(64), primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String, nullable=False)
    contrasena_anterior_hash = Column(String, nullable=False)
    fecha_expiracion = Column(DateTime, nullable=False)


class Ubicacion(Base):
    __tablename__ = "ubicaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    # Campo geométrico de PostGIS para un punto (Longitud, Latitud)
    punto = Column(Geometry(geometry_type='POINT', srid=4326))


class Tienda(Base):
    """
    Entidad de Tienda
    Almacena los datos de las tiendas de los vendedores:
    nombre, descripción, ubicación, dirección, horario, imagen.
    """
    __tablename__ = "tiendas"
    __table_args__ = (Index("uq_tiendas_vendedor_id", "vendedor_id", unique=True),)
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    ubicacion = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    horario = Column(String, nullable=True)
    imagen = Column(String, nullable=True)
    valoracion_media = Column(Float, nullable=True)
    
    # Vendedor que es dueño de la tienda
    vendedor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    vendedor = relationship("Usuario", back_populates="tiendas", foreign_keys=[vendedor_id])
    productos = relationship("Producto", back_populates="tienda", cascade="all, delete-orphan")
    coordenadas = relationship("CoordenadasTienda", back_populates="tienda", uselist=False, cascade="all, delete-orphan")
    @property
    def categorias(self):
        """Categorías únicas de todos los productos de la tienda."""
        return sorted({producto.categoria for producto in self.productos}, key=lambda categoria: categoria.value)


class CoordenadasTienda(Base):
    """Coordenadas geográficas para RF05, sin alterar las tiendas existentes."""
    __tablename__ = "coordenadas_tienda"
    tienda_id = Column(Integer, ForeignKey("tiendas.id", ondelete="CASCADE"), primary_key=True)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    tienda = relationship("Tienda", back_populates="coordenadas")
    __table_args__ = (
        CheckConstraint("latitud >= -90 AND latitud <= 90", name="latitud_valida"),
        CheckConstraint("longitud >= -180 AND longitud <= 180", name="longitud_valida"),
    )


class Producto(Base):
    """
    Entidad de Producto
    Almacena los datos de los productos disponibles en las tiendas:
    nombre, descripción, precio, precioOferta, imagen, disponible, 
    destacado, fechaCreacion, fechaActualizacion, marca, stock, categoría.
    """
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    precio = Column(Float, nullable=False)
    precio_oferta = Column(Float, nullable=True)
    valoracion_media = Column(Float, nullable=True)
    modalidad_compra = Column(String(10), nullable=False, default="presencial")
    imagen = Column(String, nullable=True)
    disponible = Column(Boolean, default=True, nullable=False)
    destacado = Column(Boolean, default=False, nullable=False)
    marca = Column(String, nullable=True)
    stock = Column(Integer, default=0, nullable=False)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Categoría del producto
    categoria = Column(Enum(Categoria), nullable=False)
    
    # Tienda que ofrece el producto
    tienda_id = Column(Integer, ForeignKey("tiendas.id"), nullable=False)
    
    # Relaciones
    tienda = relationship("Tienda", back_populates="productos")
    carrito_items = relationship("ProductoCarrito", back_populates="producto", cascade="all, delete-orphan")
    pedido_items = relationship("ProductoPedido", back_populates="producto", cascade="all, delete-orphan")


class ProductoFavorito(Base):
    __tablename__ = "productos_favoritos"
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), primary_key=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)


class TiendaFavorita(Base):
    __tablename__ = "tiendas_favoritas"
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    tienda_id = Column(Integer, ForeignKey("tiendas.id", ondelete="CASCADE"), primary_key=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)


class ValoracionProducto(Base):
    __tablename__ = "valoraciones_productos"
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), primary_key=True)
    puntuacion = Column(Integer, CheckConstraint("puntuacion >= 1 AND puntuacion <= 5"), nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ValoracionTienda(Base):
    __tablename__ = "valoraciones_tiendas"
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    tienda_id = Column(Integer, ForeignKey("tiendas.id", ondelete="CASCADE"), primary_key=True)
    puntuacion = Column(Integer, CheckConstraint("puntuacion >= 1 AND puntuacion <= 5"), nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ComentarioProducto(Base):
    __tablename__ = "comentarios_productos"
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), primary_key=True)
    texto = Column(Text, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    autor = relationship("Usuario")


class ComentarioTienda(Base):
    __tablename__ = "comentarios_tiendas"
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    tienda_id = Column(Integer, ForeignKey("tiendas.id", ondelete="CASCADE"), primary_key=True)
    texto = Column(Text, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    autor = relationship("Usuario")


class Carrito(Base):
    """
    Entidad de Carrito
    Almacena el carrito de compras del usuario:
    usuario, fechaCreacion, fechaActualizacion, sesión.
    """
    __tablename__ = "carritos"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Usuario propietario del carrito
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, unique=True)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    sesion = Column(String, nullable=True, unique=True)
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="carrito")
    items = relationship("ProductoCarrito", back_populates="carrito", cascade="all, delete-orphan")


class ProductoCarrito(Base):
    """
    Entidad de ProductoCarrito (tabla de unión)
    Almacena los productos en el carrito de compras:
    cantidad, fechaCreacion, fechaActualizacion.
    """
    __tablename__ = "productos_carrito"
    
    id = Column(Integer, primary_key=True, index=True)
    cantidad = Column(Integer, nullable=False, default=1)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Claves foráneas
    carrito_id = Column(Integer, ForeignKey("carritos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    
    # Relaciones
    carrito = relationship("Carrito", back_populates="items")
    producto = relationship("Producto", back_populates="carrito_items")


class Pedido(Base):
    """
    Entidad de Pedido
    Almacena los pedidos realizados por los usuarios:
    fecha, codigoPedido, estado, subtotal, impuesto, costeEntrega, total,
    metodosPago, direccionEnvio, direccionFacturacion, teléfono, 
    fechaCreacion, fechaActualizacion.
    """
    __tablename__ = "pedidos"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo_pedido = Column(String, unique=True, nullable=False, index=True)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Estados del pedido
    estado = Column(Enum(EstadoPedido), default=EstadoPedido.PREPARACION, nullable=False)
    
    # Detalles financieros
    subtotal = Column(Numeric(12, 2), nullable=False)
    descuento = Column(Numeric(12, 2), default=0, nullable=False)
    nombre_comprador = Column(String, nullable=False, default="")
    apellidos_comprador = Column(String, nullable=False, default="")
    email_comprador = Column(String, nullable=False, default="")
    moneda = Column(String(3), default="EUR", nullable=False)
    pago_completado = Column(Boolean, default=False, nullable=False)
    carrito_id = Column(Integer, ForeignKey("carritos.id", ondelete="SET NULL"), nullable=True)
    carrito_vaciado = Column(Boolean, default=False, nullable=False)
    stripe_session_id = Column(String, unique=True, nullable=True)
    reserva_expira = Column(DateTime, nullable=True)
    reserva_liberada = Column(Boolean, default=False, nullable=False)
    impuesto = Column(Numeric(12, 2), default=0, nullable=False)
    coste_entrega = Column(Numeric(12, 2), default=0, nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    importe_pago_original = Column(Numeric(12, 2), nullable=True)
    reembolso_pendiente = Column(Numeric(12, 2), default=0, nullable=False)
    
    # Información de envío y facturación
    metodo_pago = Column(Enum(MetodoPago), nullable=False)
    direccion_envio = Column(String, nullable=False)
    direccion_facturacion = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Usuario que realiza el pedido
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="pedidos")
    items = relationship("ProductoPedido", back_populates="pedido", cascade="all, delete-orphan")
    subpedidos = relationship("Subpedido", back_populates="pedido", cascade="all, delete-orphan")


class Subpedido(Base):
    """Productos y progreso de una tienda dentro de un pedido."""
    __tablename__ = "subpedidos"
    __table_args__ = (UniqueConstraint("pedido_id", "tienda_id", name="uq_subpedido_pedido_tienda"),)

    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True)
    tienda_id = Column(Integer, ForeignKey("tiendas.id"), nullable=False)
    estado = Column(Enum(EstadoSubpedido), default=EstadoSubpedido.PREPARACION, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    pedido = relationship("Pedido", back_populates="subpedidos")
    items = relationship("ProductoPedido", back_populates="subpedido")


class ProductoPedido(Base):
    """
    Entidad de ProductoPedido (tabla de unión)
    Almacena los productos en un pedido:
    cantidad, precioUnitario, fechaCreacion, fechaActualizacion, total.
    """
    __tablename__ = "productos_pedido"
    
    id = Column(Integer, primary_key=True, index=True)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Claves foráneas
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    subpedido_id = Column(Integer, ForeignKey("subpedidos.id"), nullable=False, index=True)
    cancelado = Column(Boolean, default=False, nullable=False)
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto", back_populates="pedido_items")
    subpedido = relationship("Subpedido", back_populates="items")
