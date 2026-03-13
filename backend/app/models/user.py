from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: str
    password: str
    display_name: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: str
