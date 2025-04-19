from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import UUID4

from app.schemas import CreateAuditorium, UpdateAuditorium, GetAuditorium, DeleteAuditorium
from app.utils.contrib import get_current_moderator
from app.services.auditorium import get_auditorium_by_uuid, get_auditoriums, create_auditorium, delete_auditorium, update_auditorium
from app.models import User

router = APIRouter()

CurrentModerator = Depends(get_current_moderator)

@router.post("/", response_model=GetAuditorium, status_code=201)
async def route_create_auditorium(
    auditorium_data: CreateAuditorium, # Данные из тела
    current_user: User = CurrentModerator # Только модератор
):
    return await create_auditorium(auditorium_data)


@router.get("/{auditorium_uuid}", response_model=GetAuditorium, status_code=200)
async def route_get_auditorium(
    auditorium_uuid: UUID4 = Path(..., title="UUID of the auditorium"),
):
    auditorium = await get_auditorium_by_uuid(auditorium_uuid)
    if not auditorium:
        raise HTTPException(status_code=404, detail="Auditorium not found")
    return auditorium

@router.get("/", response_model=List[GetAuditorium], status_code=200)
async def route_get_auditoriums():
    return await get_auditoriums()

@router.patch("/{auditorium_uuid}", response_model=GetAuditorium, status_code=200)
async def route_update_auditorium(
    update_data: UpdateAuditorium, # Данные из тела
    auditorium_uuid: UUID4 = Path(..., title="UUID of the auditorium to update"),
    current_user: User = CurrentModerator # Только модератор
):
    # Передаем UUID из пути и данные из тела в сервис
    return await update_auditorium(
        auditorium_uuid=auditorium_uuid,
        auditorium_update_data=update_data
    )

@router.delete("/{auditorium_uuid}", status_code=204)
async def route_delete_auditorium(
    auditorium_uuid: UUID4 = Path(..., title="UUID of the auditorium to delete"),
    current_user: User = CurrentModerator # Только модератор
):
    # Сервис delete_auditorium теперь сам вызывает HTTPException 404 если не найдено
    await delete_auditorium(auditorium_uuid=auditorium_uuid)
    # Нет ответа для 204