from fastapi import HTTPException, Depends

from app.schemas import CreateEquipment, GetEquipment, UpdateEquipment, DeleteEquipment
from app.models import Equipment
from pydantic import UUID4


async def create_equipment(equipment: CreateEquipment):
    equipment = await Equipment.create(equipment)
    return equipment


async def get_equipment_by_id(uuid: UUID4):
    equipment = await Equipment.get_by_id(uuid)
    return equipment

async def get_all_equipments():
    equipments = await Equipment.all()
    return equipments


async def delete_equipment(uuid: UUID4):
    equipment = await Equipment.get_by_id(uuid)
    await equipment.delete()
    return equipment