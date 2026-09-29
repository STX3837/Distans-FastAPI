"""Punto de entrada exclusivo para preparar el esquema antes de servir HTTP."""
from app.database import engine
from app.migrations import actualizar_base


if __name__ == "__main__":
    actualizar_base(engine)
