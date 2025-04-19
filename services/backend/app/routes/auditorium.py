from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import UUID4

from app.schemas import CreateAuditorium, UpdateAuditorium, GetAuditorium, DeleteAuditorium, CalendarBookingEntry
from app.utils.contrib import get_current_moderator
from app.services.auditorium import get_auditorium_by_uuid, get_auditoriums, create_auditorium, delete_auditorium, update_auditorium
from app.services.booking import get_bookings_for_calendar
from app.models import User

router = APIRouter()

CurrentModerator = Depends(get_current_moderator)

@router.post("/", response_model=GetAuditorium, status_code=201)
async def route_create_auditorium(
    auditorium_data: CreateAuditorium,
    current_user: User = CurrentModerator
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
    update_data: UpdateAuditorium,
    auditorium_uuid: UUID4 = Path(..., title="UUID of the auditorium to update"),
    current_user: User = CurrentModerator
):
    return await update_auditorium(
        auditorium_uuid=auditorium_uuid,
        auditorium_update_data=update_data
    )

@router.delete("/{auditorium_uuid}", status_code=204)
async def route_delete_auditorium(
    auditorium_uuid: UUID4 = Path(..., title="UUID of the auditorium to delete"),
    current_user: User = CurrentModerator
):
    await delete_auditorium(auditorium_uuid=auditorium_uuid)


@router.get(
    "/calendar/{auditorium_uuid}",
    response_model=List[CalendarBookingEntry],
    summary="Получить бронирования для календаря",
    description="Возвращает список бронирований для указанной аудитории в заданном диапазоне дат, "
                "в формате, удобном для отображения календаря."
)
async def route_get_auditorium_calendar(
    auditorium_uuid: UUID4 = Path(..., title="UUID аудитории"),
    start_date: date = Query(..., alias="startDate", description="Начальная дата диапазона (YYYY-MM-DD)"),
    end_date: date = Query(..., alias="endDate", description="Конечная дата диапазона (YYYY-MM-DD)"),
):
    """
    Получает данные о бронированиях для календаря конкретной аудитории.
    Требует аутентификации. Доступ может быть у всех аутентифицированных пользователей
    (чтобы видеть занятость), или можно ограничить права при необходимости.
    """

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Дата начала не может быть позже даты окончания.")

    bookings = await get_bookings_for_calendar(
        auditorium_uuid=auditorium_uuid,
        start_date=start_date,
        end_date=end_date
    )
    return bookings


@router.get(
    "/",
    response_model=List[GetAuditorium],
    status_code=200,
    summary="Получить список аудиторий с фильтрацией",
    description="Возвращает список аудиторий, опционально отфильтрованный "
                "по минимальной вместимости и/или наличию определенного оборудования."
)
async def route_get_auditoriums(
    min_capacity: Optional[int] = Query(
        None,
        alias="minCapacity",
        description="Минимальная требуемая вместимость аудитории",
        ge=1
    ),
    equipment_id: Optional[UUID4] = Query(
        None,
        alias="equipmentId",
        description="UUID оборудования, которое должно присутствовать в аудитории"
    )
):
    """
    Возвращает список аудиторий.
    Поддерживает фильтрацию по минимальной вместимости (minCapacity)
    и наличию конкретного оборудования (equipmentId).
    Доступно всем.
    """
    auditoriums = await get_auditoriums(
        min_capacity=min_capacity,
        equipment_id=equipment_id
    )
    return auditoriums