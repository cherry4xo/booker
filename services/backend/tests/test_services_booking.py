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
async def test_get_booking_by_uuid_success_owner(mock_booking, mock_user_booker):
    """ Тест: успешное получение своей брони """
    # Mock the necessary instance attributes/methods if fetch_related is used later
    mock_booking.broker_id = mock_user_booker.uuid # Set correct owner for permission check
    mock_booking.fetch_related = AsyncMock() # If service uses fetch_related later

    # --- Mock the filter().prefetch_related().first() chain ---
    mock_query = MagicMock()
    mock_query.prefetch_related.return_value = mock_query # Chain prefetch
    mock_query.first = AsyncMock(return_value=mock_booking) # first() returns the booking

    # Patch the initial filter call
    with patch('app.services.booking.Booking.filter', return_value=mock_query) as mock_filter_call:
        booking_uuid = mock_booking.uuid
        result = await booking_service.get_booking_by_uuid(booking_uuid=booking_uuid, current_user=mock_user_booker)

    # Assertions
    mock_filter_call.assert_called_once_with(uuid=booking_uuid)
    mock_query.prefetch_related.assert_called_once_with('broker', 'auditorium')
    mock_query.first.assert_called_once()
    # Permission check happens inside the service based on mock_booking.broker_id
    assert result == mock_booking
    # If fetch_related is called on the instance *after* getting it:
    # mock_booking.fetch_related.assert_called_once_with('broker', 'auditorium')

@pytest.mark.asyncio
# REMOVE mock_get from args if only using 'with patch'
async def test_get_booking_by_uuid_success_moderator(mock_booking, mock_user_moderator):
    """ Тест: успешное получение чужой брони модератором """
    # Mock the instance attributes/methods if needed by service logic
    mock_booking.broker_id = uuid4() # Belongs to someone else
    mock_booking.fetch_related = AsyncMock()

    # --- Mock the filter().prefetch_related().first() chain ---
    mock_query = MagicMock()
    mock_prefetch_chain = MagicMock()
    mock_prefetch_chain.first = AsyncMock(return_value=mock_booking) # first() returns the booking
    mock_query.prefetch_related.return_value = mock_prefetch_chain

    # Patch the initial filter call
    with patch('app.services.booking.Booking.filter', return_value=mock_query) as mock_filter_call:
        booking_uuid = mock_booking.uuid
        result = await booking_service.get_booking_by_uuid(booking_uuid=booking_uuid, current_user=mock_user_moderator)

    # Assertions
    mock_filter_call.assert_called_once_with(uuid=booking_uuid)
    mock_query.prefetch_related.assert_called_once_with('broker', 'auditorium')
    mock_prefetch_chain.first.assert_called_once()
    # Permission check passes because current_user.role is MODERATOR
    assert result == mock_booking

@pytest.mark.asyncio
# REMOVE mock_get from args
async def test_get_booking_by_uuid_forbidden(mock_booking, mock_user_booker, mock_user_moderator): # Keep moderator fixture if needed elsewhere
    """ Тест: запрещено получать чужую бронь (не модератор) """
    other_booker_uuid = uuid4()
    mock_booking.broker_id = other_booker_uuid # Belongs to someone else
    mock_booking.fetch_related = AsyncMock()

    # --- Mock the filter().prefetch_related().first() chain ---
    mock_query = MagicMock()
    mock_prefetch_chain = MagicMock()
    mock_prefetch_chain.first = AsyncMock(return_value=mock_booking) # first() returns the booking
    mock_query.prefetch_related.return_value = mock_prefetch_chain

    # Patch the initial filter call
    with patch('app.services.booking.Booking.filter', return_value=mock_query) as mock_filter_call:
        booking_uuid = mock_booking.uuid
        # current_user is mock_user_booker (role BOOKER)
        with pytest.raises(HTTPException) as exc_info:
            await booking_service.get_booking_by_uuid(booking_uuid=booking_uuid, current_user=mock_user_booker)

    # Assertions
    assert exc_info.value.status_code == 403 # Should now raise correctly
    assert "Недостаточно прав" in exc_info.value.detail
    mock_filter_call.assert_called_once_with(uuid=booking_uuid)
    mock_query.prefetch_related.assert_called_once_with('broker', 'auditorium')
    mock_prefetch_chain.first.assert_called_once()

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
# REMOVE mock_order_by, mock_prefetch, mock_filter from signature
async def test_get_bookings_booker_own(mock_user_booker, mock_booking):
    """ Тест: букер получает свой список броней """
    # --- Mock the all().prefetch_related().filter().order_by() chain ---
    mock_chain = MagicMock()
    mock_prefetch_chain = MagicMock()
    mock_filter_chain = MagicMock()

    # Configure the chain
    mock_chain.prefetch_related.return_value = mock_prefetch_chain
    mock_prefetch_chain.filter.return_value = mock_filter_chain
    # Make the final order_by awaitable and return the list
    mock_filter_chain.order_by = AsyncMock(return_value=[mock_booking])

    # Patch the initial Booking.all() call
    with patch('app.services.booking.Booking.all', return_value=mock_chain) as mock_all_call:
        results = await booking_service.get_bookings(current_user=mock_user_booker)

    # Assertions
    mock_all_call.assert_called_once()
    mock_chain.prefetch_related.assert_called_once_with('broker', 'auditorium')
    # Booker's own bookings: filter by broker_id
    mock_prefetch_chain.filter.assert_called_once_with(broker_id=mock_user_booker.uuid)
    # Check the final ordering and await
    mock_filter_chain.order_by.assert_called_once_with('start_time')
    assert results == [mock_booking]

