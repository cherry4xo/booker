import enum
from typing import Optional
from datetime import datetime

from tortoise import fields
from tortoise.models import Model
from tortoise.exceptions import DoesNotExist


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


class UserRole(str, enum.Enum):
    """ Defines the roles a user can have """
    BOOKER = "booker"
    MODERATOR = "moderator"


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

    async def to_dict(self):
        d = {}
        for field in self._meta.db_fields:
            d[field] = getattr(self, field)
        for field in self._meta.backward_fk_fields:
            d[field] = await getattr(self, field).all().values()
        return d

    @classmethod
    async def get_by_username(cls, username: str) -> Optional["User"]:
        try:
            query = cls.get_or_none(username=username)
            user = await query
            return user
        except DoesNotExist:
            return None

    def __str__(self):
        return f"{self.username} ({self.role.value})"

    class Meta:
        table = "users"
        ordering = ["username"]
