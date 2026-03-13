from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from .jwt_service import verify_token
from .models import CurrentUser
from app.services.db_service import DatabaseService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_db: DatabaseService | None = None


def get_db() -> DatabaseService:
    global _db
    if _db is None:
        from app.config import settings
        _db = DatabaseService(settings.DATABASE_PATH)
    return _db


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = verify_token(token, expected_type="access")
    except JWTError:
        raise credentials_exception

    db = get_db()
    user = db.get_user_by_id(token_data.user_id)
    if user is None:
        raise credentials_exception

    return CurrentUser(
        user_id=user["id"],
        email=user["email"],
        display_name=user["display_name"],
    )
