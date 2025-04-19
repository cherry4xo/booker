from datetime import date, datetime, timedelta, time
from builtins import min as builtin_min
from typing import List, Optional

from fastapi import HTTPException, Depends
from tortoise.exceptions import IntegrityError

from app.schemas import CreateBooking, GetBooking, UpdateBooking, DeleteBooking
from app.models import Auditorium, AvailabilitySlot, User, Booking
from app.enums import UserRole
from pydantic import UUID4


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
        segment_end_for_date = builtin_min(end_dt, datetime.combine(current_date + timedelta(days=1), time(0, 0, 0), tzinfo=start_dt.tzinfo))
        check_start_time = current_check_dt.time()
        # ---> FIX: Use datetime.time explicitly <---
        check_end_time = segment_end_for_date.time() if segment_end_for_date.date() == current_date else datetime.time(23, 59, 59, 999999)

        # ---> FIX: Use datetime.time explicitly <---
        if segment_end_for_date.time() == datetime.time(0, 0) and segment_end_for_date > current_check_dt:
        # Around line 37 (assignment inside if)
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

        # ---> FIX: Use datetime.time explicitly <---
        if check_start_time == check_end_time and check_start_time == datetime.time(0, 0):
             segment_fully_covered = True
        else:
            sorted_slots = sorted(slots_for_day, key=lambda s: s.start_time)
            for slot in sorted_slots:
                # ---> FIX: Use datetime.time explicitly <---
                effective_slot_end = slot.end_time if slot.end_time != datetime.time(0, 0) else datetime.time(23, 59, 59, 999999)

                # --- Minor logic refinement suggestion ---
                # Check if the current slot can even cover the start time needed
                if slot.start_time <= time_covered_until and effective_slot_end > time_covered_until:
                    # If the slot starts before or at the time we need coverage for,
                    # and ends after it, it extends our coverage.
                    time_covered_until = max(time_covered_until, effective_slot_end)

                # Optimization: If the next slot starts after the required end time, we can't be covered.
                # (This assumes sorted_slots)
                if slot.start_time > check_end_time:
                    break # Gaps cannot be filled by later slots

                if time_covered_until >= check_end_time:
                    segment_fully_covered = True
                    break
            # --- End refinement suggestion ---

        if not segment_fully_covered:
            auditorium = await Auditorium.get_or_none(uuid=auditorium_uuid)
            identifier = auditorium.identifier if auditorium else str(auditorium_uuid)
            raise HTTPException(
                status_code=400,
                detail=(f"Аудитория '{identifier}' недоступна в запрошенный временной интервал. "
                        f"Проблема в {current_date.strftime('%A, %Y-%m-%d')} "
                        # Show the segment that failed coverage
                        f"между {check_start_time.strftime('%H:%M:%S')} и {check_end_time.strftime('%H:%M:%S')}. "
                        f"Проверьте расписание доступности.")
            )

        current_check_dt = segment_end_for_date

    return True


async def get_booking_by_uuid(booking_uuid: UUID4, current_user: User) -> Optional[Booking]: # Возвращаем модель
    """ Получает бронирование по UUID с проверкой прав """
    booking = await Booking.filter(uuid=booking_uuid).prefetch_related('broker', 'auditorium').first()

    if not booking:
        return None

    # --- Проверка прав доступа ---
    if booking.broker_id != current_user.uuid and current_user.role != UserRole.MODERATOR:
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав для просмотра этого бронирования."
        )
    return booking


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


async def create_booking(booking_model: CreateBooking, current_user: User) -> Booking: # Возвращаем модель
    """ Создает новое бронирование """
    auditorium = await Auditorium.get_or_none(uuid=booking_model.auditorium)
    if not auditorium:
        raise HTTPException(
            status_code=404,
            detail=f"Аудитория с UUID {booking_model.auditorium} не найдена."
        )

    start = booking_model.start_time
    end = booking_model.end_time
    # Убедимся что TZ info консистентно (если используется)
    # ... (логика обработки TZ)

    await check_auditorium_availability(auditorium_uuid=booking_model.auditorium, start_dt=start, end_dt=end)
    await check_booking_overlap(auditorium_uuid=booking_model.auditorium, start=start, end=end)

    try:
        # Создаем объект Booking, UUID генерируется Tortoise
        new_booking = Booking(
            # uuid=uuid.uuid4(), # Генерируем UUID здесь, если Tortoise не настроен на автогенерацию PK
            auditorium=auditorium,
            broker=current_user,
            start_time=start,
            end_time=end,
            title=booking_model.title
        )
        await new_booking.save()
        await new_booking.fetch_related('broker', 'auditorium') # Подгружаем для возврата
        return new_booking # Возвращаем объект модели
    except IntegrityError as e:
        raise HTTPException(
            status_code=409, # Может быть конфликт UUID если генерируем вручную и не уникально
            detail=f"Ошибка целостности данных при создании бронирования: {e}"
        )
    except Exception as e:
        print(f"Unexpected error creating booking: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Неожиданная ошибка при создании бронирования."
        )
    
    
