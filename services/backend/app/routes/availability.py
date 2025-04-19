from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Path
from pydantic import UUID4

from app.schemas import GetAvailability, UpdateAvailability, CreateAvailability, DeleteAvailability
from app.utils.contrib import get_current_moderator
from app.services.availability import get_availability, get_all_availabilities, create_availability, update_availability, delete_availability
from app.models import User


router = APIRouter()


@router.post("/", response_model=GetAvailability, status_code=200)
async def route_create_availability(availability: CreateAvailability, current_user: User = Depends(get_current_moderator)):
    return await create_availability(availability)


@router.get("/", response_model=List[GetAvailability], status_code=200)
async def route_get_all_availabilities():
    return await get_all_availabilities()


@router.get("/{uuid}", response_model=GetAvailability, status_code=200)
async def route_get_availability(uuid: UUID4):
    return await get_availability(uuid)


@router.patch("/{availability_uuid}", response_model=GetAvailability, status_code=200)
async def route_update_availability(
    availability_uuid: UUID4 = Path(..., title="UUID слота доступности для обновления"),
    availability_update_data: UpdateAvailability = Body(...), # Данные из тела
    current_user: User = Depends(get_current_moderator)
):
    updated_availability = await update_availability(
         availability_uuid=availability_uuid,
         availability_update_data=availability_update_data
    )
    # Сервис кидает 404, 409 (наложение)
    return updated_availability


@router.delete("/{availability_uuid}", status_code=204)
async def route_delete_availability(
    availability_uuid: UUID4 = Path(..., title="UUID слота доступности для удаления"),
    current_user: User = Depends(get_current_moderator)
):
    """
    Удаляет слот доступности.
    Требует прав модератора.
    """
    await delete_availability(availability_uuid=availability_uuid)