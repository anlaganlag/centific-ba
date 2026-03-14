from pydantic import BaseModel
from typing import Optional


class TokenData(BaseModel):
    user_id: str
    email: str


class CurrentUser(BaseModel):
    user_id: str
    email: str
    display_name: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
