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
    # --- Workaround for SQLite: Convert times to ISO strings ---
    start_time_str = start_time.isoformat()
    # Handle midnight end time for comparison logic
    # If end_time is 00:00, it means "up to the end of the day"
    is_end_midnight = (end_time == time(0, 0))
    end_time_str = time(23, 59, 59, 999999).isoformat() if is_end_midnight else end_time.isoformat()
    midnight_str = time(0, 0).isoformat()
    # --- End Workaround ---

    # Build the query using string comparisons
    # Overlap condition: (Slot Start < My End) AND (Slot End > My Start)
    # Needs careful handling of midnight representation in DB vs Python
    # Assuming TimeField stores as TEXT 'HH:MM:SS.ffffff' in SQLite
    query = AvailabilitySlot.filter(
        auditorium_id=auditorium_uuid,
        day_of_week=day_of_week,
        # Slot starts before the new slot ends
        start_time__lt=end_time_str,
        # AND (Slot ends after the new slot starts OR Slot ends exactly at midnight represented differently)
        # This part is tricky with string comparison and midnight.
        # A simpler overlap check might be needed if this gets too complex.
        # Let's try the Tortoise Q objects first, maybe it handles strings better.
    )

    # Refined Q object approach (hoping Tortoise handles string comparison correctly)
    query = AvailabilitySlot.filter(
        auditorium_id=auditorium_uuid,
        day_of_week=day_of_week,
    )
    # Exclude the slot being updated
    if exclude_slot_uuid:
        query = query.exclude(uuid=exclude_slot_uuid)

    # Core overlap logic: Existing Slot Start < New End AND Existing Slot End > New Start
    # Handle the "End at Midnight" case carefully.
    # Case 1: Existing slot does NOT end at midnight (stored as '23:59:59...')
    q1 = Q(start_time__lt=end_time_str) & Q(end_time__gt=start_time_str) & ~Q(end_time=midnight_str)

    # Case 2: Existing slot ENDS at midnight (stored as '00:00:00')
    # It overlaps if the New slot starts before midnight (i.e., starts on the same day)
    q2 = Q(end_time=midnight_str) & Q(start_time__lt=end_time_str) # Should overlap if new slot starts before 23:59..

    # Case 3: Special handling if the NEW slot ends at midnight ('00:00:00')
    if is_end_midnight:
        # Overlaps if an existing slot starts anytime on this day
        q_new_ends_midnight = Q(start_time__gte=start_time_str) # Existing starts after or at new start
    else:
        # Standard overlap check if new slot ends normally
        q_new_ends_midnight = Q(start_time__lt=end_time_str) & (Q(end_time__gt=start_time_str) | Q(end_time=midnight_str))


    # Combine conditions - this logic might need refinement based on exact storage/comparison behavior
    # Simplified: An existing slot overlaps if its interval intersects the new interval.
    # (ExistingStart < NewEnd) and (ExistingEnd > NewStart)
    # Tortoise might handle time string comparisons lexicographically, which works for HH:MM:SS format.
    query = query.filter(
        Q(start_time__lt = end_time_str) &
        (Q(end_time__gt = start_time_str) | Q(end_time = midnight_str)) # Allow end_time=00:00 to mean "until end of day"
    )
     # Exclude cases where new starts at 00:00 and old ends at 00:00 (no overlap)
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


async def create_availability(availability_model: CreateAvailability) -> AvailabilitySlot: # Возвращаем модель
    # Проверка существования аудитории
    auditorium = await Auditorium.get_or_none(uuid=availability_model.auditorium)
    if not auditorium:
        raise HTTPException(status_code=404, detail="Auditorium not found")

    # Проверка наложения (using the existing check function)
    await check_availability_slot_overlap(
        auditorium_uuid=availability_model.auditorium, # Check uses UUID
        day_of_week=availability_model.day_of_week,
        start_time=availability_model.start_time,
        end_time=availability_model.end_time
    )

    # FIX: Create slot instance passing the fetched auditorium object
    slot_data_dict = availability_model.model_dump()
    auditorium_uuid = slot_data_dict.pop('auditorium') # Keep the uuid

    availability = AvailabilitySlot(
        auditorium_id=auditorium.uuid, # Pass the ID
        **slot_data_dict # Pass remaining fields
    )
    await availability.save()
    # Fetch related if needed after save
    await availability.fetch_related('auditorium')
    return availability


async def get_availability(uuid: UUID4) -> Optional[AvailabilitySlot]: # Возвращаем Optional[Model]
    availability = await AvailabilitySlot.get_or_none(uuid=uuid)
    # Проверка 404 в роутере
    return availability


async def get_all_availabilities() -> List[AvailabilitySlot]: # Возвращаем List[Model]
    availabilities = await AvailabilitySlot.all()
    return availabilities


async def update_availabilities( # Название лучше update_availability
    availability_uuid: UUID4,
    availability_update_data: UpdateAvailability
) -> AvailabilitySlot: # Возвращаем модель
    availability = await AvailabilitySlot.get_or_none(uuid=availability_uuid)
    if not availability:
        raise HTTPException(status_code=404, detail="Availability slot not found")

    update_data = availability_update_data.model_dump(exclude_unset=True)

    # Определяем финальные значения для проверки
    final_day = update_data.get('day_of_week', availability.day_of_week)
    final_start = update_data.get('start_time', availability.start_time)
    final_end = update_data.get('end_time', availability.end_time)
    # final_auditorium = update_data.get('auditorium', availability.auditorium_id) # Если разрешаем менять

    # Проверка наложения для новых параметров
    await check_availability_slot_overlap(
        auditorium_uuid=availability.auditorium_id, # Аудиторию обычно не меняем
        day_of_week=final_day,
        start_time=final_start,
        end_time=final_end,
        exclude_slot_uuid=availability_uuid # Исключаем текущий слот
    )

    await availability.update_from_dict(update_data).save() # Добавлен .save()
    return availability


async def delete_availability(availability_uuid: UUID4) -> None: # Принимаем UUID
    availability = await AvailabilitySlot.get_or_none(uuid=availability_uuid) # Используем get_or_none
    if not availability:
        raise HTTPException(status_code=404, detail="Availability slot not found")
    await availability.delete()