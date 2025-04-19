from datetime import time
from typing import List, Optional
from fastapi import HTTPException, Depends
from tortoise.expressions import Q

from app.schemas import CreateAvailability, GetAvailability, UpdateAvailability, DeleteAvailability
from app.models import Auditorium, AvailabilitySlot
from pydantic import UUID4


async def check_availability_slot_overlap(
    auditorium_uuid: UUID4,
    day_of_week: int,
    start_time: time,
    end_time: time,
    exclude_slot_uuid: Optional[UUID4] = None
) -> bool:
    """ Проверяет наложение нового или обновляемого слота с существующими """
    start_time_str = start_time.isoformat()
    is_end_midnight = (end_time == time(0, 0))
    end_time_str = time(23, 59, 59, 999999).isoformat() if is_end_midnight else end_time.isoformat()
    midnight_str = time(0, 0).isoformat()
    query = AvailabilitySlot.filter(
        auditorium_id=auditorium_uuid,
        day_of_week=day_of_week,
        start_time__lt=end_time_str,
    )

    query = AvailabilitySlot.filter(
        auditorium_id=auditorium_uuid,
        day_of_week=day_of_week,
    )
    if exclude_slot_uuid:
        query = query.exclude(uuid=exclude_slot_uuid)

    q1 = Q(start_time__lt=end_time_str) & Q(end_time__gt=start_time_str) & ~Q(end_time=midnight_str)
    q2 = Q(end_time=midnight_str) & Q(start_time__lt=end_time_str) 

    if is_end_midnight:
        q_new_ends_midnight = Q(start_time__gte=start_time_str) 
    else:
        q_new_ends_midnight = Q(start_time__lt=end_time_str) & (Q(end_time__gt=start_time_str) | Q(end_time=midnight_str))

    query = query.filter(
        Q(start_time__lt = end_time_str) &
        (Q(end_time__gt = start_time_str) | Q(end_time = midnight_str))
    )
    if start_time == time(0,0):
        query = query.exclude(end_time=midnight_str)


    # Use .exists()
    overlap_exists = await query.exists()

    if overlap_exists:
        raise HTTPException(
            status_code=409,
            detail=f"Availability slot overlaps with an existing slot for this auditorium on day {day_of_week}."
        )
    return True


async def create_availability(availability_model: CreateAvailability) -> AvailabilitySlot:
    auditorium = await Auditorium.get_or_none(uuid=availability_model.auditorium)
    if not auditorium:
        raise HTTPException(status_code=404, detail="Auditorium not found")

    await check_availability_slot_overlap(
        auditorium_uuid=availability_model.auditorium,
        day_of_week=availability_model.day_of_week,
        start_time=availability_model.start_time,
        end_time=availability_model.end_time
    )

    slot_data_dict = availability_model.model_dump()
    auditorium_uuid = slot_data_dict.pop('auditorium')

    availability = AvailabilitySlot(
        auditorium_id=auditorium.uuid,
        **slot_data_dict
    )
    await availability.save()
    await availability.fetch_related('auditorium')
    return availability


async def get_availability(uuid: UUID4) -> Optional[AvailabilitySlot]: 
    availability = await AvailabilitySlot.get_or_none(uuid=uuid)
    return availability


async def get_all_availabilities() -> List[AvailabilitySlot]: 
    availabilities = await AvailabilitySlot.all()
    return availabilities


async def update_availability( 
    availability_uuid: UUID4,
    availability_update_data: UpdateAvailability
) -> AvailabilitySlot:
    availability = await AvailabilitySlot.get_or_none(uuid=availability_uuid)
    if not availability:
        raise HTTPException(status_code=404, detail="Availability slot not found")

    update_data = availability_update_data.model_dump(exclude_unset=True)

    final_day = update_data.get('day_of_week', availability.day_of_week)
    final_start = update_data.get('start_time', availability.start_time)
    final_end = update_data.get('end_time', availability.end_time)

    await check_availability_slot_overlap(
        auditorium_uuid=availability.auditorium_id, 
        day_of_week=final_day,
        start_time=final_start,
        end_time=final_end,
        exclude_slot_uuid=availability_uuid 
    )

    await availability.update_from_dict(update_data).save() 
    return availability


async def delete_availability(availability_uuid: UUID4) -> None:
    availability = await AvailabilitySlot.get_or_none(uuid=availability_uuid)
    if not availability:
        raise HTTPException(status_code=404, detail="Availability slot not found")
    await availability.delete()