from fastapi import HTTPException, Depends
from pydantic import UUID4

from app.schemas import UserCreate, UserChangePasswordIn, UserGrantPrivileges
from app.models import User
from app.enums import UserRole
from app.utils import password
from app.utils.contrib import get_current_user


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