from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlmodel import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.osecurity import verify_password
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

    # print("====USER====", result)
    user = result.scalars().first()
    # print("====USER====", user.to_dict(include_tenant=True))
    if not user or not verify_password(loginData.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    from app.controllers.account_controller import AccountController
    
    # 🔹 Build Authorization Context
    account_controller = AccountController(db, tenant_uuid=user.tenant.tenant_uuid)
    auth_context = await account_controller.build_account_authorization_context()
    print("====AUTH CONTEXT====", auth_context)
    return user, auth_context




