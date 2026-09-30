from passlib.context import CryptContext

# PBKDF2-SHA256 es el esquema de hash elegido para contraseñas.
# Evita dependencia directa de bcrypt y mantiene un algoritmo robusto y ampliamente soportado.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto", pbkdf2_sha256__default_rounds=600_000)


def hash_password(password: str) -> str:
    """
    Genera un hash de contraseña con salt aleatoria.
    Según RNF02: La contraseña debe almacenarse de forma cifrada y segura.
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash seguro de la contraseña
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica una contraseña contra su hash.
    
    Args:
        plain_password: Contraseña en texto plano a verificar
        hashed_password: Hash almacenado en la base de datos
        
    Returns:
        True si la contraseña coincide, False en caso contrario
    """
    return pwd_context.verify(plain_password, hashed_password)