@pytest.mark.asyncio
async def test_get_bookings_booker_forbidden_other_user(mock_user_booker):
    """ Тест: букер пытается фильтровать по чужому ID """
    with pytest.raises(HTTPException) as exc_info:
         await booking_service.get_bookings(current_user=mock_user_booker, user_uuid=uuid4()) # Передаем чужой UUID
    assert exc_info.value.status_code == 403

@pytest.mark.asyncio
# REMOVE mock_order_by, mock_prefetch, mock_filter from signature
async def test_get_bookings_moderator_filter_user(mock_user_moderator, mock_booking):
    """ Тест: модератор фильтрует по ID пользователя """
    target_user_uuid = uuid4()

    # --- Mock the all().prefetch_related().filter().order_by() chain ---
    mock_chain = MagicMock()
    mock_prefetch_chain = MagicMock()
    mock_filter_chain = MagicMock() # Mock for filter by user_uuid
    # Mock for potential date/auditorium filters (if any) - adjust if needed
    mock_final_filter_chain = MagicMock()

    # Configure the chain
    mock_chain.prefetch_related.return_value = mock_prefetch_chain
    # First filter (by user_uuid)
    mock_prefetch_chain.filter.return_value = mock_filter_chain
    # Assume other filters might be applied, returning final mock
    # If no other filters are applied in this test case, filter_chain can directly call order_by
    mock_filter_chain.filter.return_value = mock_final_filter_chain # If there were date/auditorium filters
    # Make the final order_by awaitable and return the list
    # Apply order_by to the correct chain link depending on filters applied
    mock_filter_chain.order_by = AsyncMock(return_value=[mock_booking]) # If no other filters
    # mock_final_filter_chain.order_by = AsyncMock(return_value=[mock_booking]) # If other filters applied

    # Patch the initial Booking.all() call
    with patch('app.services.booking.Booking.all', return_value=mock_chain) as mock_all_call:
         await booking_service.get_bookings(current_user=mock_user_moderator, user_uuid=target_user_uuid)

    # Assertions
    mock_all_call.assert_called_once()
    mock_chain.prefetch_related.assert_called_once_with('broker', 'auditorium')
    # Moderator filters by user_id
    mock_prefetch_chain.filter.assert_called_once_with(broker_id=target_user_uuid) # Check filter args
    # Check the final ordering and await was called on the correct part of the chain
    mock_filter_chain.order_by.assert_called_once_with('start_time')

# Добавить тесты для фильтрации по датам и аудитории...

# --- Тесты для update_booking ---

