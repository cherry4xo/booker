# --- Файл: tests/test_services_availability.py ---
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, create_autospec
from uuid import uuid4
from datetime import time

from fastapi import HTTPException

from services.backend.app.services import availability as availability_service
from services.backend.app.models import Auditorium, AvailabilitySlot
from services.backend.app.schemas import CreateAvailability, UpdateAvailability

@pytest.fixture
def mock_availability_slot():
    slot = MagicMock(spec=AvailabilitySlot)
    slot.uuid = uuid4()
    slot.auditorium_id = uuid4()
    slot.day_of_week = 1 # Tuesday
    slot.start_time = time(9, 0)
    slot.end_time = time(12, 0)
    slot.save = AsyncMock()
    slot.delete = AsyncMock()
    slot.update_from_dict = MagicMock(return_value=slot)
    return slot

# Мок для Auditorium.get_or_none
@pytest_asyncio.fixture
async def mock_get_auditorium():
    with patch('app.services.availability.Auditorium.get_or_none', new_callable=AsyncMock) as mock:
        # Create the mock auditorium instance
        mock_aud = MagicMock(spec=Auditorium)
        # ---> ADD THIS LINE <---
        mock_aud._saved_in_db = True # Indicate it's a "saved" instance
        mock_aud.uuid = uuid4() # Give it a UUID if needed by later code

        mock.return_value = mock_aud # Return the configured mock
        yield mock

# Мок для проверки наложения слотов
@pytest_asyncio.fixture
async def mock_check_overlap():
     with patch('app.services.availability.check_availability_slot_overlap', new_callable=AsyncMock) as mock:
        mock.return_value = True # По умолчанию нет наложения
        yield mock

@pytest.mark.asyncio
async def test_create_availability_success(mock_check_overlap):
    # Create a real auditorium instance
    aud = await Auditorium.create(identifier="Test Aud", capacity=10)
    slot_data = CreateAvailability(
        auditorium=aud.uuid,
        day_of_week=2,
        start_time=time(10, 0),
        end_time=time(11, 0)
    )

    created_slot = await availability_service.create_availability(slot_data)

    assert created_slot.auditorium == aud
    assert created_slot.day_of_week == slot_data.day_of_week
    assert created_slot.start_time == slot_data.start_time
    assert created_slot.end_time == slot_data.end_time
    mock_check_overlap.assert_called_once_with(
        auditorium_uuid=aud.uuid,
        day_of_week=slot_data.day_of_week,
        start_time=slot_data.start_time,
        end_time=slot_data.end_time
    )

@pytest.mark.asyncio
async def test_create_availability_auditorium_not_found(mock_get_auditorium):
    """ Тест: аудитория не найдена при создании слота """
    mock_get_auditorium.return_value = None # Аудитория не найдена
    aud_uuid = uuid4()
    slot_data = CreateAvailability(auditorium=aud_uuid, day_of_week=1, start_time=time(9,0), end_time=time(10,0))
    with pytest.raises(HTTPException) as exc_info:
        await availability_service.create_availability(slot_data)
    assert exc_info.value.status_code == 404
    assert "Auditorium not found" in exc_info.value.detail

@pytest.mark.asyncio
async def test_create_availability_overlap_fails(mock_check_overlap):
    mock_check_overlap.side_effect = HTTPException(status_code=409, detail="Overlap")
    aud = await Auditorium.create(identifier="Test Aud", capacity=10)
    slot_data = CreateAvailability(
        auditorium=aud.uuid,
        day_of_week=1,
        start_time=time(9, 0),
        end_time=time(10, 0)
    )

    with pytest.raises(HTTPException) as exc_info:
        await availability_service.create_availability(slot_data)

    assert exc_info.value.status_code == 409
    assert "Overlap" in exc_info.value.detail
    mock_check_overlap.assert_called_once_with(
        auditorium_uuid=aud.uuid,
        day_of_week=slot_data.day_of_week,
        start_time=slot_data.start_time,
        end_time=slot_data.end_time
    )

# Добавить тесты для get_availability, get_all_availabilities, update_availabilities, delete_availability
# Тесты для update должны мокать get_or_none для слота и check_availability_slot_overlap с exclude_slot_uuid