from typing import Annotated, Optional
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


@router.post("/authorize")
async def authorize(request: Request):
    # Read form data from request
    form_data = await request.form()

    client_id = form_data.get("client_id")
    redirect_url = form_data.get("redirect_url")  # Fixed variable name
    response_type = form_data.get("response_type")
    scope = form_data.get("scope")
    state = form_data.get("state")

    # Validate required parameters
    if not all([client_id, redirect_url, response_type, scope]):
        raise HTTPException(
            status_code=400, detail="Missing required OAuth parameters."
        )

    if response_type != "code":
        raise HTTPException(
            status_code=400, detail="Invalid response_type. Must be 'code'."
        )

    # Generate a fake authorization code
    auth_code = secrets.token_urlsafe(16)

    # Construct the redirect URL with the authorization code
    redirect_url = f"{redirect_url}?code={auth_code}"
    if state:
        redirect_url += f"&state={state}"

    # Perform the redirection
    return RedirectResponse(url=redirect_url)


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
        return ResponseHandler.success(
            message="Authorization successful",
            data=[validateClient],
            login_info=current_user,
        )

    except Exception as e:

        return ResponseHandler.error(message=str(e), error_details={"detail": str(e)})


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
        return RedirectResponse(f"{redirect_url}?error=indenity_not_found{extra_params}")
