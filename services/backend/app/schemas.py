import uuid
from typing import Optional
from datetime import date, datetime, time

from pydantic import BaseModel, UUID4, ConfigDict, EmailStr, Field, field_validator


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
    capacity: int = Field(..., gt=0) # Изменен тип на int, добавлена валидация
    description: Optional[str] = None # Сделаем description опциональным при создании


class GetAuditorium(BaseModel):
    uuid: UUID4
    identifier: str
    capacity: int # Изменен тип на int
    description: Optional[str] = None # Сделаем опциональным и здесь

    model_config = ConfigDict(from_attributes=True)


class UpdateAuditorium(BaseModel):
    # uuid в Pydantic схеме для PATCH/PUT избыточен, если он есть в URL
    # Сделаем его опциональным или уберем
    uuid: Optional[UUID4] = None # Сделаем опциональным
    identifier: Optional[str] = None
    capacity: Optional[int] = Field(None, gt=0) # Изменен тип на int, добавлена валидация
    description: Optional[str] = None

class DeleteAuditorium(BaseModel):
    uuid: UUID4


class CreateAvailability(BaseModel):
    # UUID обычно генерируется сервером
    # uuid: UUID4
    auditorium: UUID4
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: time # Изменен тип на time
    end_time: time   # Изменен тип на time


class GetAvailability(BaseModel):
    uuid: UUID4
    auditorium_id: UUID4 # Возвращаем ID аудитории
    day_of_week: int
    start_time: time # Изменен тип на time
    end_time: time   # Изменен тип на time

    model_config = ConfigDict(from_attributes=True)


class UpdateAvailability(BaseModel):
    # uuid: UUID4 # Избыточен, если есть в URL
    auditorium: Optional[UUID4] = None # Позволяем менять аудиторию? Редко нужно.
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[time] = None # Изменен тип на time
    end_time: Optional[time] = None   # Изменен тип на time


class DeleteAvailability(BaseModel):
    uuid: UUID4



class CreateBooking(BaseModel):
    auditorium: UUID4
    start_time: datetime
    end_time: datetime
    title: Optional[str] = None

    # Добавим валидатор времени
    @field_validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        if 'start_time' in values.data and v <= values.data['start_time']:
            raise ValueError('Booking end time must be after start time')
        return v


class GetBooking(BaseModel):
    uuid: UUID4
    auditorium_id: UUID4 = Field(..., alias="auditorium") # Маппинг поля модели auditorium -> auditorium_id
    broker_id: UUID4 = Field(..., alias="booker") # Маппинг поля модели broker -> broker_id
    start_time: datetime
    end_time: datetime
    title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True) 


class UpdateBooking(BaseModel):
    auditorium: Optional[UUID4] = None # Позволяем менять аудиторию
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    title: Optional[str] = None


class DeleteBooking(BaseModel):
    uuid: UUID4