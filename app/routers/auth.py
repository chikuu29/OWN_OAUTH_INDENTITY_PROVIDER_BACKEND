from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.response import APIResponse, ResponseHandler
from app.db.database import get_db
from app.schemas.auth_schemas import LoginSchema, LoginResponse
from app.controllers.auth_controller import authenticateLoginUser
from app.core.security import create_jwt_token, verify_token

# OAuth2 token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter(
    prefix="/auth",  # Optional: Define a prefix for all client routes
    tags=["authentication"],  # Optional: Add a tag for better documentation grouping
)




# Dependency to extract and verify the access token
def get_current_user(access_token: str = Depends(oauth2_scheme)):
    return verify_token(access_token,"REFRESH_SECRET_KEY")


# 🚀 Login User & Get Tokens
@router.post("/login", response_model=LoginResponse)
async def login(
    response: Response,
    loginData: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await authenticateLoginUser(db, loginData)

        # {
        #   "sub": "user123",         // Subject (User ID or Username)
        #   "name": "Jiggu",         // Optional User Information
        #   "email": "jiggu@example.com",
        #   "role": "admin",         // User Role
        #   "exp": 1707849600,       // Expiration Timestamp (Unix Time)
        #   "iat": 1707846000,       // Issued At Timestamp
        #   "iss": "your-api.com",   // Issuer
        #   "aud": "your-client-id"  // Audience (Optional)
        # }
        payload = {
            "email": user.email,
            "username": user.username,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "userFullName": f"{user.first_name} {user.last_name}",
            "tanent_id": user.tenant_id,
            "tanent_name": user.tenant.tenant_name
        }
        access_token = create_jwt_token(payload, timedelta(minutes=7))
        refresh_token = create_jwt_token(payload, timedelta(days=7))

        # 🍪 Set HTTP cookies
        # response.set_cookie(
        #     key="access_token",
        #     value=access_token,
        #     httponly=True,  # Prevent access via JavaScript
        #     secure=True,  # Use HTTPS
        #     samesite="Lax",
        #     max_age=7 * 60  # 7 minutes
        # )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            authProvider="credentials",
            token_type="bearer",
            login_info={
                "email": user.email,
                "username": user.username,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "userFullName": f"{user.first_name} {user.last_name}",
                "phone": user.phone_number,
            },
            success=True,
            message="Login successful",
            error=None,
        )
    except HTTPException as e:
        return LoginResponse(
            access_token=None,
            refresh_token=None,
            authProvider="credentials",
            login_info={},
            success=False,
            message=str(e.detail),
            error={"detail": str(e.detail)},
        )


@router.get("/me")
async def identity(refresh_token: Annotated[str | None, Cookie()] = None):
    print(f"refresh_token", refresh_token)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token found"
        )

    payload = verify_token(refresh_token, "REFRESH_SECRET_KEY")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    print("payload", payload)
    access_token = access_token = create_jwt_token(payload, timedelta(minutes=7))
    return {
        "access_token": access_token,
        "authProvider": "credentials",
        "token_type": "bearer",
        "login_info": payload,
        "success": True,
        "message": "ReLogin successful",
        "error": None,
    }





@router.post("/logout")
def logout(response: Response, token: str = Depends(oauth2_scheme)):
    """Logout by deleting authentication cookies"""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully","success":True}