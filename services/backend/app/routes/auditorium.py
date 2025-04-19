from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import UUID4

from app.schemas import CreateAuditorium, UpdateAuditorium, GetAuditorium, DeleteAuditorium
from app.utils.contrib import get_current_moderator
from app.services.auditorium import get_auditorium_by_uuid, get_auditoriums, create_auditorium, delete_auditorium, update_auditorium
from app.models import User

router = APIRouter()


@router.post("/", response_model=GetAuditorium, status_code=201)
async def route_create_auditorium(auditorium: CreateAuditorium, current_user: User = Depends(get_current_moderator)):
    return await create_auditorium(auditorium)


@router.get("/{uuid}", response_model=GetAuditorium, status_code=200)
async def route_get_auditorium(uuid: UUID4):
    return await get_auditorium_by_uuid(uuid)


@router.get("/", response_model=List[GetAuditorium], status_code=200)
async def route_get_auditoriums():
    return await get_auditoriums()


@router.patch("/", response_model=GetAuditorium, status_code=200)
async def route_update_auditorium(auditorium: UpdateAuditorium, current_user: User = Depends(get_current_moderator)):
    return await update_auditorium(auditorium)


@router.delete("/{uuid}", status_code=204)
async def route_delete_auditorium(auditorium: DeleteAuditorium, current_user: User = Depends(get_current_moderator)):
    await delete_auditorium(auditorium)