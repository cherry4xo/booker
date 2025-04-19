from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import UUID4

from app.schemas import CreateBooking, DeleteBooking, UpdateBooking, GetBooking
from app.utils.contrib import get_current_moderator, get_current_user
from app.services.booking import get_booking_by_uuid, get_bookings, create_booking, delete_booking, get_my_bookings, update_booking
from app.models import User


router = APIRouter()


@router.post("/", response_model=GetBooking, status_code=201)
async def handle_create_booking(
    booking_data: CreateBooking,
    current_user: User = Depends(get_current_user)
):
    """ Создает новое бронирование для аудитории. """
    new_booking = await create_booking(booking_model=booking_data, current_user=current_user)
    return new_booking

@router.get("/", response_model=List[GetBooking])
async def handle_read_bookings(
    current_user: User = Depends(get_current_user),
    # Используем Query для параметров фильтрации
    auditorium_id: Optional[UUID4] = Query(None, alias="auditoriumId", description="Фильтр по UUID аудитории"),
    user_id: Optional[UUID4] = Query(None, alias="userId", description="Фильтр по UUID пользователя (только для модераторов)"),
    start_date: Optional[date] = Query(None, alias="startDate", description="Начальная дата для фильтрации (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, alias="endDate", description="Конечная дата для фильтрации (YYYY-MM-DD)")
):
    """ Возвращает список бронирований с возможностью фильтрации. """
    bookings_list = await get_bookings(
        current_user=current_user,
        auditorium_uuid=auditorium_id,
        user_uuid=user_id,
        start_date=start_date,
        end_date=end_date
    )
    return bookings_list


@router.get("/{booking_uuid}", response_model=GetBooking)
async def handle_read_booking(
    booking_uuid: UUID4 = Path(..., title="UUID бронирования"),
    current_user: User = Depends(get_current_user)
):
    """ Получает детали конкретного бронирования по его UUID. """
    booking = await get_booking_by_uuid(booking_uuid=booking_uuid, current_user=current_user)
    if booking is None:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    return booking


@router.patch("/{booking_uuid}", response_model=GetBooking)
async def handle_update_booking(
    booking_update_data: UpdateBooking,
    booking_uuid: UUID4 = Path(..., title="UUID бронирования для обновления"),
    current_user: User = Depends(get_current_user)
):
    """
    Обновляет существующее бронирование (частично).
    Доступно создателю брони или модератору.
    """
    updated_booking = await update_booking(
        booking_uuid=booking_uuid,
        booking_update_data=booking_update_data,
        current_user=current_user
    )
    return updated_booking


@router.delete("/{booking_uuid}", status_code=204)
async def handle_delete_booking(
    booking_uuid: UUID4 = Path(..., title="UUID бронирования для удаления"),
    current_user: User = Depends(get_current_user)
):
    """
    Удаляет (отменяет) бронирование. Доступно создателю брони или модератору.
    """
    deleted = await delete_booking(booking_uuid=booking_uuid, current_user=current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    return None


@router.get("/me", response_model=List[GetBooking], summary="Получить мои бронирования")
async def handle_read_my_bookings(
    current_user: User = Depends(get_current_user),
    auditorium_id: Optional[UUID4] = Query(None, alias="auditoriumId", description="Фильтр по UUID аудитории"),
    start_date: Optional[date] = Query(None, alias="startDate", description="Начальная дата для фильтрации (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, alias="endDate", description="Конечная дата для фильтрации (YYYY-MM-DD)")
):
    """
    Возвращает список бронирований, сделанных ТЕКУЩИМ аутентифицированным пользователем.
    Поддерживает фильтрацию по аудитории и диапазону дат.
    """
    my_bookings = await get_my_bookings(
        current_user=current_user,
        auditorium_uuid=auditorium_id,
        start_date=start_date,
        end_date=end_date
    )
    return my_bookings