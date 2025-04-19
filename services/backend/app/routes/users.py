from fastapi import APIRouter, Body, Depends, HTTPException, Path
from pydantic import UUID4
from typing import List

from app.schemas import UserCreate, UserCreated, UserGet, UserChangePasswordIn, UserGrantPrivileges, UserUpdateProfile
from app.models import User
from app.services.users import create_user, change_password, grant_user, update_profile
from app.utils.contrib import get_current_user, get_current_moderator
from app.utils import password


router = APIRouter()


@router.post("/", response_model=UserCreated, status_code=201)
async def route_create_user(user: UserCreate):
    created_user = await create_user(user=user)
    if not created_user:
        raise HTTPException(status_code=400, detail="User registration failed.") 
    return created_user


@router.get("/me", response_model=UserGet, status_code=200)
async def route_get_user(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserGet, status_code=200)
async def route_update_user_me(
    profile_data: UserUpdateProfile,
    current_user: User = Depends(get_current_user)
):
    """
    Обновляет профиль текущего пользователя (например, telegram_id).
    Требует аутентификации.
    """
    updated_user = await update_profile(
        current_user=current_user,
        profile_data=profile_data
    )
    return updated_user


@router.post("/me/change_password", status_code=200)
async def route_change_password(
    change_password_in: UserChangePasswordIn,
    current_user: User = Depends(get_current_user)
):
    return await change_password(change_password_in=change_password_in, current_user=current_user)


@router.post("/{user_uuid}/grant", response_model=UserGet, status_code=200)
async def route_grant_user_privileges(
    user_uuid: UUID4 = Path(..., title="UUID пользователя для изменения роли"),
    grant_data: UserGrantPrivileges = Body(...),
    current_moderator: User = Depends(get_current_moderator)
):
    """
    Назначает или изменяет роль указанному пользователю.
    Требует прав модератора.
    """
    updated_user = await grant_user(user_uuid=user_uuid, user_grant=grant_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found or role update failed.")
    return updated_user