# --- Файл: tests/test_services_availability.py ---
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
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
        mock.return_value = MagicMock(spec=Auditorium) # Возвращаем мок аудитории
        yield mock

# Мок для проверки наложения слотов
@pytest_asyncio.fixture
async def mock_check_overlap():
     with patch('app.services.availability.check_availability_slot_overlap', new_callable=AsyncMock) as mock:
        mock.return_value = True # По умолчанию нет наложения
        yield mock

@pytest.mark.asyncio
async def test_create_availability_success(mock_get_auditorium, mock_check_overlap):
    """ Тест успешного создания слота доступности """
    aud_uuid = uuid4()
    slot_data = CreateAvailability(
        auditorium=aud_uuid,
        day_of_week=2,
        start_time=time(10, 0),
        end_time=time(11, 0)
    )
    mock_save_slot = AsyncMock()
    # Мокаем конструктор и save
    with patch('app.services.availability.AvailabilitySlot', return_value=MagicMock(spec=AvailabilitySlot, save=mock_save_slot)) as mock_constructor:
        created_slot = await availability_service.create_availability(slot_data)

    mock_get_auditorium.assert_called_once_with(uuid=aud_uuid)
    mock_check_overlap.assert_called_once_with(
        auditorium_uuid=aud_uuid,
        day_of_week=2,
        start_time=time(10, 0),
        end_time=time(11, 0)
    )
    mock_constructor.assert_called_once_with(**slot_data.model_dump())
    mock_save_slot.assert_called_once()
    assert created_slot is not None

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
async def test_create_availability_overlap_fails(mock_get_auditorium, mock_check_overlap):
    """ Тест: наложение слотов при создании """
    mock_check_overlap.side_effect = HTTPException(status_code=409, detail="Overlap") # Симулируем ошибку наложения
    aud_uuid = uuid4()
    slot_data = CreateAvailability(auditorium=aud_uuid, day_of_week=1, start_time=time(9,0), end_time=time(10,0))
    with pytest.raises(HTTPException) as exc_info:
        await availability_service.create_availability(slot_data)
    assert exc_info.value.status_code == 409
    assert "Overlap" in exc_info.value.detail
    mock_get_auditorium.assert_called_once() # Убедимся, что аудиторию проверили
    mock_check_overlap.assert_called_once()


# Добавить тесты для get_availability, get_all_availabilities, update_availabilities, delete_availability
# Тесты для update должны мокать get_or_none для слота и check_availability_slot_overlap с exclude_slot_uuid