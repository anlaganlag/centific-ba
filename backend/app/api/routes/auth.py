from fastapi import APIRouter, HTTPException, status, Depends
from jose import JWTError
import bcrypt

from app.models.user import UserCreate, UserLogin, UserResponse
from app.auth.models import TokenResponse, CurrentUser
from app.auth.jwt_service import create_access_token, create_refresh_token, verify_token
from app.auth.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


@router.post("/register", response_model=TokenResponse)
async def register(data: UserCreate):
    db = get_db()
    existing = db.get_user_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    password_hash = hash_password(data.password)
    user = db.create_user(data.email, data.display_name, password_hash)

    return TokenResponse(
        access_token=create_access_token(user["id"], user["email"]),
        refresh_token=create_refresh_token(user["id"], user["email"]),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    db = get_db()
    user = db.get_user_by_email(data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(
        access_token=create_access_token(user["id"], user["email"]),
        refresh_token=create_refresh_token(user["id"], user["email"]),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str):
    try:
        token_data = verify_token(refresh_token, expected_type="refresh")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    db = get_db()
    user = db.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user["id"], user["email"]),
        refresh_token=create_refresh_token(user["id"], user["email"]),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    user = db.get_user_by_id(current_user.user_id)
    return UserResponse(
        id=user["id"],
        email=user["email"],
        display_name=user["display_name"],
        created_at=user["created_at"],
    )
