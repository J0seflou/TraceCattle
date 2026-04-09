import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres"
    )

    @property
    def db_url(self) -> str:
        """Convierte la URL de Railway al formato que SQLAlchemy necesita."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "trace-cattle-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Umbrales biométricos
    SIGNATURE_THRESHOLD: float = 0.75
    FACE_THRESHOLD: float = 0.70
    VOICE_THRESHOLD: float = 0.70

    # Directorio de archivos
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
