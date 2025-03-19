from typing import Annotated, Optional
import uuid
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    FastAPI,
    Form,
    Query,
    Request,
    HTTPException,
    status,
)

from fastapi.responses import JSONResponse, RedirectResponse
import secrets

from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.controllers.application_controller import validate_client
from app.controllers.oauth_controller import validateClientDetails
from app.core.response import APIResponse, ResponseHandler

# from app.core.security import generate_auth_code
from app.core.security.oauth_token_service import (
    generate_oauth_tokens,
    generate_auth_code,
    validate_token,
)
from app.db.database import get_db
from app.routers.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.oauth_schemas import (
    OauthRequest,
    OauthResponse,
    TokenRequest,
    TokenResponse,
)

from datetime import datetime, timedelta

security = HTTPBasic()
# In-memory store for auto tokens (replace with DB)
OAUTH_FLOW_USER_CONSENT_STORAGE = {}


router = APIRouter(
    prefix="/oauth",
    tags=["Authorize"],
)


# -------------------------
# Authorization Endpoint
# -------------------------


@router.get("/authorize", response_model=APIResponse)
async def authorize(
    OauthRequest: OauthRequest = Depends(),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    print("===OauthRequest===", OauthRequest)
    try:

        validateClient = await validateClientDetails(OauthRequest, current_user, db)
        validateClient["OauthRequest"] = OauthRequest.dict()
        expires_at = datetime.now() + timedelta(seconds=59)
        OAUTH_FLOW_USER_CONSENT_STORAGE[validateClient.get("client_id")] = {
            **validateClient,
            **{"expires_at": expires_at.isoformat()},
            **{"login_user": current_user},
        }
        print("OAUTH_FLOW_USER_CONSENT_STORAGE", OAUTH_FLOW_USER_CONSENT_STORAGE)

        if validateClient.get("skip_authorization") is True:

            return ResponseHandler.success(
                message="Authorization successful",
                data=[
                    {
                        **issue_auth_code(
                            client_id=validateClient.get("client_id"),
                            redirect_url=OauthRequest.redirect_url,
                        ),
                        **{"skip_authorization_done": True},
                    }
                ],
                login_info=current_user,
            )
        else:
            return ResponseHandler.success(
                message="Authorization successful",
                data=[validateClient],
                login_info=current_user,
            )

    except Exception as e:

        return ResponseHandler.error(message=str(e), error_details={"detail": str(e)})


# -------------------------
# Consent Decision Endpoint
# -------------------------


@router.post("/grant")
async def grant_access(
    client_id: str = Form(...),
    redirect_url: str = Form(...),
    state: Optional[str] = Form(...),
    action: str = Form(...),
    response_type: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    """Process Allow/Deny response from the frontend."""
    if response_type != "code":
        return RedirectResponse(f"{redirect_url}?error=invalid_response_type")

    print(OAUTH_FLOW_USER_CONSENT_STORAGE)

    identity = (
        OAUTH_FLOW_USER_CONSENT_STORAGE[client_id]
        if OAUTH_FLOW_USER_CONSENT_STORAGE[client_id] is not None
        else None
    )
    extra_params = ""
    if state:
        extra_params += f"&state={state}"

    if identity is not None:
        print("====indentity found===", identity)
        if datetime.utcnow() < identity["expires_at"]:
            if action == "allow":
                auth_code, expires_at = generate_auth_code()
                # Securely generate this in real scenarios
                OAUTH_FLOW_USER_CONSENT_STORAGE[client_id]["auth_code"] = {
                    "auth_code": auth_code,
                    "expires_at": expires_at,
                }
                return RedirectResponse(
                    f"{redirect_url}?code={auth_code}{extra_params}"
                )
            else:
                return RedirectResponse(
                    f"{redirect_url}?error=access_denied{extra_params}"
                )

        else:
            del OAUTH_FLOW_USER_CONSENT_STORAGE[client_id]
            return RedirectResponse(f"{redirect_url}?error=timeout")
    else:
        return RedirectResponse(
            f"{redirect_url}?error=identity_not_found{extra_params}"
        )


# -------------------------
# Helper to Issue Auth Code
# -------------------------
def issue_auth_code(client_id, redirect_url):

    auth_code, expires_at = generate_auth_code()
    # Securely generate this in real scenarios
    OAUTH_FLOW_USER_CONSENT_STORAGE[client_id]["auth_code"] = {
        "auth_code": auth_code,
        "expires_at": expires_at,
    }

    return {"redirect_url": f"{redirect_url}?code={auth_code}", "code": auth_code}


# -------------------------
# Token Exchange
# -------------------------
@router.post("/token", response_model=TokenResponse)
async def token_endpoint(request: TokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Unified OAuth2 Token Endpoint supporting:
    - authorization_code
    - refresh_token
    - password
    Requires client_id and client_secret for authentication.
    """
    # OAUTH_FLOW_USER_CONSENT_STORAGE = {
    #     "client_id": {
    #         "client_id": "client_id",
    #         "client_name": "MYOMSPANEL",
    #         "client_type": "confidential",
    #         "redirect_urls": ["http://localhost:5173/auth/callback"],
    #         "post_logout_redirect_urls": ["https://example.com/logout-callback"],
    #         "token_endpoint_auth_method": "client_secret_basic",
    #         "response_types": ["code"],
    #         "grant_types": ["authorization_code", "refresh_token"],
    #         "allowed_origins": ["http://localhost:5173"],
    #         "scope": ["openid", "profile", "email"],
    #         "skip_authorization": False,
    #         "OauthRequest": {
    #             "client_id": "client_id",
    #             "redirect_url": "http://localhost:5173/auth/callback",
    #             "response_type": "code",
    #             "scope": "openid profile email",
    #             "state": None,
    #             "device_id": "61b2dea5-3ea4-4184-9fa0-c86887efd043",
    #         },
    #         "expires_at": datetime(2025, 3, 2, 9, 27, 44, 6821),
    #         "login_user": {
    #             "email": "cchiku1999@gmail.com",
    #             "username": "SURYA",
    #             "firstName": "SURYANARAYAN",
    #             "lastName": "BISWAL",
    #             "userFullName": "SURYANARAYAN BISWAL",
    #             "tanent_id": 1,
    #             "tenant_name": "DEVELOPER_ORGANTISATION",
    #             "exp": 1740908024,
    #         },
    #         "auth_code": {
    #             "auth_code": "gDBKJ0vh8LoawNDJDTQueEIU8lAMvGh0",
    #             "expires_at": datetime.now() +timedelta(days=14),
    #         },
    #     }
    # }

    # Retrieve user consent identity from storage
    identity = OAUTH_FLOW_USER_CONSENT_STORAGE.get(request.client_id)
    print("===identity===", identity)

    # Validate if identity exists
    if identity is None:
        return JSONResponse(
            content=TokenResponse(
                message="OAuth session not found, or the refresh token/authorization code has expired.",
                success=False,
            ).model_dump(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Validate device ID
    device_id = identity.get("OauthRequest", {}).get("device_id")
    if device_id != request.device_id:
        return JSONResponse(
            content=TokenResponse(
                message="Device ID mismatch detected. Please ensure you are using the correct device.",
                success=False,
            ).model_dump(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Validate client credentials
    if request.client_id and request.client_secret:
        try:
            dbClient = await validate_client(
                request.client_id, request.client_secret, db
            )
        except ValueError as e:
            return JSONResponse(
                content=TokenResponse(
                    message="Invalid Client ID or Client Secret",
                    errors=e.args[0],
                    success=False,
                ).model_dump(),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
    else:
        return JSONResponse(
            content=TokenResponse(
                message="Invalid Client ID or Client Secret",
                success=False,
            ).model_dump(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Handle supported grant types
    if (
        request.grant_type in dbClient.grant_types
        and request.grant_type == "authorization_code"
    ):
        auth_code_details = identity.get("auth_code", {})
        auth_code = auth_code_details.get("auth_code", None)
        expires_at = auth_code_details.get("expires_at", None)
        # expires_at = identity.get("auth_code", (None, None))
        # Validate authorization code and expiry
        if auth_code and expires_at is not None:
            print("===expires_at", expires_at)
            # if datetime.now() < expires_at:

            if request.code == auth_code and datetime.now() < datetime.fromisoformat(expires_at):
                access_token, refresh_token, id_token, refresh_exp, id_token_exp = (
                    generate_oauth_tokens(identity)
                )

                del OAUTH_FLOW_USER_CONSENT_STORAGE[request.client_id]["auth_code"]
                return TokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    id_token=id_token,
                    refresh_exp=refresh_exp,
                    id_token_exp=id_token_exp,
                    login_info=identity.get("login_user", {}),
                    message="Token exchange successful. Access and refresh tokens have been issued.",
                    success=True,
                )
            else:
                return JSONResponse(
                    content=TokenResponse(
                        message="Authorization code has expired.",
                        success=False,
                    ).model_dump(),
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        else:
            return JSONResponse(
                content=TokenResponse(
                    message="Invalid authorization code.",
                    success=False,
                ).model_dump(),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    # Handle refresh_token grant type
    elif request.grant_type == "refresh_token":
        try:
            decodeData = await validate_token(TOKEN=request.refresh_token)
            print("DecodeData", decodeData)
            if decodeData is not None and decodeData["token_type"] == "refresh_token":

                access_token, refresh_token, id_token, refresh_exp, id_token_exp = (
                    generate_oauth_tokens(identity, include_refresh=False)
                )

                return TokenResponse(
                    access_token=access_token,
                    refresh_token=None,
                    id_token=id_token,
                    refresh_exp=None,
                    id_token_exp=id_token_exp,
                    message="New Access Token Generated Successfully.",
                    success=True,
                )

            else:
                JSONResponse(
                    content=TokenResponse(
                        message="Invalid Refresh Token",
                        success=False,
                    ).model_dump(),
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return JSONResponse(
                content=TokenResponse(
                    message=str(e),
                    success=False,
                ).model_dump(),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    # Unsupported grant type
    else:
        return JSONResponse(
            content=TokenResponse(
                message="Unsupported grant_type.",
                success=False,
            ).model_dump(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
