from fastapi import HTTPException, Depends
from pydantic import UUID4
from tortoise.exceptions import IntegrityError

from app.schemas import UserCreate, UserChangePasswordIn, UserGrantPrivileges, UserUpdateProfile
from app.models import User
from app.enums import UserRole
from app.utils import password
from app.utils.contrib import get_current_user
from app.logger import log_calls


@log_calls
async def create_user(user: UserCreate):
    user_db = await User.get_by_email(email=user.email)
    
    if user_db is not None:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists"
        )
    
    user_db = await User.get_by_username(username=user.username)

    if user_db is not None:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists"
        )
    
    user_db = await User.create(user=user)
    return user_db


@log_calls
async def change_password(
    change_password_in: UserChangePasswordIn, 
    current_user: User = Depends(get_current_user)
):
    verified, updated_password_hash = password.verify_and_update_password(change_password_in.current_password, 
                                                                          current_user.password_hash)
    if not verified:
        raise HTTPException(
            status_code=401,
            detail="Entered current password is incorrect"
        )

    current_user.password_hash = password.get_password_hash(change_password_in.new_password)
    await current_user.save()


@log_calls
async def grant_user(user_uuid: UUID4, user_grant: UserGrantPrivileges):
    user = await User.get_by_uuid(uuid=user_uuid)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_grant.role not in UserRole.list():
        raise HTTPException(
            status_code=400,
            detail="Invalid user role"
        )

    user.role = UserRole(user_grant.role)
    await user.save()
    return user


@log_calls
async def update_profile(current_user: User, profile_data: UserUpdateProfile) -> User:
    """
    Обновляет данные профиля пользователя (пока только telegram_id).
    Применяет только те поля, которые переданы в profile_data.
    """
    update_data = profile_data.model_dump(exclude_unset=True)

    if not update_data:
        return current_user

    current_user.update_from_dict(update_data)

    try:
        await current_user.save(update_fields=list(update_data.keys()))
        print(f"Профиль пользователя {current_user.username} обновлен: {update_data}")
    except IntegrityError as e:
        print(f"Ошибка целостности при обновлении профиля {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка базы данных при обновлении профиля.")
    except Exception as e:
        print(f"Неожиданная ошибка при обновлении профиля {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Не удалось обновить профиль.")

    return current_user