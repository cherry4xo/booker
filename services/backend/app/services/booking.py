from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, Depends
from tortoise.exceptions import IntegrityError

from app.schemas import CreateBooking, GetBooking, UpdateBooking, DeleteBooking
from app.models import Auditorium, AvailabilitySlot, User, Booking, UserRole
from pydantic import UUID4


async def check_auditorium_availability(
    auditorium_uuid: UUID4,
    start_dt: datetime,
    end_dt: datetime
) -> bool:
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="Время окончания должно быть после времени начала.")

    # Словарь для кэширования слотов по дню недели, чтобы избежать лишних запросов к БД
    availability_slots_cache = {}

    current_check_dt = start_dt
    while current_check_dt < end_dt:
        current_date = current_check_dt.date()
        day_of_week = current_date.weekday() # 0 = Понедельник, 6 = Воскресенье

        # Определяем конец текущего проверяемого сегмента: либо конец бронирования,
        # либо начало следующего дня (полночь)
        segment_end_for_date = min(end_dt, datetime.datetime.combine(current_date + datetime.timedelta(days=1), datetime.time.min, tzinfo=start_dt.tzinfo)) # Сохраняем TZ info

        # Определяем временной интервал, который нужно проверить для *текущей даты*
        check_start_time = current_check_dt.time()
        # Если segment_end_for_date - это полночь, то конечное время для проверки - 23:59:59...
        check_end_time = segment_end_for_date.time() if segment_end_for_date.date() == current_date else datetime.time(23, 59, 59, 999999)
        # Особый случай: если конец сегмента ровно в 00:00 следующего дня
        if segment_end_for_date.time() == datetime.time(0,0) and segment_end_for_date > current_check_dt:
             check_end_time = datetime.time(23, 59, 59, 999999) # Представляет конец дня для проверки

        # Получаем слоты доступности для этого дня недели (из кэша или БД)
        if day_of_week not in availability_slots_cache:
            slots_for_day = await AvailabilitySlot.filter(
                auditorium_id=auditorium_uuid,
                day_of_week=day_of_week
            ).order_by('start_time').all()
            availability_slots_cache[day_of_week] = slots_for_day
        else:
            slots_for_day = availability_slots_cache[day_of_week]

        if not slots_for_day:
             # Если на этот день вообще нет слотов, а бронь его затрагивает
             raise HTTPException(
                status_code=400,
                detail=(f"Аудитория недоступна в указанный интервал. "
                        f"Нет расписания доступности на {current_date.strftime('%A, %Y-%m-%d')}.")
             )

        time_covered_until = check_start_time # С какого времени интервал уже покрыт
        segment_fully_covered = False

        if check_start_time == check_end_time and check_start_time == datetime.time(0, 0):
             segment_fully_covered = True
        else:
            sorted_slots = sorted(slots_for_day, key=lambda s: s.start_time) # Убедимся, что отсортированы
            for slot in sorted_slots:
                effective_slot_end = slot.end_time if slot.end_time != datetime.time(0, 0) else datetime.time(23, 59, 59, 999999)

                if slot.start_time > time_covered_until:
                    break

                if slot.start_time <= time_covered_until and effective_slot_end > time_covered_until:
                    time_covered_until = max(time_covered_until, effective_slot_end)

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
                             f"между {check_start_time.strftime('%H:%M')} и {check_end_time.strftime('%H:%M:%S')}. "
                             f"Проверьте расписание доступности.")
                 )

        current_check_dt = segment_end_for_date

    return True


async def get_booking_by_uuid(
    uuid: UUID4
) -> GetBooking:
    booking = await Booking.get_or_none(uuid=uuid)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    return booking


async def check_booking_overlap(
    auditorium_uuid: UUID4,
    start: datetime.datetime,
    end: datetime.datetime,
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


async def create_booking(booking_model: CreateBooking, current_user: User) -> GetBooking:
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
            **booking_model.model_dump(exclude={'auditorium_id'}),
            auditorium=auditorium,
            broker=current_user
        )
        await new_booking.save()
        await new_booking.fetch_related('broker', 'auditorium')
        return new_booking
    except IntegrityError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка базы данных при создании бронирования: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Неожиданная ошибка при создании бронирования: {e}"
        )
    
