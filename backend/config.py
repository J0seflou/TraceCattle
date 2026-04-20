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

    # JWT — SECRET_KEY debe definirse en .env con un valor aleatorio de 256 bits (V-002)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "trace-cattle-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    @property
    def validated_secret_key(self) -> str:
        """Devuelve SECRET_KEY y lanza error si sigue siendo el valor por defecto."""
        _insecure_default = "trace-cattle-secret-key-change-in-production"
        if self.SECRET_KEY == _insecure_default:
            raise RuntimeError(
                "SECRET_KEY no ha sido cambiada. "
                "Define una clave aleatoria en .env: "
                "python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self.SECRET_KEY

    # AES-256 — cifrado de plantillas biométricas
    # AES_KEY debe ser una cadena hexadecimal de exactamente 64 caracteres (32 bytes).
    # El valor por defecto es SOLO para desarrollo local. En producción define AES_KEY en .env
    AES_KEY_HEX: str = os.getenv(
        "AES_KEY",
        "5472616365436174746c655f4145533235365f4465763332427974654b657921",  # TraceCattle_AES256_Dev32ByteKey!
    )

    @property
    def aes_key(self) -> bytes:
        """Clave AES-256 como 32 bytes. AES_KEY_HEX debe tener 64 caracteres hex."""
        hex_val = self.AES_KEY_HEX
        if len(hex_val) != 64:
            raise ValueError(
                f"AES_KEY debe tener 64 caracteres hexadecimales (32 bytes). "
                f"Longitud actual: {len(hex_val)}"
            )
        return bytes.fromhex(hex_val)

    # Umbrales biométricos
    SIGNATURE_THRESHOLD: float = 0.10
    FACE_THRESHOLD: float = 0.70
    VOICE_THRESHOLD: float = 0.70

    # Directorio de archivos
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    # Administrador del sistema
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@tracecattle.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin2024*")

    # Email / SMTP
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    # Si SMTP_FROM no está definido, usar el mismo correo autenticado (requerido por Gmail)
    SMTP_FROM: str = os.getenv("SMTP_FROM", "") or os.getenv("SMTP_USER", "no-reply@tracecattle.com")
    # Minutos de validez del código de cambio biométrico
    CODIGO_CAMBIO_EXPIRA_MINUTOS: int = 10

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
