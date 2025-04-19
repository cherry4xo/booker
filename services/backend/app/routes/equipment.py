from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4
from tortoise.exceptions import IntegrityError

from app.schemas import CreateEquipment, GetEquipment, UpdateEquipment
from app.models import Equipment
from app.utils.contrib import get_current_moderator
from app.services.equipment import create_equipment, get_equipment_by_id, get_all_equipments, delete_equipment
from app.models import User

router = APIRouter()


@router.post("/", response_model=CreateEquipment, status_code=201)
async def route_create_equipment(equipment: CreateEquipment, current_user: User = Depends(get_current_moderator)):
    return await create_equipment(equipment=equipment)


@router.get("/{uuid}", response_model=GetEquipment, status_code=200)
async def route_get_equipment(uuid: UUID4):
    return await get_equipment_by_id(uuid=uuid)


@router.patch("/", response_model=GetEquipment, status_code=200)
async def update_equipment(equipment_update: UpdateEquipment, current_user: User = Depends(get_current_moderator)):
    equipment = await Equipment.get_by_id(uuid=equipment_update.uuid)
    update_data = equipment.model_dump(exclude_unset=True)
    equipment = equipment.update_from_dict(update_data)
    try:
        await equipment.save()
    except IntegrityError:
        raise HTTPException(status_code=400, detail=f"Equipment name conflict.")
    return equipment


@router.get("/", response_model=List[GetEquipment], status_code=200)
async def route_get_all_equipments():
    return await get_all_equipments()


@router.delete("/{uuid}", status_code=204)
async def route_delete_equipment(uuid: UUID4, current_user: User = Depends(get_current_moderator)):
    await delete_equipment(uuid=uuid)