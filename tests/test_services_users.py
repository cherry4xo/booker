# --- Файл: tests/test_services_users.py ---
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from services.backend.app.services import users as user_service
from services.backend.app.models import User, UserRole
from services.backend.app.schemas import UserCreate, UserChangePasswordIn, UserGrantPrivileges
from services.backend.app.utils import password # Импортируем модуль паролей

@pytest.fixture
def mock_user_model():
    user = MagicMock(spec=User)
    user.uuid = uuid4()
    user.username = "testuser"
    user.email = "test@example.com"
    user.password_hash = "hashed_password"
    user.role = UserRole.BOOKER
    user.save = AsyncMock()
    return user

@pytest.mark.asyncio
@patch('app.services.users.User.get_or_none', new_callable=AsyncMock, return_value=None) # Email и username свободны
@patch('app.services.users.User.create', new_callable=AsyncMock) # Мокаем classmethod create
async def test_create_user_success(mock_model_create, mock_get_or_none, mock_user_model):
    """ Тест успешного создания пользователя """
    mock_model_create.return_value = mock_user_model # Мок create возвращает мок пользователя
    user_data = UserCreate(username="newuser", email="new@example.com", password="password123")

    created_user = await user_service.create_user(user_data)

    assert mock_get_or_none.call_count == 2 # Проверка email и username
    mock_model_create.assert_called_once_with(user=user_data) # Проверяем вызов classmethod
    assert created_user == mock_user_model

@pytest.mark.asyncio
@patch('app.services.users.User.get_or_none', new_callable=AsyncMock) # Находим пользователя по email
async def test_create_user_email_exists(mock_get_or_none, mock_user_model):
    """ Тест: email уже существует """
    mock_get_or_none.return_value = mock_user_model
    user_data = UserCreate(username="newuser", email="test@example.com", password="password123")
    with pytest.raises(HTTPException) as exc_info:
        await user_service.create_user(user_data)
    assert exc_info.value.status_code == 400
    assert "email already exists" in exc_info.value.detail
    mock_get_or_none.assert_called_once_with(email=user_data.email) # Убедимся, что искали по email

@pytest.mark.asyncio
@patch('app.services.users.User.get_or_none', new_callable=AsyncMock)
async def test_create_user_username_exists(mock_get_or_none, mock_user_model):
    """ Тест: username уже существует """
    mock_get_or_none.side_effect = [None, mock_user_model] # Email свободен, username занят
    user_data = UserCreate(username="testuser", email="new@example.com", password="password123")
    with pytest.raises(HTTPException) as exc_info:
        await user_service.create_user(user_data)
    assert exc_info.value.status_code == 400
    assert "username already exists" in exc_info.value.detail
    assert mock_get_or_none.call_count == 2

@pytest.mark.asyncio
@patch('app.services.users.password.verify_password', return_value=True) # Пароль верный
@patch('app.services.users.password.get_password_hash', return_value="new_hashed_password")
async def test_change_password_success(mock_get_hash, mock_verify, mock_user_model):
    """ Тест успешной смены пароля """
    change_data = UserChangePasswordIn(current_password="old_password", new_password="new_password")
    await user_service.change_password(change_data, mock_user_model)

    mock_verify.assert_called_once_with("old_password", "hashed_password")
    mock_get_hash.assert_called_once_with("new_password")
    assert mock_user_model.password_hash == "new_hashed_password"
    mock_user_model.save.assert_called_once()

@pytest.mark.asyncio
@patch('app.services.users.password.verify_password', return_value=False) # Пароль неверный
async def test_change_password_incorrect_current(mock_verify, mock_user_model):
    """ Тест: неверный текущий пароль """
    change_data = UserChangePasswordIn(current_password="wrong_old", new_password="new_password")
    with pytest.raises(HTTPException) as exc_info:
        await user_service.change_password(change_data, mock_user_model)
    assert exc_info.value.status_code == 401
    assert "incorrect" in exc_info.value.detail
    mock_user_model.save.assert_not_called() # Save не должен быть вызван

@pytest.mark.asyncio
@patch('app.services.users.User.get_or_none', new_callable=AsyncMock)
async def test_grant_user_success(mock_get, mock_user_model):
    """ Тест успешного назначения роли """
    mock_get.return_value = mock_user_model
    grant_data = UserGrantPrivileges(role=UserRole.MODERATOR.value) # Используем enum value
    user_uuid_to_grant = uuid4()

    result = await user_service.grant_user(user_uuid_to_grant, grant_data)

    mock_get.assert_called_once_with(uuid=user_uuid_to_grant)
    assert mock_user_model.role == UserRole.MODERATOR
    mock_user_model.save.assert_called_once()
    assert result == mock_user_model

@pytest.mark.asyncio
@patch('app.services.users.User.get_or_none', new_callable=AsyncMock, return_value=None)
async def test_grant_user_not_found(mock_get):
    """ Тест: пользователь для назначения роли не найден """
    grant_data = UserGrantPrivileges(role=UserRole.MODERATOR.value)
    with pytest.raises(HTTPException) as exc_info:
        await user_service.grant_user(uuid4(), grant_data)
    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
@patch('app.services.users.User.get_or_none', new_callable=AsyncMock)
async def test_grant_user_invalid_role(mock_get, mock_user_model):
    """ Тест: невалидная роль при назначении """
    mock_get.return_value = mock_user_model
    grant_data = UserGrantPrivileges(role="invalid_role")
    with pytest.raises(HTTPException) as exc_info:
        await user_service.grant_user(mock_user_model.uuid, grant_data)
    assert exc_info.value.status_code == 400
    assert "Invalid user role" in exc_info.value.detail
    mock_user_model.save.assert_not_called()