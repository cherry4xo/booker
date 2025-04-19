import uuid
from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel, UUID4, EmailStr


class BaseUser(BaseModel):
    uuid: Optional[UUID4] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    telegram_id: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str 