from fastapi import HTTPException, Depends
from pydantic import UUID4

from app.schemas import UserCreate, UserChangePasswordIn, UserGrantPrivileges, UserUpdateProfile
from app.models import User
from app.enums import UserRole
from app.utils import password
from app.utils.contrib import get_current_user
from tortoise.exceptions import IntegrityError


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


async def grant_user(user_uuid: UUID4, user_grant: UserGrantPrivileges):
    # Assuming User.get_by_uuid is an async function that returns User or None/raises
    user = await User.get_by_uuid(uuid=user_uuid) # Or User.get_or_none(uuid=user_uuid)

    # FIX: Add check if user exists
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # FIX: Check the 'role' attribute of the schema against the list of enum values
    if user_grant.role not in UserRole.list():
        raise HTTPException(
            status_code=400,
            detail="Invalid user role"
        )

    user.role = UserRole(user_grant.role) # Convert string value back to Enum member
    await user.save()
    return user


async def update_profile(current_user: User, profile_data: UserUpdateProfile) -> User:
    """
    Обновляет данные профиля пользователя (пока только telegram_id).
    Применяет только те поля, которые переданы в profile_data.
    """
    # Получаем данные из схемы, исключая не установленные (None)
    update_data = profile_data.model_dump(exclude_unset=True)

    if not update_data:
        # Если в запросе не было данных для обновления
        # Можно вернуть пользователя без изменений или кинуть ошибку 400
        return current_user
        # raise HTTPException(status_code=400, detail="Нет данных для обновления")

    # Обновляем объект пользователя данными из словаря
    current_user.update_from_dict(update_data)

    try:
        # Сохраняем изменения в БД
        await current_user.save(update_fields=list(update_data.keys())) # Оптимизация: обновляем только измененные поля
        print(f"Профиль пользователя {current_user.username} обновлен: {update_data}")
    except IntegrityError as e:
        # Обработка ошибок уникальности, если в будущем добавим такие поля в UserUpdateProfile
        print(f"Ошибка целостности при обновлении профиля {current_user.username}: {e}")
        # Пример: определить, какое поле вызвало конфликт, и вернуть ошибку 409
        # if "unique_constraint_name" in str(e):
        #     raise HTTPException(status_code=409, detail="Конфликт данных. Указанное значение уже используется.")
        raise HTTPException(status_code=500, detail="Ошибка базы данных при обновлении профиля.")
    except Exception as e:
        print(f"Неожиданная ошибка при обновлении профиля {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Не удалось обновить профиль.")

    # Возвращаем обновленный объект пользователя
    return current_user