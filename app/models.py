from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, Float, ForeignKey, Text
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
    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    ENVIADO = "enviado"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"
    DEVUELTO = "devuelto"


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
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    ubicacion = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    horario = Column(String, nullable=True)
    imagen = Column(String, nullable=True)
    
    # Vendedor que es dueño de la tienda
    vendedor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    vendedor = relationship("Usuario", back_populates="tiendas", foreign_keys=[vendedor_id])
    productos = relationship("Producto", back_populates="tienda", cascade="all, delete-orphan")


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


class Carrito(Base):
    """
    Entidad de Carrito
    Almacena el carrito de compras del usuario:
    usuario, fechaCreacion, fechaActualizacion, sesión.
    """
    __tablename__ = "carritos"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Usuario propietario del carrito
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    sesion = Column(String, nullable=True)
    
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
    estado = Column(Enum(EstadoPedido), default=EstadoPedido.PENDIENTE, nullable=False)
    
    # Detalles financieros
    subtotal = Column(Float, nullable=False)
    impuesto = Column(Float, default=0.0, nullable=False)
    coste_entrega = Column(Float, default=0.0, nullable=False)
    total = Column(Float, nullable=False)
    
    # Información de envío y facturación
    metodo_pago = Column(Enum(MetodoPago), nullable=False)
    direccion_envio = Column(String, nullable=False)
    direccion_facturacion = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Usuario que realiza el pedido
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="pedidos")
    items = relationship("ProductoPedido", back_populates="pedido", cascade="all, delete-orphan")


class ProductoPedido(Base):
    """
    Entidad de ProductoPedido (tabla de unión)
    Almacena los productos en un pedido:
    cantidad, precioUnitario, fechaCreacion, fechaActualizacion, total.
    """
    __tablename__ = "productos_pedido"
    
    id = Column(Integer, primary_key=True, index=True)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Claves foráneas
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto", back_populates="pedido_items")
