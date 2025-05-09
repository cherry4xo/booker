import uuid
from typing import List, Optional, TYPE_CHECKING
from datetime import date, datetime, time

from app.enums import UserRole

from pydantic import BaseModel, UUID4, ConfigDict, EmailStr, Field, field_validator


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BaseUser(BaseSchema):
    uuid: Optional[UUID4] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    telegram_id: Optional[str] = None
    role: Optional[UserRole] = None


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str 


class UserCreated(BaseSchema):
    uuid: UUID4
    username: str
    email: EmailStr
    registration_date: date
    role: UserRole

    class Config:
        orm_mode = True


class UserGet(BaseSchema):
    uuid: UUID4
    username: str
    email: EmailStr
    registration_date: date
    telegram_id: Optional[str] = None
    role: Optional[str] = None

    class Config:
        orm_mode = True


class UserUpdateProfile(BaseModel): # Схема для PATCH /users/me
    # Добавьте другие поля, которые пользователь может редактировать
    telegram_id: Optional[str] = None


class UserChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class UserGrantPrivileges(BaseModel):
    role: UserRole # Роль передается в теле

    @field_validator('role')
    def role_must_be_valid(cls, v):
        if v not in UserRole.list():
            raise ValueError(f"Invalid role. Must be one of: {UserRole.list()}")
        return v


class CreateEquipment(BaseModel):
    name: str
    description: Optional[str] = None 


class GetEquipment(BaseSchema):
    uuid: UUID4
    name: str
    description: Optional[str] = None

    class Config:
        orm_mode = True


class UpdateEquipment(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DeleteEquipment(BaseModel):
    uuid: UUID4


class CreateAuditorium(BaseModel):
    identifier: str
    capacity: int = Field(..., gt=0)
    description: Optional[str] = None
    equipment_uuids: Optional[List[UUID4]] = Field(None, description="List of equipment UUIDs to associate")


class GetAuditorium(BaseSchema):
    uuid: UUID4
    identifier: str
    capacity: int # int
    description: Optional[str] = None
    # Если нужно возвращать связанное оборудование
    equipment: List[GetEquipment] = [] # Потребует prefetch_related в сервисе


class UpdateAuditorium(BaseModel):
    identifier: Optional[str] = None
    capacity: Optional[int] = Field(None, gt=0)
    description: Optional[str] = None
    equipment_uuids: Optional[List[UUID4]] = Field(None, description="List of equipment UUIDs to set (replaces existing)")


class DeleteAuditorium(BaseModel):
    uuid: UUID4


class CreateAvailability(BaseModel):
    auditorium: UUID4 # ID аудитории, к которой добавляем слот
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: time # time
    end_time: time   # time

    # Валидатор для времени
    @field_validator('end_time')
    def check_end_time(cls, v, values):
        if 'start_time' in values.data and v != time(0,0) and v <= values.data['start_time']:
             # Разрешаем 00:00 как конец дня
            raise ValueError('End time must be after start time (unless it is 00:00)')
        return v


class GetAvailability(BaseSchema):
    uuid: UUID4
    auditorium_id: UUID4 # = Field(..., alias="auditorium") # Если поле в модели auditorium
    day_of_week: int
    start_time: time # time
    end_time: time   # time


class CalendarBookingEntry(BaseSchema):
    """
    Упрощенная схема бронирования для отображения в календаре.
    Поля 'start' и 'end' часто используются в библиотеках календарей.
    """
    uuid: UUID4 = Field(..., description="Уникальный идентификатор бронирования")
    title: Optional[str] = Field(None, description="Название/описание бронирования (может быть пустым)")
    start: datetime = Field(..., description="Время начала бронирования")
    end: datetime = Field(..., description="Время окончания бронирования")


class UpdateAvailability(BaseModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[time] = None # time
    end_time: Optional[time] = None   # time


class DeleteAvailability(BaseModel):
    uuid: UUID4



class CreateBooking(BaseModel):
    auditorium: UUID4
    start_time: datetime
    end_time: datetime
    title: Optional[str] = None

    @field_validator('end_time')
    def check_booking_end_time(cls, v, values):
        # Используем values.data для доступа к данным модели в Pydantic v2
        if 'start_time' in values.data and v <= values.data['start_time']:
            raise ValueError('Booking end time must be after start time')
        return v


class GetBooking(BaseSchema):
    uuid: UUID4
    auditorium_id: UUID4 = Field(..., alias="auditorium") # Указываем alias для поля auditorium модели
    broker_id: UUID4 = Field(..., alias="broker") # Указываем alias для поля broker модели
    start_time: datetime
    end_time: datetime
    title: Optional[str] = None


class UpdateBooking(BaseModel):
    auditorium: Optional[UUID4] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    title: Optional[str] = None


class DeleteBooking(BaseModel):
    uuid: UUID4


class JWTTokenPayload(BaseModel):
    user_uuid: UUID4 = None
    token_kind: str = None