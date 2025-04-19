# --- Файл: tests/test_services_booking.py ---

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY # ANY для uuid
from uuid import UUID, uuid4
from datetime import datetime, timedelta, date, time

from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist, IntegrityError

# Импортируем тестируемые функции и необходимые модели/схемы/enum
from services.backend.app.services import booking as booking_service
from services.backend.app.models import Booking, User, Auditorium, AvailabilitySlot, UserRole
from services.backend.app.schemas import CreateBooking, UpdateBooking

# Фикстуры для создания mock-объектов
@pytest.fixture
def mock_user_booker():
    user = MagicMock(spec=User)
    user.uuid = uuid4()
    user.role = UserRole.BOOKER
    user.username = "testbooker"
    return user

@pytest.fixture
def mock_user_moderator():
    user = MagicMock(spec=User)
    user.uuid = uuid4()
    user.role = UserRole.MODERATOR
    user.username = "testmoderator"
    return user

@pytest.fixture
def mock_auditorium():
    aud = MagicMock(spec=Auditorium)
    aud.uuid = uuid4()
    aud.identifier = "Room 101"
    return aud

@pytest.fixture
def mock_booking(mock_user_booker, mock_auditorium):
    booking = MagicMock(spec=Booking)
    booking.uuid = uuid4()
    booking.broker_id = mock_user_booker.uuid
    booking.broker = mock_user_booker # Связанный объект
    booking.auditorium_id = mock_auditorium.uuid
    booking.auditorium = mock_auditorium # Связанный объект
    booking.start_time = datetime.now()
    booking.end_time = datetime.now() + timedelta(hours=1)
    booking.title = "Test Booking"
    # Добавляем методы, которые могут быть вызваны
    booking.save = AsyncMock()
    booking.delete = AsyncMock()
    booking.fetch_related = AsyncMock(return_value=None) # fetch_related ничего не возвращает
    booking.update_from_dict = MagicMock(return_value=booking) # Возвращает self для chaining с save()
    return booking

# --- Тесты для create_booking ---

@pytest.mark.asyncio
@patch('app.services.booking.Auditorium.get_or_none', new_callable=AsyncMock)
@patch('app.services.booking.check_auditorium_availability', new_callable=AsyncMock)
@patch('app.services.booking.check_booking_overlap', new_callable=AsyncMock)
@patch('app.services.booking.Booking.save', new_callable=AsyncMock) # Мокаем save экземпляра
@patch('app.services.booking.Booking.fetch_related', new_callable=AsyncMock) # Мокаем fetch_related
async def test_create_booking_success(
    mock_fetch_related, mock_save, mock_check_overlap, mock_check_availability, mock_get_auditorium,
    mock_user_booker, mock_auditorium
):
    """ Тест успешного создания бронирования """
    mock_get_auditorium.return_value = mock_auditorium
    mock_check_availability.return_value = True
    mock_check_overlap.return_value = True

    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)
    booking_data = CreateBooking(
        # uuid не передаем
        auditorium=mock_auditorium.uuid,
        start_time=start_time,
        end_time=end_time,
        title="New Event"
    )

    # Мокаем конструктор Booking, чтобы проверить переданные аргументы
    with patch('app.services.booking.Booking', return_value=MagicMock(spec=Booking, save=mock_save, fetch_related=mock_fetch_related)) as mock_booking_constructor:
        created_booking = await booking_service.create_booking(booking_model=booking_data, current_user=mock_user_booker)

    # Проверяем вызовы
    mock_get_auditorium.assert_called_once_with(uuid=mock_auditorium.uuid)
    mock_check_availability.assert_called_once_with(auditorium_uuid=mock_auditorium.uuid, start_dt=start_time, end_dt=end_time)
    mock_check_overlap.assert_called_once_with(auditorium_uuid=mock_auditorium.uuid, start=start_time, end=end_time)
    # Проверяем, что Booking был создан с правильными аргументами
    mock_booking_constructor.assert_called_once_with(
        auditorium=mock_auditorium,
        broker=mock_user_booker,
        start_time=start_time,
        end_time=end_time,
        title="New Event"
        # uuid генерируется автоматически
    )
    mock_save.assert_called_once()
    mock_fetch_related.assert_called_once_with('broker', 'auditorium')
    assert created_booking is not None # Проверяем, что что-то вернулось (мок конструктора)