@pytest.mark.asyncio
@patch('app.services.booking.check_auditorium_availability', new_callable=AsyncMock, return_value=True)
@patch('app.services.booking.check_booking_overlap', new_callable=AsyncMock, return_value=True)
@patch('app.services.booking.Auditorium.get_or_none', new_callable=AsyncMock) # Mock for potential auditorium change check
async def test_update_booking_success_owner_time(
    mock_get_aud_check, mock_check_overlap, mock_check_availability, # Args from patches
    mock_booking, mock_user_booker # Fixtures
):
    """ Тест: успешное обновление времени своей брони """
    # Setup mock booking instance (returned by .first())
    mock_booking.broker_id = mock_user_booker.uuid # Owner matches current_user
    mock_booking.save = AsyncMock()
    mock_booking.fetch_related = AsyncMock()
    # Mock update_from_dict to allow chaining with save() and simulate attribute update
    mock_booking.update_from_dict = MagicMock(return_value=mock_booking)


    new_start = mock_booking.start_time + timedelta(minutes=30)
    new_end = mock_booking.end_time + timedelta(minutes=30)
    update_data_schema = UpdateBooking(start_time=new_start, end_time=new_end)
    update_dict = update_data_schema.model_dump(exclude_unset=True) # Data passed to update_from_dict

    # --- Mock the filter().prefetch_related().first() chain ---
    mock_query = MagicMock()
    mock_prefetch_chain = MagicMock()
    mock_prefetch_chain.first = AsyncMock(return_value=mock_booking) # <<< Correctly return mock_booking
    mock_query.prefetch_related.return_value = mock_prefetch_chain

    # Patch the initial Booking.filter call
    with patch('app.services.booking.Booking.filter', return_value=mock_query) as mock_filter_call:
        # --- Simulate attribute update for assertion ---
        # When update_from_dict(...).save() is called, update the mock's attributes
        async def save_side_effect(*args, **kwargs):
             mock_booking.start_time = new_start
             mock_booking.end_time = new_end
        mock_booking.save.side_effect = save_side_effect
        # --- End Simulation ---

        result = await booking_service.update_booking(
            booking_uuid=mock_booking.uuid,
            booking_update_data=update_data_schema,
            current_user=mock_user_booker
        )

    # Assertions
    mock_filter_call.assert_called_once_with(uuid=mock_booking.uuid)
    mock_query.prefetch_related.assert_called_once_with('broker', 'auditorium')
    mock_prefetch_chain.first.assert_called_once()
    mock_check_availability.assert_called_once_with(auditorium_uuid=mock_booking.auditorium_id, start_dt=new_start, end_dt=new_end)
    mock_check_overlap.assert_called_once_with(auditorium_uuid=mock_booking.auditorium_id, start=new_start, end=new_end, exclude_booking_uuid=mock_booking.uuid)
    mock_booking.update_from_dict.assert_called_once_with(update_dict)
    mock_booking.save.assert_awaited_once()
    mock_booking.fetch_related.assert_awaited_once_with('broker', 'auditorium')
    assert result == mock_booking
    # Check attributes were updated (due to save_side_effect simulation)
    assert result.start_time == new_start
    assert result.end_time == new_end

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
async def test_update_booking_forbidden(mock_booking, mock_user_booker, mock_user_moderator): # Need both user types
    """ Тест: запрещено обновление чужой брони (не модератор) """
    other_booker_uuid = uuid4()
    mock_booking.broker_id = other_booker_uuid # Belongs to someone else
    mock_booking.save = AsyncMock()
    mock_booking.fetch_related = AsyncMock()
    mock_booking.update_from_dict = MagicMock(return_value=mock_booking)


    update_data = UpdateBooking(title="Attempt update")

    # --- Mock the filter().prefetch_related().first() chain ---
    mock_query = MagicMock()
    mock_prefetch_chain = MagicMock()
    mock_prefetch_chain.first = AsyncMock(return_value=mock_booking) # <<< Correctly return mock_booking
    mock_query.prefetch_related.return_value = mock_prefetch_chain

    # Patch the initial Booking.filter call
    with patch('app.services.booking.Booking.filter', return_value=mock_query) as mock_filter_call:
         # current_user is mock_user_booker (role BOOKER), booking belongs to other_booker
         with pytest.raises(HTTPException) as exc_info:
              await booking_service.update_booking(
                  booking_uuid=mock_booking.uuid,
                  booking_update_data=update_data,
                  current_user=mock_user_booker # Using booker, not moderator
              )

    # Assertions
    assert exc_info.value.status_code == 403 # <<< Should be 403 now
    assert "Недостаточно прав" in exc_info.value.detail
    mock_filter_call.assert_called_once_with(uuid=mock_booking.uuid)
    mock_query.prefetch_related.assert_called_once_with('broker', 'auditorium')
    mock_prefetch_chain.first.assert_called_once()
    mock_booking.save.assert_not_called()

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