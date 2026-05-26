"""
Tests para verificar todas las entidades y sus relaciones según el Modelo Conceptual.

Verifica:
- Creación de todas las entidades (Usuario, Tienda, Producto, Carrito, ProductoCarrito, Pedido, ProductoPedido)
- Relaciones 1:N y M:M correctamente configuradas
- Composiciones: Producto (Tienda), ProductoCarrito (Carrito), ProductoPedido (Pedido)
- Cascadas de eliminación
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models import (
    Usuario, Tienda, Producto, Carrito, ProductoCarrito, Pedido, ProductoPedido,
    RolUsuario, Categoria, EstadoPedido, MetodoPago, Base
)


# Crear un engine de SQLite en memoria para testing
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="function")
def db_session():
    """Fixture para crear una sesión de base de datos limpia para cada test."""
    # Crear todas las tablas (ignorar errores de GeoAlchemy2 en SQLite)
    try:
        Base.metadata.create_all(bind=test_engine)
    except Exception as e:
        # GeoAlchemy2 no funciona con SQLite, pero no afecta a nuestros tests
        if "RecoverGeometryColumn" not in str(e):
            raise

    session = TestSessionLocal()
    yield session

    # Limpiar después de cada test (ignorar errores de GeoAlchemy2 en SQLite)
    session.close()
    try:
        Base.metadata.drop_all(bind=test_engine)
    except Exception as e:
        # GeoAlchemy2 no funciona con SQLite, pero no afecta a nuestros tests
        if "CheckSpatialIndex" not in str(e):
            raise


class TestUsuarioEntity:
    """Tests para la entidad Usuario."""
    
    def test_crear_usuario_comprador(self, db_session):
        """Verifica la creación de un usuario comprador."""
        usuario = Usuario(
            nombre="Juan",
            apellidos="García López",
            email="juan@example.com",
            telefono="666123456",
            direccion="Calle Principal 123",
            ciudad="Madrid",
            codigo_postal="28001",
            contrasena_hash="hashed_password",
            rol=RolUsuario.COMPRADOR,
            activo=True
        )
        db_session.add(usuario)
        db_session.commit()
        
        assert usuario.id is not None
        assert usuario.nombre == "Juan"
        assert usuario.rol == RolUsuario.COMPRADOR
        assert usuario.activo is True
        assert usuario.fecha_creacion is not None
        print(f"✓ Usuario Comprador creado: {usuario.nombre} ({usuario.email})")
    
    def test_crear_usuario_vendedor(self, db_session):
        """Verifica la creación de un usuario vendedor."""
        usuario = Usuario(
            nombre="María",
            apellidos="Rodríguez Pérez",
            email="maria@example.com",
            telefono="655987654",
            direccion="Avenida Central 456",
            ciudad="Barcelona",
            codigo_postal="08001",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR,
            activo=True
        )
        db_session.add(usuario)
        db_session.commit()
        
        assert usuario.rol == RolUsuario.VENDEDOR
        print(f"✓ Usuario Vendedor creado: {usuario.nombre} ({usuario.email})")
    
    def test_crear_usuario_admin(self, db_session):
        """Verifica la creación de un usuario administrador."""
        usuario = Usuario(
            nombre="Admin",
            apellidos="System",
            email="admin@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.ADMIN,
            activo=True
        )
        db_session.add(usuario)
        db_session.commit()
        
        assert usuario.rol == RolUsuario.ADMIN
        print(f"✓ Usuario Admin creado: {usuario.nombre}")


class TestTiendaEntity:
    """Tests para la entidad Tienda."""
    
    def test_crear_tienda_sin_vendedor(self, db_session):
        """Verifica que se puede intentar crear una tienda (falla sin vendedor)."""
        # Esto debería fallar porque vendedor_id es obligatorio
        tienda = Tienda(
            nombre="Mi Tienda",
            descripcion="Tienda de ejemplo",
            ubicacion="Madrid",
            direccion="Calle Principal 123",
            horario="09:00-21:00",
            imagen="tienda.jpg",
            vendedor_id=None  # Esto causará error
        )
        db_session.add(tienda)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
        print("✓ Validación: Tienda requiere vendedor")
    
    def test_crear_tienda_con_vendedor(self, db_session):
        """Verifica la creación de una tienda con vendedor."""
        # Crear vendedor
        vendedor = Usuario(
            nombre="María",
            apellidos="Rodríguez",
            email="maria@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR
        )
        db_session.add(vendedor)
        db_session.flush()
        
        # Crear tienda
        tienda = Tienda(
            nombre="Tienda de María",
            descripcion="Tienda especializada en tecnología",
            ubicacion="Barcelona, Spain",
            direccion="Avenida Gaudí 100",
            horario="10:00-20:00",
            imagen="tienda_maria.jpg",
            vendedor_id=vendedor.id
        )
        db_session.add(tienda)
        db_session.commit()
        
        assert tienda.id is not None
        assert tienda.vendedor_id == vendedor.id
        assert tienda.nombre == "Tienda de María"
        print(f"✓ Tienda creada: {tienda.nombre} (Vendedor: {vendedor.nombre})")
    
    def test_relacion_usuario_tiendas_uno_a_muchos(self, db_session):
        """Verifica relación 1:N entre Usuario y Tienda."""
        # Crear vendedor
        vendedor = Usuario(
            nombre="Carlos",
            apellidos="González",
            email="carlos@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR
        )
        db_session.add(vendedor)
        db_session.flush()
        
        # Crear múltiples tiendas para el mismo vendedor
        tienda1 = Tienda(
            nombre="Tienda 1",
            vendedor_id=vendedor.id
        )
        tienda2 = Tienda(
            nombre="Tienda 2",
            vendedor_id=vendedor.id
        )
        db_session.add_all([tienda1, tienda2])
        db_session.commit()
        
        # Verificar relación inversa
        assert len(vendedor.tiendas) == 2
        assert tienda1 in vendedor.tiendas
        assert tienda2 in vendedor.tiendas
        print(f"✓ Relación Usuario→Tiendas (1:N): {len(vendedor.tiendas)} tiendas para {vendedor.nombre}")


class TestProductoEntity:
    """Tests para la entidad Producto."""
    
    def test_crear_producto_en_tienda(self, db_session):
        """Verifica la creación de un producto en una tienda."""
        # Crear vendedor y tienda
        vendedor = Usuario(
            nombre="Ana",
            apellidos="López",
            email="ana@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR
        )
        db_session.add(vendedor)
        db_session.flush()
        
        tienda = Tienda(
            nombre="Tienda de Ana",
            vendedor_id=vendedor.id
        )
        db_session.add(tienda)
        db_session.flush()
        
        # Crear producto
        producto = Producto(
            nombre="Laptop",
            descripcion="Laptop de alta gama",
            precio=1200.00,
            precio_oferta=1000.00,
            imagen="laptop.jpg",
            disponible=True,
            destacado=True,
            marca="Dell",
            stock=5,
            categoria=Categoria.TECNOLOGIA_ELECTRONICA,
            tienda_id=tienda.id
        )
        db_session.add(producto)
        db_session.commit()
        
        assert producto.id is not None
        assert producto.tienda_id == tienda.id
        assert producto.categoria == Categoria.TECNOLOGIA_ELECTRONICA
        assert producto.precio == 1200.00
        print(f"✓ Producto creado: {producto.nombre} en {tienda.nombre}")
    
    def test_composicion_producto_tienda(self, db_session):
        """Verifica la composición: Producto es parte de Tienda (cascade delete)."""
        # Crear vendedor y tienda
        vendedor = Usuario(
            nombre="Pedro",
            apellidos="Martínez",
            email="pedro@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR
        )
        db_session.add(vendedor)
        db_session.flush()
        
        tienda = Tienda(
            nombre="Tienda de Pedro",
            vendedor_id=vendedor.id
        )
        db_session.add(tienda)
        db_session.flush()
        
        # Crear múltiples productos en la tienda
        producto1 = Producto(
            nombre="Producto 1",
            precio=10.00,
            categoria=Categoria.CULTURA_OCIO,
            tienda_id=tienda.id
        )
        producto2 = Producto(
            nombre="Producto 2",
            precio=20.00,
            categoria=Categoria.HOGAR_BRICOLAJE,
            tienda_id=tienda.id
        )
        db_session.add_all([producto1, producto2])
        db_session.commit()
        
        tienda_id = tienda.id
        productos_count = len(tienda.productos)
        assert productos_count == 2
        print(f"✓ Tienda tiene {productos_count} productos")
        
        # Eliminar la tienda (composición: productos se deben eliminar en cascada)
        db_session.delete(tienda)
        db_session.commit()
        
        # Verificar que los productos se eliminaron
        productos_restantes = db_session.query(Producto).filter_by(tienda_id=tienda_id).all()
        assert len(productos_restantes) == 0
        print("✓ Composición Producto←Tienda verificada: Productos eliminados al eliminar Tienda")
    
    def test_relacion_tienda_productos_uno_a_muchos(self, db_session):
        """Verifica relación 1:N entre Tienda y Producto."""
        # Crear tienda
        vendedor = Usuario(
            nombre="Laura",
            apellidos="García",
            email="laura@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR
        )
        db_session.add(vendedor)
        db_session.flush()
        
        tienda = Tienda(
            nombre="Tienda de Laura",
            vendedor_id=vendedor.id
        )
        db_session.add(tienda)
        db_session.flush()
        
        # Crear productos con diferentes categorías
        categorias = [
            Categoria.CULTURA_OCIO,
            Categoria.TECNOLOGIA_ELECTRONICA,
            Categoria.MODA_COMPLEMENTOS
        ]
        
        for i, categoria in enumerate(categorias):
            producto = Producto(
                nombre=f"Producto {i+1}",
                precio=10.00 * (i+1),
                categoria=categoria,
                tienda_id=tienda.id
            )
            db_session.add(producto)
        
        db_session.commit()
        
        assert len(tienda.productos) == 3
        print(f"✓ Relación Tienda→Productos (1:N): {len(tienda.productos)} productos en tienda")


class TestCarritoYProductoCarrito:
    """Tests para la entidad Carrito y ProductoCarrito."""
    
    def test_crear_carrito_para_usuario(self, db_session):
        """Verifica la creación de un carrito para un usuario."""
        # Crear comprador
        comprador = Usuario(
            nombre="Juan",
            apellidos="García",
            email="juan@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.COMPRADOR
        )
        db_session.add(comprador)
        db_session.flush()
        
        # Crear carrito
        carrito = Carrito(
            usuario_id=comprador.id,
            sesion="session_123"
        )
        db_session.add(carrito)
        db_session.commit()
        
        assert carrito.id is not None
        assert carrito.usuario_id == comprador.id
        assert carrito.sesion == "session_123"
        print(f"✓ Carrito creado para usuario: {comprador.nombre}")
    
    def test_relacion_usuario_carrito_uno_a_uno(self, db_session):
        """Verifica relación 1:1 entre Usuario y Carrito."""
        # Crear comprador
        comprador = Usuario(
            nombre="María",
            apellidos="López",
            email="maria@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.COMPRADOR
        )
        db_session.add(comprador)
        db_session.flush()
        
        # Crear carrito
        carrito = Carrito(
            usuario_id=comprador.id
        )
        db_session.add(carrito)
        db_session.commit()
        
        # Verificar relación
        assert comprador.carrito is not None
        assert comprador.carrito.id == carrito.id
        print("✓ Relación Usuario←→Carrito (1:1) verificada")
    
    def test_agregar_productos_a_carrito(self, db_session):
        """Verifica agregar productos al carrito (composición)."""
        # Crear usuario, vendedor, tienda y productos
        comprador = Usuario(
            nombre="Carlos",
            apellidos="López",
            email="carlos@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.COMPRADOR
        )
        db_session.add(comprador)
        db_session.flush()
        
        vendedor = Usuario(
            nombre="Ana",
            apellidos="García",
            email="ana@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR
        )
        db_session.add(vendedor)
        db_session.flush()
        
        tienda = Tienda(
            nombre="Tienda Ana",
            vendedor_id=vendedor.id
        )
        db_session.add(tienda)
        db_session.flush()
        
        producto1 = Producto(
            nombre="Producto A",
            precio=10.00,
            categoria=Categoria.CULTURA_OCIO,
            tienda_id=tienda.id
        )
        producto2 = Producto(
            nombre="Producto B",
            precio=20.00,
            categoria=Categoria.HOGAR_BRICOLAJE,
            tienda_id=tienda.id
        )
        db_session.add_all([producto1, producto2])
        db_session.flush()
        
        # Crear carrito
        carrito = Carrito(
            usuario_id=comprador.id
        )
        db_session.add(carrito)
        db_session.flush()
        
        # Agregar productos al carrito
        item1 = ProductoCarrito(
            cantidad=2,
            carrito_id=carrito.id,
            producto_id=producto1.id
        )
        item2 = ProductoCarrito(
            cantidad=1,
            carrito_id=carrito.id,
            producto_id=producto2.id
        )
        db_session.add_all([item1, item2])
        db_session.commit()
        
        assert len(carrito.items) == 2
        assert carrito.items[0].cantidad == 2
        assert carrito.items[1].producto.nombre == "Producto B"
        print(f"✓ Carrito tiene {len(carrito.items)} productos")
    
    def test_composicion_producto_carrito(self, db_session):
        """Verifica la composición: ProductoCarrito es parte de Carrito (cascade delete)."""
        # Crear usuario, carrito y productos en carrito
        comprador = Usuario(
            nombre="David",
            apellidos="López",
            email="david@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.COMPRADOR
        )
        db_session.add(comprador)
        db_session.flush()
        
        vendedor = Usuario(
            nombre="Elena",
            apellidos="García",
            email="elena@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR
        )
        db_session.add(vendedor)
        db_session.flush()
        
        tienda = Tienda(
            nombre="Tienda Elena",
            vendedor_id=vendedor.id
        )
        db_session.add(tienda)
        db_session.flush()
        
        producto = Producto(
            nombre="Producto X",
            precio=50.00,
            categoria=Categoria.TECNOLOGIA_ELECTRONICA,
            tienda_id=tienda.id
        )
        db_session.add(producto)
        db_session.flush()
        
        carrito = Carrito(
            usuario_id=comprador.id
        )
        db_session.add(carrito)
        db_session.flush()
        
        item = ProductoCarrito(
            cantidad=3,
            carrito_id=carrito.id,
            producto_id=producto.id
        )
        db_session.add(item)
        db_session.commit()
        
        carrito_id = carrito.id
        items_count = len(carrito.items)
        assert items_count == 1
        print(f"✓ Carrito contiene {items_count} item")
        
        # Eliminar carrito (composición: items se deben eliminar en cascada)
        db_session.delete(carrito)
        db_session.commit()
        
        # Verificar que los items se eliminaron
        items_restantes = db_session.query(ProductoCarrito).filter_by(carrito_id=carrito_id).all()
        assert len(items_restantes) == 0
        print("✓ Composición ProductoCarrito←Carrito verificada: Items eliminados al eliminar Carrito")


class TestPedidoYProductoPedido:
    """Tests para la entidad Pedido y ProductoPedido."""
    
    def test_crear_pedido(self, db_session):
        """Verifica la creación de un pedido."""
        # Crear comprador
        comprador = Usuario(
            nombre="Felipe",
            apellidos="López",
            email="felipe@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.COMPRADOR
        )
        db_session.add(comprador)
        db_session.flush()
        
        # Crear pedido
        pedido = Pedido(
            codigo_pedido="PED-001",
            fecha=datetime.utcnow(),
            estado=EstadoPedido.PENDIENTE,
            subtotal=100.00,
            impuesto=21.00,
            coste_entrega=10.00,
            total=131.00,
            metodo_pago=MetodoPago.TARJETA_CREDITO,
            direccion_envio="Calle Principal 123, Madrid",
            direccion_facturacion="Calle Principal 123, Madrid",
            telefono="666123456",
            usuario_id=comprador.id
        )
        db_session.add(pedido)
        db_session.commit()
        
        assert pedido.id is not None
        assert pedido.codigo_pedido == "PED-001"
        assert pedido.estado == EstadoPedido.PENDIENTE
        assert pedido.total == 131.00
        print(f"✓ Pedido creado: {pedido.codigo_pedido}")
    
    def test_agregar_productos_a_pedido(self, db_session):
        """Verifica agregar productos a un pedido (composición)."""
        # Crear comprador
        comprador = Usuario(
            nombre="Gonzalo",
            apellidos="García",
            email="gonzalo@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.COMPRADOR
        )
        db_session.add(comprador)
        db_session.flush()
        
        # Crear vendedor, tienda y productos
        vendedor = Usuario(
            nombre="Francisca",
            apellidos="López",
            email="francisca@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR
        )
        db_session.add(vendedor)
        db_session.flush()
        
        tienda = Tienda(
            nombre="Tienda Francisca",
            vendedor_id=vendedor.id
        )
        db_session.add(tienda)
        db_session.flush()
        
        producto1 = Producto(
            nombre="Producto M",
            precio=50.00,
            categoria=Categoria.MODA_COMPLEMENTOS,
            tienda_id=tienda.id
        )
        producto2 = Producto(
            nombre="Producto N",
            precio=30.00,
            categoria=Categoria.ALIMENTACION_BEBIDAS,
            tienda_id=tienda.id
        )
        db_session.add_all([producto1, producto2])
        db_session.flush()
        
        # Crear pedido
        pedido = Pedido(
            codigo_pedido="PED-002",
            estado=EstadoPedido.CONFIRMADO,
            subtotal=80.00,
            impuesto=16.80,
            coste_entrega=5.00,
            total=101.80,
            metodo_pago=MetodoPago.PAYPAL,
            direccion_envio="Avenida Central 456, Barcelona",
            direccion_facturacion="Avenida Central 456, Barcelona",
            usuario_id=comprador.id
        )
        db_session.add(pedido)
        db_session.flush()
        
        # Agregar productos al pedido
        item1 = ProductoPedido(
            cantidad=1,
            precio_unitario=50.00,
            total=50.00,
            pedido_id=pedido.id,
            producto_id=producto1.id
        )
        item2 = ProductoPedido(
            cantidad=1,
            precio_unitario=30.00,
            total=30.00,
            pedido_id=pedido.id,
            producto_id=producto2.id
        )
        db_session.add_all([item1, item2])
        db_session.commit()
        
        assert len(pedido.items) == 2
        assert pedido.items[0].cantidad == 1
        assert pedido.items[1].producto.nombre == "Producto N"
        print(f"✓ Pedido contiene {len(pedido.items)} productos")
    
    def test_composicion_producto_pedido(self, db_session):
        """Verifica la composición: ProductoPedido es parte de Pedido (cascade delete)."""
        # Crear comprador
        comprador = Usuario(
            nombre="Helena",
            apellidos="García",
            email="helena@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.COMPRADOR
        )
        db_session.add(comprador)
        db_session.flush()
        
        # Crear vendedor, tienda y producto
        vendedor = Usuario(
            nombre="Iván",
            apellidos="López",
            email="ivan@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR
        )
        db_session.add(vendedor)
        db_session.flush()
        
        tienda = Tienda(
            nombre="Tienda Iván",
            vendedor_id=vendedor.id
        )
        db_session.add(tienda)
        db_session.flush()
        
        producto = Producto(
            nombre="Producto Z",
            precio=100.00,
            categoria=Categoria.SALUD_BIENESTAR,
            tienda_id=tienda.id
        )
        db_session.add(producto)
        db_session.flush()
        
        # Crear pedido
        pedido = Pedido(
            codigo_pedido="PED-003",
            estado=EstadoPedido.ENVIADO,
            subtotal=100.00,
            impuesto=21.00,
            coste_entrega=0.00,
            total=121.00,
            metodo_pago=MetodoPago.TRANSFERENCIA,
            direccion_envio="Dirección 789, Valencia",
            direccion_facturacion="Dirección 789, Valencia",
            usuario_id=comprador.id
        )
        db_session.add(pedido)
        db_session.flush()
        
        # Agregar producto al pedido
        item = ProductoPedido(
            cantidad=1,
            precio_unitario=100.00,
            total=100.00,
            pedido_id=pedido.id,
            producto_id=producto.id
        )
        db_session.add(item)
        db_session.commit()
        
        pedido_id = pedido.id
        items_count = len(pedido.items)
        assert items_count == 1
        print(f"✓ Pedido contiene {items_count} item")
        
        # Eliminar pedido (composición: items se deben eliminar en cascada)
        db_session.delete(pedido)
        db_session.commit()
        
        # Verificar que los items se eliminaron
        items_restantes = db_session.query(ProductoPedido).filter_by(pedido_id=pedido_id).all()
        assert len(items_restantes) == 0
        print("✓ Composición ProductoPedido←Pedido verificada: Items eliminados al eliminar Pedido")
    
    def test_relacion_usuario_pedidos_uno_a_muchos(self, db_session):
        """Verifica relación 1:N entre Usuario y Pedido."""
        # Crear comprador
        comprador = Usuario(
            nombre="Julio",
            apellidos="García",
            email="julio@example.com",
            contrasena_hash="hashed_password",
            rol=RolUsuario.COMPRADOR
        )
        db_session.add(comprador)
        db_session.flush()
        
        # Crear múltiples pedidos
        pedido1 = Pedido(
            codigo_pedido="PED-004",
            estado=EstadoPedido.ENTREGADO,
            subtotal=50.00,
            total=60.50,
            metodo_pago=MetodoPago.EFECTIVO,
            direccion_envio="Dir 1",
            direccion_facturacion="Dir 1",
            usuario_id=comprador.id
        )
        pedido2 = Pedido(
            codigo_pedido="PED-005",
            estado=EstadoPedido.CANCELADO,
            subtotal=75.00,
            total=90.75,
            metodo_pago=MetodoPago.TARJETA_DEBITO,
            direccion_envio="Dir 2",
            direccion_facturacion="Dir 2",
            usuario_id=comprador.id
        )
        db_session.add_all([pedido1, pedido2])
        db_session.commit()
        
        assert len(comprador.pedidos) == 2
        assert pedido1 in comprador.pedidos
        assert pedido2 in comprador.pedidos
        print(f"✓ Relación Usuario→Pedidos (1:N): {len(comprador.pedidos)} pedidos para {comprador.nombre}")


class TestIntegracionCompleta:
    """Tests de integración completa del modelo."""
    
    def test_flujo_completo_ecommerce(self, db_session):
        """Verifica un flujo completo de compra en el ecommerce."""
        print("\n=== FLUJO COMPLETO DE ECOMMERCE ===")
        
        # 1. Crear usuarios (Comprador y Vendedor)
        print("\n1. Creando usuarios...")
        comprador = Usuario(
            nombre="Juan",
            apellidos="García López",
            email="juan.garcia@example.com",
            telefono="666123456",
            direccion="Calle Principal 123",
            ciudad="Madrid",
            codigo_postal="28001",
            contrasena_hash="hashed_password",
            rol=RolUsuario.COMPRADOR
        )
        
        vendedor = Usuario(
            nombre="María",
            apellidos="Rodríguez Pérez",
            email="maria.rodriguez@example.com",
            telefono="655987654",
            direccion="Avenida Central 456",
            ciudad="Barcelona",
            codigo_postal="08001",
            contrasena_hash="hashed_password",
            rol=RolUsuario.VENDEDOR
        )
        db_session.add_all([comprador, vendedor])
        db_session.flush()
        print(f"   ✓ Comprador: {comprador.nombre} ({comprador.email})")
        print(f"   ✓ Vendedor: {vendedor.nombre} ({vendedor.email})")
        
        # 2. Crear tienda
        print("\n2. Creando tienda del vendedor...")
        tienda = Tienda(
            nombre="TechStore María",
            descripcion="Tienda especializada en tecnología de última generación",
            ubicacion="Barcelona, Spain",
            direccion="Avenida Gaudí 100",
            horario="10:00-21:00",
            imagen="techstore.jpg",
            vendedor_id=vendedor.id
        )
        db_session.add(tienda)
        db_session.flush()
        print(f"   ✓ Tienda: {tienda.nombre}")
        
        # 3. Crear productos en la tienda
        print("\n3. Creando productos...")
        productos_data = [
            ("Laptop Dell XPS 13", "Laptop de alta gama ultraportátil", 1299.99, 1099.99, Categoria.TECNOLOGIA_ELECTRONICA),
            ("Mouse Logitech MX", "Mouse inalámbrico de precisión", 99.99, None, Categoria.TECNOLOGIA_ELECTRONICA),
            ("Teclado Mecánico RGB", "Teclado mecánico con switches Cherry", 149.99, 119.99, Categoria.TECNOLOGIA_ELECTRONICA),
            ("Monitor LG 27\"", "Monitor 4K de 27 pulgadas", 399.99, None, Categoria.TECNOLOGIA_ELECTRONICA),
        ]
        
        productos = []
        for nombre, desc, precio, precio_oferta, categoria in productos_data:
            producto = Producto(
                nombre=nombre,
                descripcion=desc,
                precio=precio,
                precio_oferta=precio_oferta,
                disponible=True,
                destacado=precio_oferta is not None,
                marca="Tech Brand",
                stock=10,
                categoria=categoria,
                tienda_id=tienda.id
            )
            db_session.add(producto)
            productos.append(producto)
            print(f"   ✓ {nombre} - ${precio}")
        
        db_session.flush()
        
        # 4. Crear carrito para el comprador
        print("\n4. Creando carrito para comprador...")
        carrito = Carrito(
            usuario_id=comprador.id,
            sesion="session_abc123"
        )
        db_session.add(carrito)
        db_session.flush()
        print(f"   ✓ Carrito creado (sesión: {carrito.sesion})")
        
        # 5. Agregar productos al carrito
        print("\n5. Agregando productos al carrito...")
        items_carrito = [
            (productos[0], 1),  # Laptop x1
            (productos[1], 2),  # Mouse x2
            (productos[2], 1),  # Teclado x1
        ]
        
        total_carrito = 0
        for producto, cantidad in items_carrito:
            item = ProductoCarrito(
                cantidad=cantidad,
                carrito_id=carrito.id,
                producto_id=producto.id
            )
            db_session.add(item)
            total_carrito += producto.precio_oferta or producto.precio * cantidad
            print(f"   ✓ {producto.nombre} x{cantidad}")
        
        db_session.flush()
        print(f"   Total carrito: ${total_carrito:.2f}")
        
        # 6. Crear pedido basado en el carrito
        print("\n6. Creando pedido desde carrito...")
        subtotal = total_carrito
        impuesto = subtotal * 0.21  # 21% IVA
        coste_entrega = 9.99
        total_pedido = subtotal + impuesto + coste_entrega
        
        pedido = Pedido(
            codigo_pedido="PED-2026-001",
            fecha=datetime.utcnow(),
            estado=EstadoPedido.PENDIENTE,
            subtotal=subtotal,
            impuesto=impuesto,
            coste_entrega=coste_entrega,
            total=total_pedido,
            metodo_pago=MetodoPago.TARJETA_CREDITO,
            direccion_envio=f"{comprador.direccion}, {comprador.ciudad}",
            direccion_facturacion=f"{comprador.direccion}, {comprador.ciudad}",
            telefono=comprador.telefono,
            usuario_id=comprador.id
        )
        db_session.add(pedido)
        db_session.flush()
        print(f"   ✓ Pedido: {pedido.codigo_pedido}")
        print(f"   Subtotal: ${pedido.subtotal:.2f}")
        print(f"   IVA (21%): ${pedido.impuesto:.2f}")
        print(f"   Envío: ${pedido.coste_entrega:.2f}")
        print(f"   Total: ${pedido.total:.2f}")
        
        # 7. Agregar items del carrito al pedido
        print("\n7. Agregando productos al pedido...")
        for item_carrito in carrito.items:
            item_pedido = ProductoPedido(
                cantidad=item_carrito.cantidad,
                precio_unitario=item_carrito.producto.precio_oferta or item_carrito.producto.precio,
                total=item_carrito.cantidad * (item_carrito.producto.precio_oferta or item_carrito.producto.precio),
                pedido_id=pedido.id,
                producto_id=item_carrito.producto_id
            )
            db_session.add(item_pedido)
            print(f"   ✓ {item_carrito.producto.nombre} x{item_carrito.cantidad}")
        
        db_session.commit()
        
        # 8. Verificar relaciones
        print("\n8. Verificando todas las relaciones...")
        assert len(carrito.items) == 3
        assert len(pedido.items) == 3
        assert comprador.carrito is not None
        assert len(comprador.pedidos) == 1
        assert len(vendedor.tiendas) == 1
        assert len(tienda.productos) == 4
        print("   ✓ Todas las relaciones verificadas correctamente")
        
        # 9. Cambiar estado del pedido
        print("\n9. Actualizando estado del pedido...")
        pedido.estado = EstadoPedido.CONFIRMADO
        db_session.commit()
        print(f"   ✓ Pedido actualizado a: {pedido.estado.value}")
        
        print("\n=== FLUJO COMPLETADO EXITOSAMENTE ===\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