@pytest.mark.asyncio
@patch('app.services.booking.Auditorium.get_or_none', new_callable=AsyncMock, return_value=None)
async def test_create_booking_auditorium_not_found(mock_get_auditorium, mock_user_booker):
    """ Тест: аудитория не найдена """
    booking_data = CreateBooking(auditorium=uuid4(), start_time=datetime.now(), end_time=datetime.now()+timedelta(hours=1))
    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(booking_model=booking_data, current_user=mock_user_booker)
    assert exc_info.value.status_code == 404
    assert "Аудитория с UUID" in exc_info.value.detail

@pytest.mark.asyncio
@patch('app.services.booking.Auditorium.get_or_none', new_callable=AsyncMock)
@patch('app.services.booking.check_auditorium_availability', new_callable=AsyncMock, side_effect=HTTPException(status_code=400, detail="Not available"))
async def test_create_booking_availability_fails(mock_check_availability, mock_get_auditorium, mock_user_booker, mock_auditorium):
    """ Тест: проверка доступности не пройдена """
    mock_get_auditorium.return_value = mock_auditorium
    booking_data = CreateBooking(auditorium=mock_auditorium.uuid, start_time=datetime.now(), end_time=datetime.now()+timedelta(hours=1))
    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(booking_model=booking_data, current_user=mock_user_booker)
    assert exc_info.value.status_code == 400
    assert "Not available" in exc_info.value.detail # Проверяем текст ошибки из мока
    mock_check_availability.assert_called_once()

@pytest.mark.asyncio
@patch('app.services.booking.Auditorium.get_or_none', new_callable=AsyncMock)
@patch('app.services.booking.check_auditorium_availability', new_callable=AsyncMock, return_value=True)
@patch('app.services.booking.check_booking_overlap', new_callable=AsyncMock, side_effect=HTTPException(status_code=409, detail="Overlap detected"))
async def test_create_booking_overlap_fails(mock_check_overlap, mock_check_availability, mock_get_auditorium, mock_user_booker, mock_auditorium):
    """ Тест: проверка наложения не пройдена """
    mock_get_auditorium.return_value = mock_auditorium
    booking_data = CreateBooking(auditorium=mock_auditorium.uuid, start_time=datetime.now(), end_time=datetime.now()+timedelta(hours=1))
    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(booking_model=booking_data, current_user=mock_user_booker)
    assert exc_info.value.status_code == 409
    assert "Overlap detected" in exc_info.value.detail
    mock_check_availability.assert_called_once() # Убедимся, что первая проверка прошла
    mock_check_overlap.assert_called_once()


# --- Тесты для get_booking_by_uuid ---

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock)
async def test_get_booking_by_uuid_success_owner(mock_get, mock_booking, mock_user_booker):
    """ Тест: успешное получение своей брони """
    mock_get.return_value.prefetch_related.return_value = mock_booking # Мокаем результат prefetch
    booking_uuid = mock_booking.uuid
    result = await booking_service.get_booking_by_uuid(booking_uuid=booking_uuid, current_user=mock_user_booker)

    mock_get.assert_called_once()
    # Проверяем, что get_or_none был вызван с правильным uuid
    assert mock_get.call_args[1]['uuid'] == booking_uuid
    result.prefetch_related.assert_called_once_with('broker', 'auditorium')
    assert result == mock_booking

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock)
async def test_get_booking_by_uuid_success_moderator(mock_get, mock_booking, mock_user_moderator):
    """ Тест: успешное получение чужой брони модератором """
    mock_get.return_value.prefetch_related.return_value = mock_booking
    booking_uuid = mock_booking.uuid
    result = await booking_service.get_booking_by_uuid(booking_uuid=booking_uuid, current_user=mock_user_moderator)
    assert result == mock_booking

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock)
async def test_get_booking_by_uuid_forbidden(mock_get, mock_booking, mock_user_moderator):
    """ Тест: запрещено получать чужую бронь (не модератор) """
    # Создаем другого юзера-букера
    other_booker = MagicMock(spec=User, uuid=uuid4(), role=UserRole.BOOKER)
    mock_booking.broker_id = other_booker.uuid # Бронь принадлежит другому

    mock_get.return_value.prefetch_related.return_value = mock_booking
    booking_uuid = mock_booking.uuid

    with pytest.raises(HTTPException) as exc_info:
        # Текущий пользователь - модератор из фикстуры, но мы передаем другого booker'а
        await booking_service.get_booking_by_uuid(booking_uuid=booking_uuid, current_user=mock_user_booker) # mock_user_booker пытается получить бронь other_booker

    assert exc_info.value.status_code == 403
    assert "Недостаточно прав" in exc_info.value.detail

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock)
async def test_get_booking_by_uuid_not_found(mock_get, mock_user_booker):
    """ Тест: бронь не найдена """
    mock_get.return_value.prefetch_related.return_value = None # Мокаем результат prefetch как None
    booking_uuid = uuid4()
    result = await booking_service.get_booking_by_uuid(booking_uuid=booking_uuid, current_user=mock_user_booker)
    assert result is None

