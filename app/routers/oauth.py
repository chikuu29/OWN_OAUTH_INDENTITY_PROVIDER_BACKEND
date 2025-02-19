from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, FastAPI, Form, Query, Request, HTTPException,status
from fastapi.responses import JSONResponse, RedirectResponse
import secrets

from app.controllers.oauth_controller import validateClientDetails
from app.core.response import APIResponse, ResponseHandler
from app.db.database import get_db
from app.routers.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.oauth_schemas import OauthRequest, OauthResponse

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
        raise HTTPException(status_code=400, detail="Missing required OAuth parameters.")

    if response_type != "code":
        raise HTTPException(status_code=400, detail="Invalid response_type. Must be 'code'.")

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
    # client_id: str = Query(...),
    # response_type: str = Query(...),
    # redirect_url: str = Query(...),
    # scope: str = Query(...)
    # client_id: str,
    # redirect_url: str,
    # response_type: str,
    # scope: str,
    # state: str = None,
    # device_id: str = None,
    OauthRequest: OauthRequest=Depends(),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # print(client_id, response_type, redirect_url, scope)
    print("===OauthRequest===", OauthRequest)
    try:
        # Validate required parameters
    

        # if clientData.response_type != "code":
        #     raise ValueError("Invalid response_type. Must be 'code'.")
        

        validateClient = await validateClientDetails(OauthRequest, current_user,db)
        # merged_data = {**validateClient, **OauthRequest.dict()} 
        validateClient['OauthRequest'] = OauthRequest.dict()
        return ResponseHandler.success(
            message="Authorization successful",
            data=[validateClient],
            login_info=current_user
        )
       

        
    except Exception as e:
        
        return ResponseHandler.error(
            message=str(e),
            error_details={"detail": str(e)}
        )
       


@router.post("/grant")
async def grant_access(
    client_id: str = Form(...), redirect_url: str = Form(...), state: str = Form(...), action: str = Form(...)
):
    """ Process Allow/Deny response from the frontend. """
    print(client_id, redirect_url, state, action)
    if action == "allow":
        auth_code = "authcode123"  # Securely generate this in real scenarios
        # user_consent_storage[auth_code] = client_id
        return RedirectResponse(f"{redirect_url}?code={auth_code}&state={state}")
    else:
        return RedirectResponse(f"{redirect_url}?error=access_denied&state={state}")

@router.post("/authorize")
async def authorize(request: Request):
    pass