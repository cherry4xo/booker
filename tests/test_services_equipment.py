# --- Файл: tests/test_services_equipment.py ---
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from tortoise.exceptions import IntegrityError

from services.backend.app.services import equipment as equipment_service
from services.backend.app.models import Equipment
from services.backend.app.schemas import CreateEquipment, UpdateEquipment

@pytest.fixture
def mock_equipment_model():
    eq = MagicMock(spec=Equipment)
    eq.uuid = uuid4()
    eq.name = "Projector"
    eq.description = "A standard projector"
    eq.save = AsyncMock()
    eq.delete = AsyncMock()
    eq.update_from_dict = MagicMock(return_value=eq)
    return eq

@pytest.mark.asyncio
@patch('app.services.equipment.Equipment.save', new_callable=AsyncMock)
async def test_create_equipment_success(mock_save):
    """ Тест успешного создания оборудования """
    eq_data = CreateEquipment(name="Whiteboard", description="Magnetic whiteboard")
    # Мокаем конструктор
    with patch('app.services.equipment.Equipment', return_value=MagicMock(spec=Equipment, save=mock_save)) as mock_constructor:
        created_eq = await equipment_service.create_equipment(eq_data)

    mock_constructor.assert_called_once_with(**eq_data.model_dump())
    mock_save.assert_called_once()
    assert created_eq is not None

@pytest.mark.asyncio
async def test_create_equipment_name_conflict():
    """ Тест конфликта имени при создании """
    eq_data = CreateEquipment(name="Projector", description="Another projector")
    # Мокаем конструктор и save, чтобы save вызвал IntegrityError
    mock_save = AsyncMock(side_effect=IntegrityError("Unique constraint failed"))
    with patch('app.services.equipment.Equipment', return_value=MagicMock(spec=Equipment, save=mock_save)):
        with pytest.raises(HTTPException) as exc_info:
            await equipment_service.create_equipment(eq_data)
    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail

@pytest.mark.asyncio
@patch('app.services.equipment.Equipment.get_or_none', new_callable=AsyncMock)
async def test_get_equipment_by_id_success(mock_get, mock_equipment_model):
    """ Тест успешного получения по ID """
    mock_get.return_value = mock_equipment_model
    result = await equipment_service.get_equipment_by_id(mock_equipment_model.uuid)
    mock_get.assert_called_once_with(uuid=mock_equipment_model.uuid)
    assert result == mock_equipment_model

@pytest.mark.asyncio
@patch('app.services.equipment.Equipment.get_or_none', new_callable=AsyncMock, return_value=None)
async def test_get_equipment_by_id_not_found(mock_get):
    """ Тест: оборудование не найдено по ID """
    result = await equipment_service.get_equipment_by_id(uuid4())
    assert result is None

@pytest.mark.asyncio
@patch('app.services.equipment.Equipment.all', new_callable=AsyncMock)
async def test_get_all_equipments(mock_all, mock_equipment_model):
    """ Тест получения списка оборудования """
    mock_all.return_value = [mock_equipment_model, MagicMock(spec=Equipment)]
    result = await equipment_service.get_all_equipments()
    mock_all.assert_called_once()
    assert len(result) == 2
    assert result[0] == mock_equipment_model

@pytest.mark.asyncio
@patch('app.services.equipment.Equipment.get_or_none', new_callable=AsyncMock)
async def test_update_equipment_success(mock_get, mock_equipment_model):
    """ Тест успешного обновления оборудования """
    # Первый get_or_none - найти оборудование, второй - проверить конфликт имени (None)
    mock_get.side_effect = [mock_equipment_model, None]
    eq_uuid = mock_equipment_model.uuid
    update_data = UpdateEquipment(name="Super Projector", description="Updated desc")

    result = await equipment_service.update_equipment(eq_uuid, update_data)

    assert mock_get.call_count == 2
    mock_equipment_model.update_from_dict.assert_called_once_with(update_data.model_dump(exclude_unset=True))
    mock_equipment_model.save.assert_called_once()
    assert result == mock_equipment_model

# Добавить тесты для update_equipment_not_found, update_equipment_name_conflict

@pytest.mark.asyncio
@patch('app.services.equipment.Equipment.get_or_none', new_callable=AsyncMock)
async def test_delete_equipment_success(mock_get, mock_equipment_model):
    """ Тест успешного удаления """
    mock_get.return_value = mock_equipment_model
    await equipment_service.delete_equipment(mock_equipment_model.uuid)
    mock_get.assert_called_once_with(uuid=mock_equipment_model.uuid)
    mock_equipment_model.delete.assert_called_once()

@pytest.mark.asyncio
@patch('app.services.equipment.Equipment.get_or_none', new_callable=AsyncMock, return_value=None)
async def test_delete_equipment_not_found(mock_get):
    """ Тест удаления: не найдено """
    eq_uuid = uuid4()
    with pytest.raises(HTTPException) as exc_info:
        await equipment_service.delete_equipment(eq_uuid)
    assert exc_info.value.status_code == 404