# --- Файл: tests/test_services_auditorium.py ---

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pydantic import UUID4 as PydanticUUID4

from fastapi import HTTPException
from tortoise.exceptions import IntegrityError

from services.backend.app.services import auditorium as auditorium_service
from services.backend.app.models import Auditorium
from services.backend.app.schemas import CreateAuditorium, UpdateAuditorium

@pytest.fixture
def mock_auditorium_model():
    aud = MagicMock(spec=Auditorium)
    aud.uuid = uuid4()
    aud.identifier = "Room A"
    aud.capacity = 50
    aud.description = "Test Desc"
    aud.save = AsyncMock()
    aud.delete = AsyncMock()
    # Мок для update_from_dict().save()
    aud.update_from_dict = MagicMock(return_value=aud) # Возвращает self для chaining
    return aud

@pytest.mark.asyncio
async def test_create_auditorium_success():
    aud_data = CreateAuditorium(identifier="New Room", capacity=30, description="A new room")
    with patch('app.models.Auditorium.get_or_none', new_callable=AsyncMock, return_value=None) as mock_get_or_none:
        with patch('app.models.Auditorium') as mock_aud_class:
            mock_save = AsyncMock()
            mock_instance = MagicMock(spec=Auditorium, save=mock_save, **aud_data.model_dump())
            mock_instance.uuid = uuid4()
            mock_aud_class.return_value = mock_instance

            created_aud = await auditorium_service.create_auditorium(aud_data)

            mock_get_or_none.assert_called_once_with(identifier="New Room")
            mock_aud_class.assert_called_once_with(**aud_data.model_dump())
            mock_save.assert_called_once()
            assert created_aud == mock_instance

@pytest.mark.asyncio
@patch('app.services.auditorium.Auditorium.get_or_none', new_callable=AsyncMock)
async def test_update_auditorium_success(mock_get, mock_auditorium_model):
    """ Тест успешного обновления """
    # Первый вызов get_or_none - найти аудиторию для обновления
    # Второй вызов get_or_none - проверить конфликт нового идентификатора (вернет None)
    mock_get.side_effect = [mock_auditorium_model, None]
    aud_uuid = mock_auditorium_model.uuid
    update_data = UpdateAuditorium(identifier="Updated Room A", capacity=60)

    result = await auditorium_service.update_auditorium(auditorium_uuid=aud_uuid, auditorium_update_data=update_data)

    assert mock_get.call_count == 2
    mock_auditorium_model.update_from_dict.assert_called_once_with(update_data.model_dump(exclude_unset=True))
    mock_auditorium_model.save.assert_called_once()
    assert result == mock_auditorium_model

@pytest.mark.asyncio
@patch('app.services.auditorium.Auditorium.get_or_none', new_callable=AsyncMock, return_value=None)
async def test_update_auditorium_not_found(mock_get):
    """ Тест обновления: аудитория не найдена """
    update_data = UpdateAuditorium(capacity=10)
    with pytest.raises(HTTPException) as exc_info:
        await auditorium_service.update_auditorium(uuid4(), update_data)
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
@patch('app.services.auditorium.Auditorium.get_or_none', new_callable=AsyncMock)
async def test_update_auditorium_identifier_conflict(mock_get, mock_auditorium_model):
    """ Тест обновления: конфликт нового идентификатора """
    existing_auditorium_with_new_id = MagicMock(spec=Auditorium, uuid=uuid4())
    # First call finds the auditorium to update
    # Second call finds an *existing* auditorium with the *new* identifier
    mock_get.side_effect = [mock_auditorium_model, existing_auditorium_with_new_id]
    aud_uuid = mock_auditorium_model.uuid
    update_data = UpdateAuditorium(identifier="Existing Identifier") # New identifier that already exists

    with pytest.raises(HTTPException) as exc_info:
        await auditorium_service.update_auditorium(auditorium_uuid=aud_uuid, auditorium_update_data=update_data)

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail
    assert mock_get.call_count == 2
    mock_auditorium_model.save.assert_not_called()

@pytest.mark.asyncio
@patch('app.services.auditorium.Auditorium.get_or_none', new_callable=AsyncMock)
async def test_delete_auditorium_success(mock_get, mock_auditorium_model):
    """ Тест успешного удаления """
    mock_get.return_value = mock_auditorium_model
    await auditorium_service.delete_auditorium(mock_auditorium_model.uuid)
    mock_get.assert_called_once_with(uuid=mock_auditorium_model.uuid)
    mock_auditorium_model.delete.assert_called_once()

@pytest.mark.asyncio
@patch('app.services.auditorium.Auditorium.get_or_none', new_callable=AsyncMock, return_value=None)
async def test_delete_auditorium_not_found(mock_get):
    """ Тест удаления: аудитория не найдена """
    aud_uuid = uuid4()
    with pytest.raises(HTTPException) as exc_info:
        await auditorium_service.delete_auditorium(aud_uuid)
    assert exc_info.value.status_code == 404
    mock_get.assert_called_once_with(uuid=aud_uuid)

# Тесты для get_auditorium_by_uuid и get_auditoriums аналогичны тестам для equipment