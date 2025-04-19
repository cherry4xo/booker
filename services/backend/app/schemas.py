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


class UserCreated(BaseModel):
    uuid: UUID4
    username: str
    email: EmailStr


class UserGet(BaseModel):
    uuid: UUID4
    username: str
    email: EmailStr
    telegram_id: Optional[str] = None
    role: Optional[str] = None


class UserChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class UserGrantPrivileges(BaseModel):
    uuid: UUID4
    role: str


class CreateEquipment(BaseModel):
    name: str
    description: str


class GetEquipment(BaseModel):
    uuid: UUID4
    name: str
    description: str


class UpdateEquipment(BaseModel):
    uuid: UUID4
    name: Optional[str] = None
    description: Optional[str] = None


class DeleteEquipment(BaseModel):
    uuid: UUID4


class CreateAuditorium(BaseModel):
    identifier: str
    capacity: str
    description: str


class GetAuditorium(BaseModel):
    uuid: UUID4
    identifier: str
    capacity: str
    description: str


class UpdateAuditorium(BaseModel):
    uuid: UUID4
    identifier: Optional[str] = None
    capacity: Optional[str] = None
    description: Optional[str] = None

class DeleteAuditorium(BaseModel):
    uuid: UUID4


class CreateAvailability(BaseModel):
    uuid: UUID4
    auditorium: UUID4
    day_of_week: int
    start_time: datetime
    end_time: datetime


class GetAvailability(BaseModel):
    uuid: UUID4
    auditorium: UUID4
    day_of_week: int
    start_time: datetime
    end_time: datetime


class UpdateAvailability(BaseModel):
    uuid: UUID4
    auditorium: Optional[UUID4] = None
    day_of_week: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class DeleteAvailability(BaseModel):
    uuid: UUID4


class CreateBooking(BaseModel):
    uuid: UUID4
    auditorium: UUID4
    start_time: datetime
    end_time: datetime
    title: Optional[str] = None


class GetBooking(BaseModel):
    uuid: UUID4
    auditorium: Optional[UUID4] = None
    booker: Optional[UUID4] = None
    start_time: datetime
    end_time: datetime
    title: Optional[str] = None


class UpdateBooking(BaseModel):
    uuid: UUID4
    auditorium: Optional[UUID4] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    title: Optional[str] = None


class DeleteBooking(BaseModel):
    uuid: UUID4