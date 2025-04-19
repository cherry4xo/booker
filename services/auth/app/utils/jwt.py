from datetime import datetime, timedelta

import jwt
from fastapi.encoders import jsonable_encoder

from app import settings

ALGORITHM = "HS256"
access_token_jwt_subject = "access"
refresh_token_jwt_subject = "refresh"


def create_access_token(*, data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire.timestamp(), "sub": access_token_jwt_subject})
    encoded_jwt = jwt.encode(jsonable_encoder(to_encode), settings.SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(*, data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire.timestamp(), "sub": refresh_token_jwt_subject})
    encoded_jwt = jwt.encode(jsonable_encoder(to_encode), settings.SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt