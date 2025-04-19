
from datetime import date
import enum
from typing import Optional
from datetime import datetime

from pydantic import UUID4
from tortoise import fields
from tortoise.models import Model
from tortoise.exceptions import DoesNotExist

from app.utils import password
from app.schemas import UserCreate, CreateEquipment, CreateAuditorium, CreateAvailability, CreateBooking
from app.enums import UserRole


class BaseModel(Model):
    async def to_dict(self):
        d = {}
        for field in self._meta.db_fields:
            d[field] = getattr(self, field)
        for field in self._meta.backward_fk_fields:
            d[field] = await getattr(self, field).all().values()
        return d
    
    class Meta:
        abstract = True


class TimestampMixin:
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class User(TimestampMixin, BaseModel):
    uuid = fields.UUIDField(pk=True)
    username = fields.CharField(max_length=255, unique=True, null=True)
    email = fields.CharField(max_length=255, unique=True, null=True)
    password_hash = fields.CharField(max_length=255, null=True)
    registration_date = fields.DateField(auto_now_add=True)
    telegram_id = fields.CharField(max_length=255, null=True)
    role = fields.CharEnumField(UserRole, default=UserRole.BOOKER, description="User role")

    @classmethod
    async def create(cls, user: UserCreate) -> "User":
        user_dict = user.model_dump(exclude=["password"])
        password_hash = password.get_password_hash(password=user.password)
        model = cls(**user_dict, password_hash=password_hash, registration_date=date.today())
        return model
    
    @classmethod
    async def get_by_uuid(cls, uuid: UUID4) -> "User":
        try:
            query = cls.get_or_none(uuid=uuid)
            user = await query
            return user
        except DoesNotExist:
            return None

    @classmethod
    async def get_by_username(cls, username: str) -> Optional["User"]:
        try:
            query = cls.get_or_none(username=username)
            user = await query
            return user
        except DoesNotExist:
            return None
        
    @classmethod 
    async def get_by_email(cls, email: str) -> Optional["User"]:
        try:
            query = cls.get_or_none(email=email)
            user = await query
            return user
        except DoesNotExist:
            return None

    def __str__(self):
        return f"{self.username} ({self.role.value})"

    class Meta:
        table = "users"
        ordering = ["username"]


class Equipment(BaseModel):
    uuid = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)

    @classmethod
    async def create(cls, equipment: CreateEquipment) -> "Equipment":
        equipment_dict = equipment.model_dump()
        equipment = cls(**equipment_dict)
        await equipment.save()
        return equipment

    @classmethod
    async def get_by_name(cls, name: str) -> Optional["Equipment"]:
        try:
            query = cls.get_or_none(name=name)
            equipment = await query
            return equipment
        except DoesNotExist:
            return None
        
    @classmethod
    async def get_by_id(cls, uuid: str) -> Optional["Equipment"]:
        try:
            query = cls.get_or_none(uuid=uuid)
            equipment = await query
            return equipment
        except DoesNotExist:
            return None
        
    def __str__(self) -> str:
        return self.name
    
    class Meta:
        table = "equipment"
        ordering = ["name"]


class AvailabilitySlot(BaseModel):
    uuid = fields.UUIDField(pk=True)
    auditorium: fields.ForeignKeyRelation["Auditorium"] = fields.ForeignKeyField(
        "models.Auditorium", related_name="availability_slots", on_delete=fields.CASCADE
    )
    day_of_week = fields.IntField(description="Day of the week (0=Monday, 6=Sunday)")
    start_time = fields.TimeField(description="Start time of the slot")
    end_time = fields.TimeField(description="End time of the slot")

    @classmethod
    async def create(cls, model: CreateAvailability) -> "AvailabilitySlot":
        model_dict = model.model_dump()
        availability = cls(**model_dict)
        await availability.save()
        return availability
        
    @classmethod
    async def get_by_id(cls, uuid: str) -> Optional["AvailabilitySlot"]:
        try:
            query = cls.get_or_none(uuid=uuid)
            equipment = await query
            return equipment
        except DoesNotExist:
            return None
        
    @classmethod
    async def get_by_auditorium(cls, auditorium: UUID4) -> Optional["AvailabilitySlot"]:
        try:
            query = cls.get_or_none(auditorium=auditorium)
            equipment = await query
            return equipment
        except DoesNotExist:
            return None

    class Meta:
        table = "availability_slots"
        unique_together = (("auditorium", "day_of_week", "start_time"), ("auditorium", "day_of_week", "end_time"))
        ordering = ["auditorium", "day_of_week", "start_time"]

    def __str__(self):
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        return f"Aud. {self.auditorium_id}: {days[self.day_of_week]} {self.start_time}-{self.end_time}"


class Auditorium(BaseModel):
    uuid = fields.UUIDField(pk=True)
    identifier = fields.CharField(max_length=100, unique=True)
    capacity = fields.IntField()
    desctiption = fields.TextField(null=True)
    equipment: fields.ManyToManyRelation["Equipment"] = fields.ManyToManyField(
        "models.Equipment", related_name="auditoriums_equipment", through="auditorium_equipment"
    )

    availability_schedule = fields.ReverseRelation["AvailabilitySlot"]
    bookings: fields.ReverseRelation["Booking"]

    @classmethod
    async def create(cls, auditorium_model: CreateAuditorium) -> "Auditorium":
        auditorium_dict = auditorium_model.model_dump()
        auditorium = cls(**auditorium_dict)
        await auditorium.save()
        return auditorium

    @classmethod
    async def get_by_id(cls, uuid: str) -> Optional["Auditorium"]:
        try:
            query = cls.get_or_none(uuid=uuid)
            auditorium = await query
            return auditorium
        except DoesNotExist:
            return None

    def __str__(self):
        return self.identifier

    class Meta:
        table = "auditoriums"
        ordering = ["identifier"]


class Booking(BaseModel):
    uuid = fields.UUIDField(pk=True)
    broker: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="bookings", on_delete=fields.CASCADE
    )
    auditorium: fields.ForeignKeyRelation["Auditorium"] = fields.ForeignKeyField(
        "models.Auditorium", related_name="bookings", on_delete=fields.CASCADE
    )
    start_time = fields.DatetimeField()
    end_time = fields.DatetimeField()
    title = fields.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"Booking {self.id}: Aud. {self.auditorium_id} by User {self.booker_id} ({self.start_time} - {self.end_time})"

    class Meta:
        table = "bookings"
        ordering = ["start_time"]
    
    @classmethod
    async def create(cls, booking_model: CreateBooking, user: User) -> "Booking":
        booking_dict = booking_model.model_dump()
        booking = cls(**booking_dict, broker=user.uuid)
        await booking.save()
        return booking

    @classmethod
    async def get_by_id(cls, uuid: str) -> Optional["Booking"]:
        try:
            query = cls.get_or_none(uuid=uuid)
            booking = await query
            return booking
        except DoesNotExist:
            return None
