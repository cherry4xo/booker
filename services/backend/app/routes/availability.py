from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import UUID4

from app.schemas import GetAvailability, UpdateAvailability, CreateAvailability, DeleteAvailability
from app.utils.contrib import get_current_moderator
from app.services.availability import get_availability, get_all_availabilities, create_availability, update_availabilities, delete_availability
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


@router.patch("/", response_model=GetAvailability, status_code=200)
async def route_update_availability(availability: UpdateAvailability, current_user: User = Depends(get_current_moderator)):
    return await update_availabilities(availability)


@router.delete("/", status_code=204)
async def route_delete_availability(availability: DeleteAvailability, current_user: User = Depends(get_current_moderator)):
    await delete_availability(availability)