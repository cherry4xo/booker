from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import UUID4

from app.schemas import CreateBooking, DeleteBooking, UpdateBooking, GetBooking
from app.utils.contrib import get_current_moderator, get_current_user
from app.services.booking import get_booking_by_uuid, get_bookings, create_booking, delete_booking, update_booking
from app.models import User


router = APIRouter()


@router.post("/", response_model=GetBooking, status_code=201)
async def handle_create_booking(
    booking_data: CreateBooking, # Используем схему для создания
    current_user: User = Depends(get_current_user)
):
    """
    Создает новое бронирование для аудитории.
    """
    # Важно: response_model должен уметь сериализовать возвращаемый объект модели Booking
    # Убедитесь, что в GetBooking есть Config { from_attributes = True } (Pydantic v2)
    # или orm_mode = True (Pydantic v1)
    new_booking_model = await create_booking(booking_model=booking_data, current_user=current_user)
    # Сериализация в GetBooking произойдет автоматически благодаря FastAPI/Pydantic
    return new_booking_model

@router.get("/", response_model=List[GetBooking], status_code=200)
async def handle_read_bookings(
    booking: GetBooking,
    current_user: User = Depends(get_current_user)
):
    """
    Возвращает список бронирований с возможностью фильтрации.
    """
    bookings_list = await get_bookings(
        current_user=current_user,
        auditorium_uuid=booking.auditorium,
        user_uuid=booking.booker,
        start_date=booking.start_time,
        end_date=booking.end_time
    )
    return bookings_list


@router.get("/{booking_uuid}", response_model=GetBooking, status_code=200)
async def handle_read_booking(
    booking_uuid: UUID4 = Path(..., title="UUID бронирования"),
    current_user: User = Depends(get_current_user)
):
    """
    Получает детали конкретного бронирования по его UUID.
    """
    booking = await get_booking_by_uuid(booking_uuid=booking_uuid, current_user=current_user)
    if booking is None:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    return booking


@router.patch("/{booking_uuid}", response_model=GetBooking, status_code=200)
async def handle_update_booking(
    booking_update_data: UpdateBooking, # Используем схему для обновления
    booking_uuid: UUID4 = Path(..., title="UUID бронирования для обновления"),
    current_user: User = Depends(get_current_user)
):
    """
    Обновляет существующее бронирование.
    Доступно создателю брони или модератору.
    Позволяет изменять время, аудиторию или заголовок.
    """
    # Проверяем, что UUID в пути совпадает с UUID в теле запроса, если он там есть
    # (В UpdateBooking он обязателен по вашей схеме, это можно изменить сделав Optional)
    if booking_update_data.uuid != booking_uuid:
        raise HTTPException(
            status_code=400,
            detail="UUID в пути и в теле запроса не совпадают."
        )

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
        # CRUD функция delete_booking возвращает False если не найдено
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    # Нет тела ответа для статуса 204
    return None

