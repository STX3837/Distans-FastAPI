from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models import Usuario, RolUsuario
from app.schemas import UsuarioCreate, UsuarioUpdate, UsuarioAdminUpdate
from app.security import hash_password, verify_password
from typing import Optional, List


def crear_usuario(db: Session, usuario: UsuarioCreate) -> Usuario:
    """
    Crea un nuevo usuario en la base de datos.
    
    Args:
        db: Sesión de base de datos
        usuario: Datos del usuario a crear
        
    Returns:
        Usuario creado
    """
    # Convertir el rol entrante al Enum del modelo para respetar el tipo ENUM en BD.
    rol_entrada = usuario.rol.value if hasattr(usuario.rol, 'value') else usuario.rol
    if isinstance(rol_entrada, RolUsuario):
        rol_db = rol_entrada
    elif isinstance(rol_entrada, str):
        try:
            rol_db = RolUsuario(rol_entrada.lower())
        except ValueError as error:
            raise ValueError("Rol no válido") from error
    else:
        rol_db = RolUsuario.COMPRADOR

    usuario_bd = Usuario(
        nombre=usuario.nombre,
        apellidos=usuario.apellidos,
        email=usuario.email,
        telefono=usuario.telefono,
        direccion=usuario.direccion,
        ciudad=usuario.ciudad,
        codigo_postal=usuario.codigo_postal,
        contrasena_hash=hash_password(usuario.contrasena),
        rol=rol_db,
    )
    db.add(usuario_bd)
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise ValueError("No se pudo crear el usuario") from error
    db.refresh(usuario_bd)
    return usuario_bd


def obtener_usuario_por_id(db: Session, usuario_id: int) -> Optional[Usuario]:
    """Obtiene un usuario por su ID"""
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


def obtener_usuario_por_email(db: Session, email: str) -> Optional[Usuario]:
    """Obtiene un usuario por su email"""
    return db.query(Usuario).filter(Usuario.email == email).first()


def obtener_todos_usuarios(db: Session, skip: int = 0, limit: int = 100) -> List[Usuario]:
    """Obtiene todos los usuarios con paginación"""
    return db.query(Usuario).offset(skip).limit(limit).all()


def actualizar_usuario(db: Session, usuario_id: int, datos_actualizacion: UsuarioUpdate) -> Optional[Usuario]:
    """
    Actualiza datos del usuario (RF28 - Vista de usuario).
    El usuario solo puede actualizar ciertos campos de su perfil.
    """
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        return None
    
    # Actualizar solo los campos permitidos
    datos_dict = datos_actualizacion.dict(exclude_unset=True)
    for campo, valor in datos_dict.items():
        if valor is not None:
            setattr(usuario, campo, valor)
    
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_usuario_admin(db: Session, usuario_id: int, datos_actualizacion: UsuarioAdminUpdate) -> Optional[Usuario]:
    """
    Actualiza datos del usuario como administrador (RF32).
    El administrador puede actualizar todos los campos incluido es_administrador y activo.
    """
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        return None
    
    datos_dict = datos_actualizacion.dict(exclude_unset=True)
    for campo, valor in datos_dict.items():
        if valor is not None:
            setattr(usuario, campo, valor)
    
    db.commit()
    db.refresh(usuario)
    return usuario


def cambiar_contrasena(db: Session, usuario_id: int, contrasena_actual: str, contrasena_nueva: str) -> bool:
    """
    Cambia la contraseña de un usuario.
    Verifica que la contraseña actual sea correcta.
    """
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        return False
    
    # Verificar contraseña actual
    if not verify_password(contrasena_actual, usuario.contrasena_hash):
        return False
    
    # Actualizar con nueva contraseña cifrada
    usuario.contrasena_hash = hash_password(contrasena_nueva)
    db.commit()
    return True


def eliminar_usuario(db: Session, usuario_id: int) -> bool:
    """
    Elimina un usuario de la base de datos (RF32 - Admin).
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID del usuario a eliminar
        
    Returns:
        True si se eliminó exitosamente, False si no existe
    """
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        return False
    
    db.delete(usuario)
    db.commit()
    return True


def autenticar_usuario(db: Session, email: str, contrasena: str) -> Optional[Usuario]:
    """
    Autentica un usuario verificando email y contraseña.
    
    Args:
        db: Sesión de base de datos
        email: Email del usuario
        contrasena: Contraseña en texto plano
        
    Returns:
        Usuario si la autenticación es exitosa, None en caso contrario
    """
    usuario = obtener_usuario_por_email(db, email)
    if not usuario:
        return None
    
    if not verify_password(contrasena, usuario.contrasena_hash):
        return None
    
    return usuario
