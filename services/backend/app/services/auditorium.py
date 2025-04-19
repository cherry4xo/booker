from fastapi import HTTPException, Depends

from app.schemas import CreateAuditorium, UpdateAuditorium, DeleteAuditorium
from app.models import Auditorium
from pydantic import UUID4


async def create_auditorium(auditorium_model: CreateAuditorium):
    auditorium = await Auditorium.create(auditorium_model)
    return auditorium


async def update_auditorium(auditorium_model: UpdateAuditorium):
    auditorium = await Auditorium.get_by_id(auditorium_model.uuid)
    if not auditorium:
        raise HTTPException(status_code=404, detail="Auditorium not found")
    await auditorium.update_from_dict(auditorium_model.model_dump())
    return auditorium


async def delete_auditorium(auditorium: DeleteAuditorium):
    auditorium = await Auditorium.get_by_id(auditorium.uuid)
    if not auditorium:
        raise HTTPException(status_code=404, detail="Auditorium not found")
    await auditorium.delete()


async def get_auditorium_by_uuid(uuid: UUID4):
    auditorium = await Auditorium.get_by_id(uuid)
    if not auditorium:
        raise HTTPException(status_code=404, detail="Auditorium not found")
    return auditorium


async def get_auditoriums():
    auditoriums = await Auditorium.all()
    return auditoriums