from typing import List, Optional
from fastapi import HTTPException, Depends

from app.schemas import CreateAuditorium, UpdateAuditorium, DeleteAuditorium
from app.models import Auditorium
from pydantic import UUID4



async def create_auditorium(auditorium_model: CreateAuditorium) -> Auditorium:
    # Проверка на уникальность identifier (Tortoise сделает это при .save(), но можно и заранее)
    existing = await Auditorium.get_or_none(identifier=auditorium_model.identifier)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Auditorium with identifier '{auditorium_model.identifier}' already exists."
        )
    # Используем прямое создание, а не classmethod модели
    auditorium = Auditorium(**auditorium_model.model_dump())
    await auditorium.save()
    return auditorium


async def update_auditorium(auditorium_uuid: UUID4, auditorium_update_data: UpdateAuditorium) -> Auditorium:
    auditorium = await Auditorium.get_or_none(uuid=auditorium_uuid)
    if not auditorium:
        raise HTTPException(status_code=404, detail="Auditorium not found")

    update_data = auditorium_update_data.model_dump(exclude_unset=True)

    # Проверка уникальности identifier, если он меняется
    if 'identifier' in update_data and update_data['identifier'] != auditorium.identifier:
         existing = await Auditorium.get_or_none(identifier=update_data['identifier'])
         if existing:
             raise HTTPException(
                status_code=409,
                detail=f"Auditorium with identifier '{update_data['identifier']}' already exists."
             )

    await auditorium.update_from_dict(update_data).save() # Добавлен .save()
    # Можно добавить prefetch_related('equipment') если нужно вернуть с оборудованием
    return auditorium


async def delete_auditorium(auditorium_uuid: UUID4): # Принимаем UUID
    auditorium = await Auditorium.get_or_none(uuid=auditorium_uuid) # Используем get_or_none
    if not auditorium:
        raise HTTPException(status_code=404, detail="Auditorium not found")
    await auditorium.delete()


async def get_auditorium_by_uuid(auditorium_uuid: UUID4) -> Optional[Auditorium]: # Возвращаем Optional[Model]
    # Добавить .prefetch_related('equipment', 'availability_slots') если нужно
    auditorium = await Auditorium.get_or_none(uuid=auditorium_uuid)
    # Проверка на 404 теперь в роутере или при использовании результата
    return auditorium


async def get_auditoriums() -> List[Auditorium]:
    auditoriums = await Auditorium.all().prefetch_related('equipment', 'availability_slots')
    return auditoriums
