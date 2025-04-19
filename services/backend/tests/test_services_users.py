# --- Файл: tests/test_services_users.py ---
import pytest
import pytest_asyncio
from app.utils.password import pwd_context 
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from services.backend.app.services import users as user_service
from services.backend.app.models import User
from app.enums import UserRole
from services.backend.app.schemas import UserCreate, UserChangePasswordIn, UserGrantPrivileges

@pytest.fixture
def mock_user_model():
    user = MagicMock(spec=User)
    user.uuid = uuid4()
    user.username = "testuser"
    user.email = "test@example.com"
    # Use a real hash for a known password
    user.password_hash = pwd_context.hash("correct_password")
    user.role = UserRole.BOOKER
    user.save = AsyncMock()
    return user

@pytest.mark.asyncio
@patch('app.services.users.User.get_or_none', new_callable=AsyncMock, return_value=None)
@patch('app.services.users.User.create', new_callable=AsyncMock)
async def test_create_user_success(mock_model_create, mock_get_or_none, mock_user_model):
    """ Тест успешного создания пользователя """
    mock_model_create.return_value = mock_user_model
    user_data = UserCreate(username="newuser", email="new@example.com", password="password123")

    created_user = await user_service.create_user(user_data)

    assert mock_get_or_none.call_count == 2
    mock_model_create.assert_called_once_with(user=user_data)
    assert created_user == mock_user_model

@pytest.mark.asyncio
@patch('app.services.users.User.get_or_none', new_callable=AsyncMock)
async def test_create_user_email_exists(mock_get_or_none, mock_user_model):
    """ Тест: email уже существует """
    mock_get_or_none.return_value = mock_user_model
    user_data = UserCreate(username="newuser", email="test@example.com", password="password123")
    with pytest.raises(HTTPException) as exc_info:
        await user_service.create_user(user_data)
    assert exc_info.value.status_code == 400
    assert "email already exists" in exc_info.value.detail
    mock_get_or_none.assert_called_once_with(email=user_data.email)

@pytest.mark.asyncio
@patch('app.services.users.User.get_or_none', new_callable=AsyncMock)
async def test_create_user_username_exists(mock_get_or_none, mock_user_model):
    """ Тест: username уже существует """
    mock_get_or_none.side_effect = [None, mock_user_model]
    user_data = UserCreate(username="testuser", email="new@example.com", password="password123")
    with pytest.raises(HTTPException) as exc_info:
        await user_service.create_user(user_data)
    assert exc_info.value.status_code == 400
    assert "username already exists" in exc_info.value.detail
    assert mock_get_or_none.call_count == 2

@pytest.mark.asyncio
@patch('app.services.users.password.get_password_hash', return_value="new_hashed_password")
async def test_change_password_success(mock_get_hash, mock_user_model):
    """ Тест успешной смены пароля """
    change_data = UserChangePasswordIn(current_password="correct_password", new_password="new_password")

    await user_service.change_password(change_data, mock_user_model)

    mock_get_hash.assert_called_once_with("new_password")
    assert mock_user_model.password_hash == "new_hashed_password"
    mock_user_model.save.assert_called_once()

@pytest.mark.asyncio
async def test_change_password_incorrect_current(mock_user_model):
    """ Тест: неверный текущий пароль """
    change_data = UserChangePasswordIn(current_password="wrong_old", new_password="new_password")
    with pytest.raises(HTTPException) as exc_info:
        await user_service.change_password(change_data, mock_user_model)

    assert exc_info.value.status_code == 401
    assert "incorrect" in exc_info.value.detail or "Invalid" in exc_info.value.detail
    mock_user_model.save.assert_not_called()

@pytest.mark.asyncio
@patch('app.services.users.User.get_or_none', new_callable=AsyncMock)
async def test_grant_user_success(mock_get, mock_user_model):
    """ Тест успешного назначения роли """
    mock_get.return_value = mock_user_model
    grant_data = UserGrantPrivileges(role=UserRole.MODERATOR.value)
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