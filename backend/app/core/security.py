from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_INSECURE_DEFAULT_SECRET = "fleetflow-local-development-key-change-this-before-production"
# A local-development fallback keeps the one-command launcher usable before a
# .env file exists. Production validates that it has been replaced at startup.
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    _INSECURE_DEFAULT_SECRET,
)
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
)


def validate_production_security() -> None:
    """Reject known or short JWT signing keys in a production process."""
    if os.getenv("ENVIRONMENT", "development").lower() != "production":
        return
    if SECRET_KEY == _INSECURE_DEFAULT_SECRET or len(SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY must be a unique value of at least 32 characters in production.")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