# --- Тесты для get_bookings ---
# (Более комплексные, мокаем Booking.all().filter()...)

@pytest.mark.asyncio
@patch('app.services.booking.Booking.filter') # Мокаем filter
@patch('app.services.booking.Booking.prefetch_related') # Мокаем prefetch_related
@patch('app.services.booking.Booking.order_by') # Мокаем order_by
async def test_get_bookings_booker_own(mock_order_by, mock_prefetch, mock_filter, mock_user_booker, mock_booking):
    """ Тест: букер получает свой список броней """
    mock_chain = MagicMock()
    # Настраиваем цепочку вызовов: all -> prefetch_related -> filter -> order_by -> await
    with patch('app.services.booking.Booking.all', return_value=mock_chain):
         mock_chain.prefetch_related.return_value = mock_chain
         mock_chain.filter.return_value = mock_chain # filter возвращает query
         mock_chain.order_by.return_value = [mock_booking] # order_by возвращает результат (список)

         results = await booking_service.get_bookings(current_user=mock_user_booker)

    # Проверяем, что был вызван filter с ID текущего юзера
    mock_chain.filter.assert_called_once_with(broker_id=mock_user_booker.uuid)
    mock_chain.order_by.assert_called_once_with('start_time')
    assert results == [mock_booking]

@pytest.mark.asyncio
async def test_get_bookings_booker_forbidden_other_user(mock_user_booker):
    """ Тест: букер пытается фильтровать по чужому ID """
    with pytest.raises(HTTPException) as exc_info:
         await booking_service.get_bookings(current_user=mock_user_booker, user_uuid=uuid4()) # Передаем чужой UUID
    assert exc_info.value.status_code == 403

@pytest.mark.asyncio
@patch('app.services.booking.Booking.filter')
@patch('app.services.booking.Booking.prefetch_related')
@patch('app.services.booking.Booking.order_by')
async def test_get_bookings_moderator_filter_user(mock_order_by, mock_prefetch, mock_filter, mock_user_moderator, mock_booking):
    """ Тест: модератор фильтрует по ID пользователя """
    target_user_uuid = uuid4()
    mock_chain = MagicMock()
    with patch('app.services.booking.Booking.all', return_value=mock_chain):
         mock_chain.prefetch_related.return_value = mock_chain
         mock_chain.filter.return_value = mock_chain # Первый filter (по user_id)
         mock_chain.order_by.return_value = [mock_booking]

         await booking_service.get_bookings(current_user=mock_user_moderator, user_uuid=target_user_uuid)

    # Проверяем, что filter был вызван с target_user_uuid
    mock_chain.filter.assert_called_once_with(broker_id=target_user_uuid) # Исправлено

# Добавить тесты для фильтрации по датам и аудитории...