async def update_booking(
    booking_uuid: UUID4,
    booking_update_data: UpdateBooking,
    current_user: User
) -> Booking:
    """ Обновляет существующее бронирование """
    booking = await Booking.get_or_none(uuid=booking_uuid).prefetch_related('broker', 'auditorium') # Подгружаем аудиторию сразу

    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")

    # Проверка прав: пользователь является создателем брони ИЛИ модератором
    if booking.broker_id != current_user.uuid and current_user.role != UserRole.MODERATOR:
        raise HTTPException(
            status_code=404,
            detail="Недостаточно прав для изменения этого бронирования."
        )

    update_data = booking_update_data.model_dump(exclude_unset=True, exclude={'uuid'}) # Исключаем uuid

    # Определяем финальные значения для проверки и обновления
    final_start_time = update_data.get('start_time', booking.start_time)
    final_end_time = update_data.get('end_time', booking.end_time)
    final_auditorium_uuid = update_data.get('auditorium', booking.auditorium_id)

    # --- Проверки перед обновлением ---
    # 1. Проверка, изменилась ли аудитория
    final_auditorium = booking.auditorium # Текущая аудитория по умолчанию
    if 'auditorium' in update_data and update_data['auditorium'] != booking.auditorium_id:
        final_auditorium = await Auditorium.get_or_none(uuid=final_auditorium_uuid)
        if not final_auditorium:
            raise HTTPException(
                status_code=404,
                detail=f"Новая аудитория с UUID {final_auditorium_uuid} не найдена."
            )
        # Если аудитория меняется, нужно присвоить объект полю 'auditorium' в update_data
        update_data['auditorium'] = final_auditorium
    else:
         # Если аудитория не меняется, убираем ее ID из данных для обновления,
         # чтобы не пытаться обновить FK по ID. Или передаем текущий объект.
         if 'auditorium' in update_data:
             del update_data['auditorium'] # Убираем ID, т.к. объект не меняется


    # 2. Проверка доступности и пересечений для *новых* параметров
    await check_auditorium_availability(
        auditorium_uuid=final_auditorium_uuid,
        start_dt=final_start_time,
        end_dt=final_end_time
    )
    await check_booking_overlap(
        auditorium_uuid=final_auditorium_uuid,
        start=final_start_time,
        end=final_end_time,
        exclude_booking_uuid=booking_uuid # Исключаем текущую бронь из проверки
    )
    # --- Конец проверок ---

    # Применяем изменения к объекту booking
    # Можно использовать update_from_dict или присваивать поля вручную
    for key, value in update_data.items():
        setattr(booking, key, value)

    try:
        await booking.save()
        # Подгружаем связанные объекты, если они изменились или для ответа
        await booking.fetch_related('broker', 'auditorium')
        return booking
    except IntegrityError as e:
        raise HTTPException(
            status_code=409,
            detail=f"Ошибка целостности данных при обновлении бронирования: {e}"
        )
    except Exception as e:
        print(f"Unexpected error updating booking: {e}")
        raise HTTPException(
            status_code=500,
            detail="Неожиданная ошибка при обновлении бронирования."
        )

async def get_bookings(
    current_user: User,
    auditorium_uuid: Optional[UUID4] = None,
    user_uuid: Optional[UUID4] = None,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None
) -> List[Booking]:
    query = Booking.all().prefetch_related('broker', 'auditorium')
    if current_user.role != UserRole.MODERATOR:
        query = query.filter(broker_id=current_user.uuid)
        if user_uuid is not None and user_uuid != current_user.uuid:
             raise HTTPException(status_code=403, detail="Вы не можете просматривать бронирования других пользователей.")
    elif user_uuid is not None:
        query = query.filter(broker=user_uuid)
    if auditorium_uuid:
        query = query.filter(auditorium=auditorium_uuid)
    if start_date:
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        # Если работаете с Aware Timezones, убедитесь что start_datetime тоже Aware
        # start_datetime = start_datetime.replace(tzinfo=current_user.timezone_info or datetime.timezone.utc) # Пример
        query = query.filter(start_time__gte=start_datetime)
    if end_date:
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        # end_datetime = end_datetime.replace(tzinfo=current_user.timezone_info or datetime.timezone.utc) # Пример
        query = query.filter(end_time__lte=end_datetime)
    bookings = await query.order_by('start_time')
    return bookings


async def delete_booking(booking_uuid: UUID4, current_user: User) -> bool:
    booking = await Booking.get_or_none(uuid=booking_uuid)
    if not booking:
        return False
    if booking.broker_id != current_user.uuid and current_user.role != UserRole.MODERATOR:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления этого бронирования.")
    try:
        await booking.delete()
        return True
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Не удалось удалить бронирование: {e}")