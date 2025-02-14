from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlmodel import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.auth import User
from sqlalchemy.orm import selectinload


# 🔹 Authenticate User Function
async def authenticateLoginUser(db: AsyncSession, loginData: OAuth2PasswordRequestForm):
    result = await db.execute(
        select(User)
        .options(selectinload(User.tenant))
        .filter(
            (User.username == loginData.username) | (User.email == loginData.username)
        )
    )
    user = result.scalars().first()
    if not user or not verify_password(loginData.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    return user
