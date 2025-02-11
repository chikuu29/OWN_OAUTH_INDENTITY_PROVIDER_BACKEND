from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.response import APIResponse, ResponseHandler
from app.db.database import get_db
from app.schemas.auth_schemas import LoginSchema,LoginResponse
from app.controllers.auth_controller import authenticateLoginUser
from app.core.security import create_jwt_token


router = APIRouter(
    prefix="/auth",  # Optional: Define a prefix for all client routes
    tags=["authentication"],   # Optional: Add a tag for better documentation grouping
)

# 🚀 Login User & Get Tokens
@router.post('/login',response_model=LoginResponse)
async def login(
    response:Response,
    loginData:OAuth2PasswordRequestForm=Depends(),
    db:AsyncSession=Depends(get_db)):
    try:
        user = await authenticateLoginUser(db, loginData)

        access_token = create_jwt_token({"sub": user.email}, timedelta(minutes=7))
        refresh_token = create_jwt_token({"sub": user.email}, timedelta(days=7))


# 🍪 Set HTTP cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,  # Prevent access via JavaScript
            secure=True,  # Use HTTPS
            samesite="Lax",
            max_age=7 * 60  # 7 minutes
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            authProvider="credentials",
            token_type= "bearer",
            login_info={
                "email": user.email,
                "username": user.username,
                'firstName':user.first_name,
                'lastName':user.last_name,
                'userFullName':f"{user.first_name} {user.last_name}",
                'phone':user.phone_number
            },
            success=True,
            message="Login successful",
            error=None
        )
    except HTTPException as e:
        return LoginResponse(
            access_token=None,
            refresh_token=None,
            authProvider="credentials",
            login_info={},
            success=False,
            message=str(e.detail),
            error={"detail": str(e.detail)}
        )
