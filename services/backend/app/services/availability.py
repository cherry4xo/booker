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
    # Корректируем время 00:00 для запроса
    db_end_time = time(23, 59, 59, 999999) if end_time == time(0,0) else end_time
    db_start_time = start_time

    query = AvailabilitySlot.filter(
        Q(start_time__lt=db_end_time) &
        (Q(end_time__gt=db_start_time) | Q(end_time=time(0,0))), # Заканчивается после начала ИЛИ в полночь
        auditorium_id=auditorium_uuid,
        day_of_week=day_of_week,
    )

    # Особая обработка для start_time = 00:00, чтобы не пересекалось с end_time = 00:00
    if db_start_time == time(0,0):
        query = query.exclude(end_time=time(0,0)) # Не считаем пересечением, если старый заканчивается в полночь, а новый начинается

    if exclude_slot_uuid:
        query = query.exclude(uuid=exclude_slot_uuid)

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

    # Проверка наложения
    await check_availability_slot_overlap(
        auditorium_uuid=availability_model.auditorium,
        day_of_week=availability_model.day_of_week,
        start_time=availability_model.start_time,
        end_time=availability_model.end_time
    )

    # Создаем объект напрямую
    availability = AvailabilitySlot(**availability_model.model_dump())
    await availability.save()
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