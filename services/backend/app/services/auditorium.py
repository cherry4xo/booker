from typing import List, Optional
from fastapi import HTTPException, Depends
from pydantic import UUID4

from app.schemas import CreateAuditorium, UpdateAuditorium, DeleteAuditorium
from app.models import Auditorium, Equipment
from app.logger import log_calls

from app import metrics

@log_calls
async def _get_equipment_objects(equipment_uuids: Optional[List[UUID4]]) -> List[Equipment]:
    """Вспомогательная функция для получения объектов Equipment по UUID."""
    equipment_objects = []
    if equipment_uuids:
        equipment_objects = await Equipment.filter(uuid__in=equipment_uuids)
        if len(equipment_objects) != len(equipment_uuids):
            found_uuids = {eq.uuid for eq in equipment_objects}
            missing_uuids = [str(uuid) for uuid in equipment_uuids if uuid not in found_uuids]
            raise HTTPException(
                status_code=404,
                detail=f"Following equipment UUIDs not found: {', '.join(missing_uuids)}"
            )
    return equipment_objects


@log_calls
async def create_auditorium(auditorium_model: CreateAuditorium) -> Auditorium:
    existing = await Auditorium.get_or_none(identifier=auditorium_model.identifier)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Auditorium with identifier '{auditorium_model.identifier}' already exists."
        )
    equipment_to_add = []
    if hasattr(auditorium_model, 'equipment_uuids') and auditorium_model.equipment_uuids:
         equipment_to_add = await _get_equipment_objects(auditorium_model.equipment_uuids)
         create_data = auditorium_model.model_dump(exclude={'equipment_uuids'})
    else:
         create_data = auditorium_model.model_dump()

    auditorium = Auditorium(**create_data)
    await auditorium.save()

    if equipment_to_add:
        await auditorium.equipment.add(*equipment_to_add)
    await auditorium.fetch_related('equipment') 

    metrics.backend_auditoriums_managed_total.labels(operation="create").inc()

    return auditorium


@log_calls
async def update_auditorium(auditorium_uuid: UUID4, auditorium_update_data: UpdateAuditorium) -> Auditorium:
    auditorium = await Auditorium.get_or_none(uuid=auditorium_uuid)
    if not auditorium:
        raise HTTPException(status_code=404, detail="Auditorium not found")

    update_data = auditorium_update_data.model_dump(exclude_unset=True)

    if 'identifier' in update_data and update_data['identifier'] != auditorium.identifier:
        existing = await Auditorium.get_or_none(identifier=update_data['identifier'])
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Auditorium with identifier '{update_data['identifier']}' already exists."
            )

    await auditorium.update_from_dict(update_data).save()
    await auditorium.fetch_related('equipment')

    metrics.backend_auditoriums_managed_total.labels(operation="update").inc()

    return auditorium


@log_calls
async def delete_auditorium(auditorium_uuid: UUID4):
    auditorium = await Auditorium.get_or_none(uuid=auditorium_uuid)
    if not auditorium:
        raise HTTPException(status_code=404, detail="Auditorium not found")
    await auditorium.delete()

    metrics.backend_auditoriums_managed_total.labels(operation="delete").inc()


@log_calls
async def get_auditorium_by_uuid(auditorium_uuid: UUID4) -> Optional[Auditorium]:
    auditorium = await Auditorium.get_or_none(uuid=auditorium_uuid)
    if auditorium:
        await auditorium.fetch_related('equipment') 
    return auditorium


@log_calls
async def get_auditoriums(
    min_capacity: Optional[int] = None,
    equipment_id: Optional[UUID4] = None
) -> List[Auditorium]:
    """
    Получает список аудиторий с опциональной фильтрацией
    по минимальной вместимости и наличию оборудования.
    """
    query = Auditorium.all()

    if min_capacity is not None:
        query = query.filter(capacity__gte=min_capacity)

    if equipment_id is not None:
        query = query.filter(equipment__uuid=equipment_id).distinct()
    query = query.prefetch_related('equipment')
    auditoriums = await query.order_by('identifier')

    return auditoriums