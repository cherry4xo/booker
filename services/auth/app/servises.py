from datetime import timedelta

from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas import JWTAccessToken, JWTRefreshToken, JWTToken, CredentialsSchema, RefreshToken
from app.models import User
from app.utils.contrib import authenticate, validate_refresh_token, reusable_oauth2, refresh_oauth2, get_current_user
from app.utils.jwt import create_access_token, create_refresh_token
from app import settings
from app.logger import log_calls


@log_calls
async def get_access_token(credentials: OAuth2PasswordRequestForm = Depends()):
    credentials = CredentialsSchema(email=credentials.username, password=credentials.password)
    user = await authenticate(credentials=credentials)

    if not user:
        raise HTTPException(
            status_code=400,
            detail="incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    return {
        "access_token": create_access_token(data={"user_uuid": str(user.uuid)}, expires_delta=access_token_expires),
        "refresh_token": create_refresh_token(data={"user_uuid": str(user.uuid)}, expires_delta=refresh_token_expires),
        "token_type": "bearer"
    }


@log_calls
async def login_refresh_token(credentials: OAuth2PasswordRequestForm = Depends()):
    credentials = CredentialsSchema(email=credentials.username, password=credentials.password)
    user = await authenticate(credentials=credentials)

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect email or password"
        )
    refresh_token_expires = timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
    
    return {
        "refresh_token": create_refresh_token(data={"user_uuid": str(user.uuid)}, expires_delta=refresh_token_expires),
        "token_type": "bearer"
    }


@log_calls
async def refresh_token(
    token: RefreshToken
):
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user = await validate_refresh_token(token=token.refresh_token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="The user with uuid in token does not exist"
        )

    new_access_token = create_access_token(data={"user_uuid": str(user.uuid), "expires_delta": access_token_expires})
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@log_calls
async def validate_access_token(
    token: str = Security(reusable_oauth2)
):
    return await get_current_user(token=token)