from __future__ import annotations

from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    username: str
    password: str

class UserInDB(User):
    hashed_password: str

class AsanaName(BaseModel):
    name_ru: str
    name_en: str
    name_sanskrit: str

class AsanaSource(BaseModel):
    author: str
    year: int
    title: str
