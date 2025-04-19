from typing import List
from fastapi import HTTPException, Depends

from app.schemas import CreateAvailability, GetAvailability, UpdateAvailability, DeleteAvailability
from app.models import Auditorium, AvailabilitySlot
from pydantic import UUID4


async def create_availability(availability_model: CreateAvailability) -> GetAvailability:
    availability = await AvailabilitySlot.create(availability_model)
    return availability


async def get_availability(uuid: UUID4) -> GetAvailability:
    availability = await AvailabilitySlot.get_by_id(uuid)
    if not availability:
        raise HTTPException(status_code=404, detail="Availability not found")
    return availability


async def get_all_availabilities() -> List[GetAvailability]:
    availabilities = await AvailabilitySlot.all()
    return availabilities


async def update_availabilities(availability_model: UpdateAvailability) -> GetAvailability:
    availability = await AvailabilitySlot.get_by_id(availability_model.uuid)
    if not availability:
        raise HTTPException(status_code=404, detail="Availability not found")
    
    availability_dict = availability_model.model_dump(exclude_unset=True)
    await availability.update_from_dict(availability_dict)
    return availability


async def delete_availability(availability_model: DeleteAvailability) -> None:
    availability = await AvailabilitySlot.get_by_id(availability_model.uuid)
    if not availability:
        raise HTTPException(status_code=404, detail="Availability not found")
    await availability.delete()