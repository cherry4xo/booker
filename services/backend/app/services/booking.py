from datetime import date, datetime, timedelta, time
from builtins import min as builtin_min
from typing import List, Optional

from fastapi import HTTPException, Depends, Query
from tortoise.exceptions import IntegrityError
from pydantic import UUID4

from app.schemas import CreateBooking, GetBooking, UpdateBooking, DeleteBooking
from app.models import Auditorium, AvailabilitySlot, User, Booking
from app.enums import UserRole
from app.logger import log_calls


@log_calls
async def check_auditorium_availability(
    auditorium_uuid: UUID4,
    start_dt: datetime,
    end_dt: datetime
) -> bool:
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="Время окончания должно быть после времени начала.")
    
    availability_slots_cache = {}
    current_check_dt = start_dt
    
    while current_check_dt < end_dt:
        current_date = current_check_dt.date()
        day_of_week = current_date.weekday()
        next_day_start = datetime.combine(current_date + timedelta(days=1), time(0, 0, 0), tzinfo=start_dt.tzinfo)
        segment_end_for_date = min(end_dt, next_day_start)
        check_start_time = current_check_dt.time()
        check_end_time = segment_end_for_date.time() if segment_end_for_date.date() == current_date else datetime.time(23, 59, 59, 999999)

        if segment_end_for_date.time() == datetime.time(0, 0) and segment_end_for_date > current_check_dt:
            check_end_time = datetime.time(23, 59, 59, 999999)

        if day_of_week not in availability_slots_cache:
            slots_for_day = await AvailabilitySlot.filter(
                auditorium_id=auditorium_uuid,
                day_of_week=day_of_week
            ).order_by('start_time').all()
            availability_slots_cache[day_of_week] = slots_for_day
        else:
            slots_for_day = availability_slots_cache[day_of_week]

        if not slots_for_day:
            raise HTTPException(
                status_code=400,
                detail=(f"Аудитория недоступна в указанный интервал. "
                        f"Нет расписания доступности на {current_date.strftime('%A, %Y-%m-%d')}.")
            )

        time_covered_until = check_start_time
        segment_fully_covered = False

        if check_start_time == check_end_time and check_start_time == datetime.time(0, 0):
             segment_fully_covered = True
        else:
            sorted_slots = sorted(slots_for_day, key=lambda s: s.start_time)
            for slot in sorted_slots:
                effective_slot_end = slot.end_time if slot.end_time != datetime.time(0, 0) else datetime.time(23, 59, 59, 999999)

                if slot.start_time <= time_covered_until and effective_slot_end > time_covered_until:
                    time_covered_until = max(time_covered_until, effective_slot_end)

                if slot.start_time > check_end_time:
                    break

                if time_covered_until >= check_end_time:
                    segment_fully_covered = True
                    break

        if not segment_fully_covered:
            auditorium = await Auditorium.get_or_none(uuid=auditorium_uuid)
            identifier = auditorium.identifier if auditorium else str(auditorium_uuid)
            raise HTTPException(
                status_code=400,
                detail=(f"Аудитория '{identifier}' недоступна в запрошенный временной интервал. "
                        f"Проблема в {current_date.strftime('%A, %Y-%m-%d')} "
                        f"между {check_start_time.strftime('%H:%M:%S')} и {check_end_time.strftime('%H:%M:%S')}. "
                        f"Проверьте расписание доступности.")
            )

        current_check_dt = segment_end_for_date

    return True


@log_calls
async def get_booking_by_uuid(booking_uuid: UUID4, current_user: User) -> Optional[Booking]:
    """ Получает бронирование по UUID с проверкой прав """
    booking = await Booking.filter(uuid=booking_uuid).prefetch_related('broker', 'auditorium').first()

    if not booking:
        return None

    if booking.broker_id != current_user.uuid and current_user.role != UserRole.MODERATOR:
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав для просмотра этого бронирования."
        )
    return booking


@log_calls
async def check_booking_overlap(
    auditorium_uuid: UUID4,
    start: datetime,
    end: datetime,
    exclude_booking_uuid: Optional[UUID4] = None
) -> bool:
    """
    Проверяет, пересекается ли запрошенное время с существующими бронированиями.
    (Без изменений, должна работать корректно с пересечением полуночи).
    """
    query = Booking.filter(
        auditorium_id=auditorium_uuid,
        start_time__lt=end,
        end_time__gt=start
    )
    if exclude_booking_uuid:
        query = query.exclude(uuid=exclude_booking_uuid)

    overlapping_booking_exists = await query.exists()

    if overlapping_booking_exists:
        auditorium = await Auditorium.get_or_none(uuid=auditorium_uuid)
        identifier = auditorium.identifier if auditorium else str(auditorium_uuid)
        raise HTTPException(
            status_code=409,
            detail=f"Запрошенный временной слот для аудитории '{identifier}' конфликтует с существующим бронированием."
        )
    return True


