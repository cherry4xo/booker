from fastapi import APIRouter, Depends, Security
from fastapi.security import OAuth2PasswordRequestForm

from app.servises import get_access_token, login_refresh_token, refresh_token, validate_access_token, validate_refresh_token
from app.utils.contrib import reusable_oauth2
from app.schemas import JWTToken, JWTRefreshToken, JWTAccessToken, RefreshToken

router = APIRouter()


@router.post("/access-token", response_model=JWTToken, status_code=200)
async def route_access_token(credentials: OAuth2PasswordRequestForm = Depends()):
    return await get_access_token(credentials=credentials)


@router.post("/refresh-token", response_model=JWTRefreshToken, status_code=200)
async def route_refresh_token(credentials: OAuth2PasswordRequestForm = Depends()):
    return await login_refresh_token(credentials=credentials)


@router.post("/refresh", response_model=JWTAccessToken, status_code=200)
async def route_refresh(token: RefreshToken):
    return await refresh_token(token=token)


@router.get("/validate")
async def validate_assess_token(
    token: str = Security(reusable_oauth2)
):
    return await validate_access_token(token=token)