# --- Тесты для update_booking ---

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock)
@patch('app.services.booking.check_auditorium_availability', new_callable=AsyncMock, return_value=True)
@patch('app.services.booking.check_booking_overlap', new_callable=AsyncMock, return_value=True)
@patch('app.services.booking.Auditorium.get_or_none', new_callable=AsyncMock) # Мокаем для случая смены аудитории
async def test_update_booking_success_owner_time(
    mock_get_auditorium, mock_check_overlap, mock_check_availability, mock_get_booking,
    mock_booking, mock_user_booker
):
    """ Тест: успешное обновление времени своей брони """
    mock_get_booking.return_value.prefetch_related.return_value = mock_booking # Возвращаем существующую бронь

    new_start = mock_booking.start_time + timedelta(minutes=30)
    new_end = mock_booking.end_time + timedelta(minutes=30)
    update_data = UpdateBooking(start_time=new_start, end_time=new_end) # Обновляем только время

    result = await booking_service.update_booking(
        booking_uuid=mock_booking.uuid,
        booking_update_data=update_data,
        current_user=mock_user_booker
    )

    # Проверки
    mock_get_booking.assert_called_once()
    # Проверка доступности/наложения для *новых* времени и *старой* аудитории
    mock_check_availability.assert_called_once_with(auditorium_uuid=mock_booking.auditorium_id, start_dt=new_start, end_dt=new_end)
    mock_check_overlap.assert_called_once_with(auditorium_uuid=mock_booking.auditorium_id, start=new_start, end=new_end, exclude_booking_uuid=mock_booking.uuid)
    # Проверяем, что save был вызван на моке бронирования
    mock_booking.save.assert_called_once()
    # Проверяем, что fetch_related был вызван после save
    mock_booking.fetch_related.assert_called_with('broker', 'auditorium')
    assert result == mock_booking # Должен вернуться обновленный мок
    # Проверяем, что атрибуты мока были обновлены (если мок не был заменен)
    assert mock_booking.start_time == new_start
    assert mock_booking.end_time == new_end

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock)
async def test_update_booking_not_found(mock_get_booking, mock_user_booker):
    """ Тест: обновление несуществующей брони """
    mock_get_booking.return_value.prefetch_related.return_value = None
    update_data = UpdateBooking(title="New Title")
    with pytest.raises(HTTPException) as exc_info:
        await booking_service.update_booking(uuid4(), update_data, mock_user_booker)
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock)
async def test_update_booking_forbidden(mock_get_booking, mock_booking, mock_user_moderator):
    """ Тест: запрещено обновление чужой брони (не модератор) """
    other_booker = MagicMock(spec=User, uuid=uuid4(), role=UserRole.BOOKER)
    mock_booking.broker_id = other_booker.uuid # Бронь принадлежит другому
    mock_get_booking.return_value.prefetch_related.return_value = mock_booking

    update_data = UpdateBooking(title="Attempt update")
    with pytest.raises(HTTPException) as exc_info:
         # mock_user_moderator из фикстуры, но мы передаем другого букера для проверки
         await booking_service.update_booking(mock_booking.uuid, update_data, mock_user_booker)
    assert exc_info.value.status_code == 403

# Добавить тесты для update_booking:
# - Смена аудитории (успех, новая аудитория не найдена)
# - Ошибка проверки доступности при обновлении
# - Ошибка проверки наложения при обновлении

# --- Тесты для delete_booking ---

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock)
async def test_delete_booking_success_owner(mock_get, mock_booking, mock_user_booker):
    """ Тест: успешное удаление своей брони """
    mock_get.return_value = mock_booking
    result = await booking_service.delete_booking(mock_booking.uuid, mock_user_booker)
    mock_get.assert_called_once_with(uuid=mock_booking.uuid)
    mock_booking.delete.assert_called_once()
    assert result is True

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock)
async def test_delete_booking_success_moderator(mock_get, mock_booking, mock_user_moderator):
    """ Тест: успешное удаление чужой брони модератором """
    mock_get.return_value = mock_booking
    result = await booking_service.delete_booking(mock_booking.uuid, mock_user_moderator)
    mock_booking.delete.assert_called_once()
    assert result is True

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock, return_value=None)
async def test_delete_booking_not_found(mock_get, mock_user_booker):
    """ Тест: удаление несуществующей брони """
    result = await booking_service.delete_booking(uuid4(), mock_user_booker)
    mock_get.assert_called_once()
    assert result is False

@pytest.mark.asyncio
@patch('app.services.booking.Booking.get_or_none', new_callable=AsyncMock)
async def test_delete_booking_forbidden(mock_get, mock_booking, mock_user_booker):
    """ Тест: запрещено удаление чужой брони (не модератор) """
    other_booker = MagicMock(spec=User, uuid=uuid4(), role=UserRole.BOOKER)
    mock_booking.broker_id = other_booker.uuid # Принадлежит другому
    mock_get.return_value = mock_booking

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.delete_booking(mock_booking.uuid, mock_user_booker)
    assert exc_info.value.status_code == 403
    mock_booking.delete.assert_not_called() # Убедимся, что delete не вызван