from typing import List, Optional
from fastapi import HTTPException, Depends
from tortoise.exceptions import IntegrityError

from app.schemas import CreateEquipment, GetEquipment, UpdateEquipment, DeleteEquipment
from app.models import Equipment
from pydantic import UUID4


async def create_equipment(equipment_model: CreateEquipment) -> Equipment: # Возвращаем модель
    try:
        # Используем прямое создание
        equipment = Equipment(**equipment_model.model_dump())
        await equipment.save()
        return equipment
    except IntegrityError: # Обработка уникального имени
        raise HTTPException(
            status_code=409,
            detail=f"Equipment with name '{equipment_model.name}' already exists."
        )


async def get_equipment_by_id(equipment_uuid: UUID4) -> Optional[Equipment]: # Возвращаем Optional[Model]
    equipment = await Equipment.get_or_none(uuid=equipment_uuid)
    # Проверка 404 в роутере
    return equipment


async def update_equipment(equipment_uuid: UUID4, equipment_update_data: UpdateEquipment) -> Equipment:
    equipment = await Equipment.get_or_none(uuid=equipment_uuid)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    update_data = equipment_update_data.model_dump(exclude_unset=True)

    # Проверка уникальности имени, если оно меняется
    if 'name' in update_data and update_data['name'] != equipment.name:
        existing = await Equipment.get_or_none(name=update_data['name'])
        if existing:
            raise HTTPException(
            status_code=409,
            detail=f"Equipment with name '{update_data['name']}' already exists."
            )

    try:
        await equipment.update_from_dict(update_data).save() # Добавлен .save()
    except IntegrityError: # На случай других гонок или проблем
        raise HTTPException(
        status_code=409,
        detail=f"Failed to update equipment due to data integrity issue."
        )
    return equipment


async def get_all_equipments() -> List[Equipment]: # Возвращаем List[Model]
    equipments = await Equipment.all()
    return equipments


async def delete_equipment(equipment_uuid: UUID4): # Принимаем UUID
    equipment = await Equipment.get_or_none(uuid=equipment_uuid) # Используем get_or_none
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    await equipment.delete()