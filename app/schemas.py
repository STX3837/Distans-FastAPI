from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, List
from enum import Enum


class RolUsuario(str, Enum):
    """Roles disponibles para los usuarios"""
    COMPRADOR = "comprador"
    VENDEDOR = "vendedor"
    ADMIN = "admin"


class Categoria(str, Enum):
    """Categorías de productos disponibles"""
    CULTURA_OCIO = "Cultura y ocio"
    HOGAR_BRICOLAJE = "Hogar y bricolaje"
    SALUD_BIENESTAR = "Salud y bienestar"
    TECNOLOGIA_ELECTRONICA = "Tecnología y electrónica"
    FLORISTERIAS_JARDINERIA = "Floristerías y jardinería"
    ALIMENTACION_BEBIDAS = "Alimentación y bebidas"
    MODA_COMPLEMENTOS = "Moda y complementos"
    PAPELERIA_OFICINA = "Papelería y oficina"


class EstadoPedido(str, Enum):
    """Estados posibles de un pedido"""
    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    ENVIADO = "enviado"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"
    DEVUELTO = "devuelto"


class MetodoPago(str, Enum):
    """Métodos de pago disponibles"""
    TARJETA_CREDITO = "tarjeta_credito"
    TARJETA_DEBITO = "tarjeta_debito"
    PAYPAL = "paypal"
    TRANSFERENCIA = "transferencia"
    EFECTIVO = "efectivo"


# ===== USUARIO SCHEMAS =====

class UsuarioBase(BaseModel):
    """Campos básicos de usuario"""
    nombre: str = Field(min_length=1)
    apellidos: str = Field(min_length=1)
    email: EmailStr
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    codigo_postal: Optional[str] = None

    @field_validator("nombre", "apellidos", "email", mode="before")
    @classmethod
    def validar_identidad(cls, value):
        if value is None or not str(value).strip():
            raise ValueError("Este campo no puede estar vacío")
        return str(value).strip()


class UsuarioCreate(UsuarioBase):
    """Schema para crear un usuario con contraseña"""
    contrasena: str = Field(min_length=8, max_length=128)  # Contraseña en texto plano
    rol: Optional[RolUsuario] = RolUsuario.COMPRADOR  # Rol por defecto: Comprador


