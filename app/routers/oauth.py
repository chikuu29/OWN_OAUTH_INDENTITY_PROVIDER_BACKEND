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

from app.controllers.oauth_controller import validateClientDetails
from app.core.response import APIResponse, ResponseHandler
from app.core.security import generate_auth_code
from app.db.database import get_db
from app.routers.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.oauth_schemas import OauthRequest, OauthResponse

from datetime import datetime, timedelta


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
        expires_at = datetime.utcnow() + timedelta(seconds=59)
        OAUTH_FLOW_USER_CONSENT_STORAGE[validateClient.get("client_id")] = {
            **validateClient,
            **{"expires_at": expires_at},
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

    indenity = (
        OAUTH_FLOW_USER_CONSENT_STORAGE[client_id]
        if OAUTH_FLOW_USER_CONSENT_STORAGE[client_id] is not None
        else None
    )
    extra_params = ""
    if state:
        extra_params += f"&state={state}"

    if indenity is not None:
        print("====indentity found===", indenity)
        if datetime.utcnow() < indenity["expires_at"]:
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
            f"{redirect_url}?error=indenity_not_found{extra_params}"
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
@router.post("/token")
def token(grant_type: str = Form(...), code: str = Form(...), client_id: str = Form(...)):
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="Unsupported grant_type")

    # auth_code_data = auth_codes.pop(code, None)
    # if not auth_code_data or auth_code_data["client_id"] != client_id:
    #     raise HTTPException(status_code=400, detail="Invalid authorization code")

    access_token = str(uuid.uuid4())
    id_token = str(uuid.uuid4())

    return {
        "access_token": access_token,
        "id_token": id_token,
        "token_type": "Bearer",
        "expires_in": 3600
    }