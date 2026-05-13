from passlib.context import CryptContext

# Use bcrypt_sha256 to allow arbitrary-length passwords (pre-hashes with SHA-256)
# Use PBKDF2-SHA256 to avoid bcrypt 72-byte limitation and external bcrypt dependency
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Cifra una contraseña en texto plano.
    Según RNF02: La contraseña debe almacenarse de forma cifrada y segura.
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash seguro de la contraseña
    """
    # Passlib's bcrypt_sha256 pre-hashes with SHA-256, avoiding bcrypt 72-byte limit
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