async def update_booking(
    booking_uuid: UUID4,
    booking_update_data: UpdateBooking, # Используем схему UpdateBooking
    current_user: User
) -> Booking: # Возвращаем модель
    """ Обновляет существующее бронирование """
    # Используем стандартный метод Tortoise
    booking = await Booking.filter(uuid=booking_uuid).prefetch_related('broker', 'auditorium').first()

    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")

    # Проверка прав: пользователь является создателем брони ИЛИ модератором
    if booking.broker_id != current_user.uuid and current_user.role != UserRole.MODERATOR:
        raise HTTPException(
            status_code=403, # Исправлен статус на 403
            detail="Недостаточно прав для изменения этого бронирования."
        )

    # Используем exclude_unset=True для поддержки PATCH-семантики
    update_data = booking_update_data.model_dump(exclude_unset=True)

    # Определяем финальные значения для проверки и обновления
    final_start_time = update_data.get('start_time', booking.start_time)
    final_end_time = update_data.get('end_time', booking.end_time)
    final_auditorium_uuid = update_data.get('auditorium', booking.auditorium_id)

    # --- Проверки перед обновлением ---
    final_auditorium = booking.auditorium
    if 'auditorium' in update_data and update_data['auditorium'] != booking.auditorium_id:
        final_auditorium_uuid = update_data['auditorium'] # Берем UUID из данных для обновления
        final_auditorium = await Auditorium.get_or_none(uuid=final_auditorium_uuid)
        if not final_auditorium:
            raise HTTPException(
                status_code=404,
                detail=f"Новая аудитория с UUID {final_auditorium_uuid} не найдена."
            )
        # Для обновления через update_from_dict нужно передать auditorium_id
        update_data['auditorium_id'] = final_auditorium.uuid
        del update_data['auditorium'] # Удаляем ключ 'auditorium', оставляем 'auditorium_id'
    elif 'auditorium' in update_data:
         # Если UUID аудитории передан, но он тот же самый, удаляем его из update_data
         del update_data['auditorium']


    await check_auditorium_availability(
        auditorium_uuid=final_auditorium_uuid, # Используем UUID аудитории
        start_dt=final_start_time,
        end_dt=final_end_time
    )
    await check_booking_overlap(
        auditorium_uuid=final_auditorium_uuid, # Используем UUID аудитории
        start=final_start_time,
        end=final_end_time,
        exclude_booking_uuid=booking_uuid
    )
    # --- Конец проверок ---

    # Применяем изменения к объекту booking
    # Используем update_from_dict для простоты
    await booking.update_from_dict(update_data).save()

    # Подгружаем связанные объекты снова, т.к. update_from_dict их сбрасывает
    await booking.fetch_related('broker', 'auditorium')
    return booking

async def get_bookings(
    current_user: User,
    auditorium_uuid: Optional[UUID4] = None,
    user_uuid: Optional[UUID4] = None,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None
) -> List[Booking]: # Возвращаем список моделей
    """ Получает список бронирований с фильтрацией и проверкой прав """
    query = Booking.all().prefetch_related('broker', 'auditorium')

    if current_user.role != UserRole.MODERATOR:
        query = query.filter(broker_id=current_user.uuid)
        if user_uuid is not None and user_uuid != current_user.uuid:
             raise HTTPException(status_code=403, detail="Вы не можете просматривать бронирования других пользователей.")
    elif user_uuid is not None:
        query = query.filter(broker_id=user_uuid) # Исправлено на _id

    if auditorium_uuid:
        query = query.filter(auditorium_id=auditorium_uuid) # Исправлено на _id

    if start_date:
        start_datetime = datetime.combine(start_date, datetime.time.min)
        # Добавить обработку TZ если необходимо
        query = query.filter(start_time__gte=start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.time.max)
        # Добавить обработку TZ если необходимо
        query = query.filter(end_time__lte=end_datetime)

    bookings = await query.order_by('start_time')
    return bookings


async def delete_booking(booking_uuid: UUID4, current_user: User) -> bool:
    """ Удаляет бронирование по UUID с проверкой прав """
    # Используем стандартный метод Tortoise
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


async def get_bookings_for_calendar(
    auditorium_uuid: UUID4,
    start_date: date,
    end_date: date
) -> List[Booking]:
    """
    Получает список бронирований для указанной аудитории в заданном диапазоне дат.
    Возвращает список моделей Booking, готовых для преобразования в CalendarBookingEntry.
    """
    # Преобразуем даты в datetime для корректного сравнения с полями модели
    # Включаем весь день для start_date и end_date
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)

    # Добавляем обработку часовых поясов, если ваше приложение их использует
    # Например, если start_dt/end_dt должны быть в UTC:
    # from app.utils.timezone import make_aware # Пример хелпера
    # start_dt = make_aware(start_dt)
    # end_dt = make_aware(end_dt)
    # Или используйте timezone.utc из datetime, если время хранится в UTC

    # Запрос для поиска бронирований, которые *пересекаются* с заданным диапазоном [start_dt, end_dt]
    # Условие пересечения: (BookingStart < QueryEnd) AND (BookingEnd > QueryStart)
    query = Booking.filter(
        auditorium_id=auditorium_uuid,
        start_time__lt=end_dt,  # Бронь начинается до конца запрашиваемого периода
        end_time__gt=start_dt   # Бронь заканчивается после начала запрашиваемого периода
    ).order_by('start_time')

    # Если в схеме CalendarBookingEntry нужно имя пользователя, добавь prefetch:
    # query = query.prefetch_related('broker')

    bookings = await query.all()
    return bookings