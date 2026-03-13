from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.config import settings
from .models import TokenData


def create_access_token(user_id: str, email: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": expires,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, email: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "refresh",
        "exp": expires,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str, expected_type: str = "access") -> TokenData:
    """Verify and decode JWT token. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    token_type = payload.get("type")
    if token_type != expected_type:
        raise JWTError(f"Expected {expected_type} token, got {token_type}")
    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise JWTError("Invalid token payload")
    return TokenData(user_id=user_id, email=email)