class UsuarioRegistro(UsuarioCreate):
    """RF27: datos de contacto y dirección obligatorios en el registro público."""
    telefono: str = Field(min_length=1)
    direccion: str = Field(min_length=1)
    ciudad: str = Field(min_length=1)
    codigo_postal: str = Field(min_length=1)

    @field_validator("telefono", "direccion", "ciudad", "codigo_postal", mode="before")
    @classmethod
    def validar_datos_comprador(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Este dato del comprador es obligatorio")
        return value.strip()


class DatosCompradorPago(UsuarioBase):
    """Datos de la cuenta reutilizables al completar el pago; no incluye credenciales."""
    telefono: str = Field(min_length=1)
    direccion: str = Field(min_length=1)
    ciudad: str = Field(min_length=1)
    codigo_postal: str = Field(min_length=1)

    model_config = ConfigDict(from_attributes=True)


class UsuarioAdminCreate(UsuarioCreate):
    activo: bool = True


class UsuarioUpdate(BaseModel):
    """Schema para actualizar datos del usuario - RF28"""
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    codigo_postal: Optional[str] = None

    @field_validator("nombre", "apellidos", "email", mode="before")
    @classmethod
    def validar_identidad(cls, value):
        if value is None or not str(value).strip():
            raise ValueError("Este campo no puede estar vacío")
        return str(value).strip()


class UsuarioCambiarContrasena(BaseModel):
    """Schema para cambiar contraseña"""
    contrasena_actual: str
    contrasena_nueva: str = Field(min_length=8, max_length=128)


class UsuarioResponse(UsuarioBase):
    """Schema para respuesta de usuario - sin contraseña"""
    id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    rol: RolUsuario
    activo: bool
    
    class Config:
        from_attributes = True


class UsuarioAdminUpdate(BaseModel):
    """Schema para actualizar usuario como administrador - RF32"""
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    codigo_postal: Optional[str] = None
    rol: Optional[RolUsuario] = None
    activo: Optional[bool] = None

    @field_validator("nombre", "apellidos", "email", mode="before")
    @classmethod
    def validar_identidad(cls, value):
        if value is None or not str(value).strip():
            raise ValueError("Este campo no puede estar vacío")
        return str(value).strip()


class UsuarioAdminResponse(UsuarioBase):
    """Schema para respuesta de usuario en vista de administrador - RF32"""
    id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    rol: RolUsuario
    activo: bool
    
    class Config:
        from_attributes = True


# ===== TIENDA SCHEMAS =====

class TiendaBase(BaseModel):
    """Campos básicos de tienda"""
    nombre: str
    descripcion: Optional[str] = None
    ubicacion: Optional[str] = None
    direccion: Optional[str] = None
    horario: Optional[str] = None
    imagen: Optional[str] = None


class TiendaCreate(TiendaBase):
    """Schema para crear una tienda"""
    pass


class TiendaUpdate(BaseModel):
    """Schema para actualizar una tienda"""
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    ubicacion: Optional[str] = None
    direccion: Optional[str] = None
    horario: Optional[str] = None
    imagen: Optional[str] = None


class TiendaResponse(TiendaBase):
    """Schema para respuesta de tienda"""
    id: int
    vendedor_id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    
    class Config:
        from_attributes = True


# ===== PRODUCTO SCHEMAS =====

class ProductoBase(BaseModel):
    """Campos básicos de producto"""
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    precio_oferta: Optional[float] = None
    imagen: Optional[str] = None
    disponible: bool = True
    destacado: bool = False
    marca: Optional[str] = None
    stock: int = 0
    categoria: Categoria


class ProductoCreate(ProductoBase):
    """Schema para crear un producto"""
    tienda_id: int


class ProductoUpdate(BaseModel):
    """Schema para actualizar un producto"""
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    precio_oferta: Optional[float] = None
    imagen: Optional[str] = None
    disponible: Optional[bool] = None
    destacado: Optional[bool] = None
    marca: Optional[str] = None
    stock: Optional[int] = None
    categoria: Optional[Categoria] = None


class ProductoResponse(ProductoBase):
    """Schema para respuesta de producto"""
    id: int
    tienda_id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    
    class Config:
        from_attributes = True


# ===== PRODUCTO CARRITO SCHEMAS =====

class ProductoCarritoBase(BaseModel):
    """Campos básicos de producto en carrito"""
    cantidad: int = 1
    producto_id: int


class ProductoCarritoCreate(ProductoCarritoBase):
    """Schema para agregar producto al carrito"""
    pass


class ProductoCarritoUpdate(BaseModel):
    """Schema para actualizar cantidad de producto en carrito"""
    cantidad: int


class ProductoCarritoResponse(ProductoCarritoBase):
    """Schema para respuesta de producto en carrito"""
    id: int
    carrito_id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    producto: Optional[ProductoResponse] = None
    
    class Config:
        from_attributes = True


# ===== CARRITO SCHEMAS =====

class CarritoBase(BaseModel):
    """Campos básicos de carrito"""
    sesion: Optional[str] = None


class CarritoCreate(CarritoBase):
    """Schema para crear un carrito"""
    pass


class CarritoResponse(CarritoBase):
    """Schema para respuesta de carrito"""
    id: int
    usuario_id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    items: List[ProductoCarritoResponse] = []
    
    class Config:
        from_attributes = True


# ===== PRODUCTO PEDIDO SCHEMAS =====

class ProductoPedidoBase(BaseModel):
    """Campos básicos de producto en pedido"""
    cantidad: int
    precio_unitario: float
    total: float
    producto_id: int


class ProductoPedidoResponse(ProductoPedidoBase):
    """Schema para respuesta de producto en pedido"""
    id: int
    pedido_id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    producto: Optional[ProductoResponse] = None
    
    class Config:
        from_attributes = True


# ===== PEDIDO SCHEMAS =====

class PedidoBase(BaseModel):
    """Campos básicos de pedido"""
    codigo_pedido: str
    estado: EstadoPedido = EstadoPedido.PENDIENTE
    subtotal: float
    impuesto: float = 0.0
    coste_entrega: float = 0.0
    total: float
    metodo_pago: MetodoPago
    direccion_envio: str
    direccion_facturacion: str
    telefono: Optional[str] = None


class PedidoCreate(BaseModel):
    """Schema para crear un pedido"""
    metodo_pago: MetodoPago
    direccion_envio: str
    direccion_facturacion: str
    telefono: Optional[str] = None
    impuesto: float = 0.0
    coste_entrega: float = 0.0


class PedidoUpdate(BaseModel):
    """Schema para actualizar estado de pedido"""
    estado: Optional[EstadoPedido] = None
    direccion_envio: Optional[str] = None
    direccion_facturacion: Optional[str] = None
    telefono: Optional[str] = None


class PedidoResponse(PedidoBase):
    """Schema para respuesta de pedido"""
    id: int
    usuario_id: Optional[int] = None
    descuento: float = 0
    nombre_comprador: str = ""
    apellidos_comprador: str = ""
    email_comprador: str = ""
    moneda: str = "EUR"
    pago_completado: bool = False
    fecha: datetime
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    items: List[ProductoPedidoResponse] = []
    
    class Config:
        from_attributes = True
