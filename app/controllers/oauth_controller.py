
from app.schemas.oauth_schemas import OauthRequest
from sqlalchemy import select

from app.models.client import OAuthClient 
from sqlalchemy.ext.asyncio import AsyncSession

async def validateClientDetails(OauthRequest:OauthRequest, current_user, db: AsyncSession):
    # Check if client_id exists
    client = await db.execute(select(OAuthClient).filter(OAuthClient.client_id == OauthRequest.client_id))
    client = client.scalars().first()
    if not client:
        raise ValueError("Invalid client_id.")
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id.")

    # Check if the redirect URL is allowed
    if OauthRequest.redirect_url not in client.redirect_urls:
        raise ValueError("Invalid redirect_url.")
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid redirect_url.")

    # Check if the response type is allowed
    if OauthRequest.response_type not in client.response_types:
        raise ValueError("Invalid response_type.")
       

    # Check if the scope is allowed


    for i in OauthRequest.scope.split(" "):
        if i not in client.scope:
            raise ValueError(f"Invalid scope {i}")
            # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid scope.") 
   
       
        
    # Return Client Details except Secret Key
    return {
        "client_id": client.client_id,
        "client_name": client.client_name,
        "client_type": client.client_type,
        "redirect_urls": client.redirect_urls,
        "post_logout_redirect_urls": client.post_logout_redirect_urls,
        "token_endpoint_auth_method": client.token_endpoint_auth_method,
        "response_types": client.response_types,
        "grant_types": client.grant_types,
        "allowed_origins": client.allowed_origins,
        "scope": client.scope,
        "skip_authorization": client.skip_authorization

        
    }
