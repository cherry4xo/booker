from fastapi import APIRouter, Depends, HTTPException

from app.schemas import UserCreate, UserCreated, UserGet, UserChangePasswordIn, UserGrantPrivileges
from app.models import User
from app.services.users import create_user, change_password, grant_user
from app.utils.contrib import get_current_user, get_current_moderator
from app.utils import password


router = APIRouter()


@router.post("/", response_model=UserCreated, status_code=200)
async def route_create_user(user: UserCreate):
    return await create_user(user=user) 


@router.get("/me", response_model=UserGet, status_code=200)
async def route_get_user(user: User = Depends(get_current_user)):
    return user


@router.post("/me/change_password", status_code=200)
async def route_change_password(
    change_password_in: UserChangePasswordIn,
    current_user: User = Depends(get_current_user)
):
    return await change_password(change_password_in=change_password_in, current_user=current_user)


@router.post("/grant", response_model=UserGet, status_code=200)
async def route_grant_user(user: UserGrantPrivileges, current_user: User = Depends(get_current_moderator)):
    return await grant_user(user=user)