@log_calls
async def create_booking(booking_model: CreateBooking, current_user: User) -> Booking:
    """ Создает новое бронирование """
    auditorium = await Auditorium.get_or_none(uuid=booking_model.auditorium)
    if not auditorium:
        raise HTTPException(
            status_code=404,
            detail=f"Аудитория с UUID {booking_model.auditorium} не найдена."
        )

    start = booking_model.start_time
    end = booking_model.end_time

    await check_auditorium_availability(auditorium_uuid=booking_model.auditorium, start_dt=start, end_dt=end)
    await check_booking_overlap(auditorium_uuid=booking_model.auditorium, start=start, end=end)

    try:
        new_booking = Booking(
            auditorium=auditorium,
            broker=current_user,
            start_time=start,
            end_time=end,
            title=booking_model.title
        )
        await new_booking.save()
        await new_booking.fetch_related('broker', 'auditorium')
        return new_booking
    except IntegrityError as e:
        raise HTTPException(
            status_code=409,
            detail=f"Ошибка целостности данных при создании бронирования: {e}"
        )
    except Exception as e:
        print(f"Unexpected error creating booking: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Неожиданная ошибка при создании бронирования."
        )
    
    
@log_calls
async def update_booking(
    booking_uuid: UUID4,
    booking_update_data: UpdateBooking,
    current_user: User
) -> Booking:
    """ Обновляет существующее бронирование """
    booking = await Booking.filter(uuid=booking_uuid).prefetch_related('broker', 'auditorium').first()

    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")

    if booking.broker_id != current_user.uuid and current_user.role != UserRole.MODERATOR:
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав для изменения этого бронирования."
        )

    update_data = booking_update_data.model_dump(exclude_unset=True)

    final_start_time = update_data.get('start_time', booking.start_time)
    final_end_time = update_data.get('end_time', booking.end_time)
    final_auditorium_uuid = update_data.get('auditorium', booking.auditorium_id)

    final_auditorium = booking.auditorium
    if 'auditorium' in update_data and update_data['auditorium'] != booking.auditorium_id:
        final_auditorium_uuid = update_data['auditorium']
        final_auditorium = await Auditorium.get_or_none(uuid=final_auditorium_uuid)
        if not final_auditorium:
            raise HTTPException(
                status_code=404,
                detail=f"Новая аудитория с UUID {final_auditorium_uuid} не найдена."
            )
        update_data['auditorium_id'] = final_auditorium.uuid
        del update_data['auditorium']
    elif 'auditorium' in update_data:
        del update_data['auditorium']


    await check_auditorium_availability(
        auditorium_uuid=final_auditorium_uuid,
        start_dt=final_start_time,
        end_dt=final_end_time
    )
    await check_booking_overlap(
        auditorium_uuid=final_auditorium_uuid,
        start=final_start_time,
        end=final_end_time,
        exclude_booking_uuid=booking_uuid
    )
    await booking.update_from_dict(update_data).save()

    await booking.fetch_related('broker', 'auditorium')
    return booking


@log_calls
async def get_bookings(
    current_user: User,
    auditorium_uuid: Optional[UUID4] = None,
    user_uuid: Optional[UUID4] = None,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None
) -> List[Booking]:
    """ Получает список бронирований с фильтрацией и проверкой прав """
    query = Booking.all().prefetch_related('broker', 'auditorium')

    if current_user.role != UserRole.MODERATOR:
        query = query.filter(broker_id=current_user.uuid)
        if user_uuid is not None and user_uuid != current_user.uuid:
             raise HTTPException(status_code=403, detail="Вы не можете просматривать бронирования других пользователей.")
    elif user_uuid is not None:
        query = query.filter(broker_id=user_uuid)

    if auditorium_uuid:
        query = query.filter(auditorium_id=auditorium_uuid)

    if start_date:
        start_datetime = datetime.combine(start_date, datetime.time.min)
        query = query.filter(start_time__gte=start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.time.max)
        query = query.filter(end_time__lte=end_datetime)

    bookings = await query.order_by('start_time')
    return bookings


@log_calls
async def delete_booking(booking_uuid: UUID4, current_user: User) -> bool:
    """ Удаляет бронирование по UUID с проверкой прав """
    booking = await Booking.get_or_none(uuid=booking_uuid)
    if not booking:
        return False

    if booking.broker_id != current_user.uuid and current_user.role != UserRole.MODERATOR:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления этого бронирования.")
    try:
        await booking.delete()
        return True
    except Exception as e:
         print(f"Error deleting booking {booking_uuid}: {e}")
         raise HTTPException(status_code=500, detail=f"Не удалось удалить бронирование.")


@log_calls
async def get_bookings_for_calendar(
    auditorium_uuid: UUID4,
    start_date: date,
    end_date: date
) -> List[Booking]:
    """
    Получает список бронирований для указанной аудитории в заданном диапазоне дат.
    Возвращает список моделей Booking, готовых для преобразования в CalendarBookingEntry.
    """
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)

    query = Booking.filter(
        auditorium_id=auditorium_uuid,
        start_time__lt=end_dt,
        end_time__gt=start_dt
    ).order_by('start_time')

    bookings = await query.all()
    return bookings


@log_calls
async def get_my_bookings(
    current_user: User,
    auditorium_uuid: Optional[UUID4] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Booking]:
    """
    Получает список бронирований ТЕКУЩЕГО пользователя с возможностью фильтрации.
    """
    query = Booking.filter(broker_id=current_user.uuid)

    if auditorium_uuid:
        query = query.filter(auditorium_id=auditorium_uuid)

    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query = query.filter(start_time__gte=start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(end_time__lte=end_datetime)

    bookings = await query.prefetch_related('broker', 'auditorium').order_by('start_time')
    return bookings