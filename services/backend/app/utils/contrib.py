from typing import Optional

import jwt
from fastapi import HTTPException, Security
from fastapi.security import OAuth2PasswordBearer

from app.models import User
from app.enums import UserRole
from app.schemas import JWTTokenPayload
from app import settings


reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=settings.LOGIN_URL,
)

async def get_current_user(token: str = Security(reusable_oauth2)) -> Optional[User]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        token_data = JWTTokenPayload(**payload)
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    
    user = await User.filter(uuid=token_data.user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


async def get_current_moderator(token: str = Security(reusable_oauth2)) -> Optional[User]:
    user = await get_current_user(token)
    if user.role != UserRole.MODERATOR:
        raise HTTPException(status_code=403, detail="You are not a moderator")
    
    return user