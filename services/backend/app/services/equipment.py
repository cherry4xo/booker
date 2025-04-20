from typing import List, Optional
from fastapi import HTTPException, Depends
from tortoise.exceptions import IntegrityError
from pydantic import UUID4

from app.schemas import CreateEquipment, GetEquipment, UpdateEquipment, DeleteEquipment
from app.models import Equipment
from app.logger import log_calls

from app import metrics


@log_calls
async def create_equipment(equipment_model: CreateEquipment) -> Equipment:
    equipment = Equipment.get_by_name(equipment_model.name)
    if equipment:
        raise HTTPException(
            status_code=409,
            detail=f"Equipment with name '{equipment_model.name}' already exists."
        )
    try:
        equipment = Equipment(**equipment_model.model_dump())
        await equipment.save()

        metrics.backend_equipment_managed_total.labels(operation="create").inc()

        return equipment
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"Equipment with name '{equipment_model.name}' already exists."
        )


@log_calls
async def get_equipment_by_id(equipment_uuid: UUID4) -> Optional[Equipment]:
    equipment = await Equipment.get_or_none(uuid=equipment_uuid)
    return equipment


@log_calls
async def update_equipment(equipment_uuid: UUID4, equipment_update_data: UpdateEquipment) -> Equipment:
    equipment = await Equipment.get_or_none(uuid=equipment_uuid)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    update_data = equipment_update_data.model_dump(exclude_unset=True)

    if 'name' in update_data and update_data['name'] != equipment.name:
        existing = await Equipment.get_or_none(name=update_data['name'])
        if existing:
            raise HTTPException(
            status_code=409,
            detail=f"Equipment with name '{update_data['name']}' already exists."
            )

    try:
        await equipment.update_from_dict(update_data).save()
        metrics.backend_equipment_managed_total.labels(operation="update").inc()
    except IntegrityError:
        raise HTTPException(
        status_code=409,
        detail=f"Failed to update equipment due to data integrity issue."
        )
    return equipment


@log_calls
async def get_all_equipments() -> List[Equipment]:
    equipments = await Equipment.all()
    return equipments


@log_calls
async def delete_equipment(equipment_uuid: UUID4):
    equipment = await Equipment.get_or_none(uuid=equipment_uuid)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    await equipment.delete()

    metrics.backend_equipment_managed_total.labels(operation="delete").inc()