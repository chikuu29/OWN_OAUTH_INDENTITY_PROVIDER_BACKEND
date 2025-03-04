from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security.oauth_token_service import validate_token

# oauth2_scheme = OAuth2AuthorizationCodeBearer(tokenUrl="/auth/login")
# Define OAuth2 Authorization Code Bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def getRequestIdentity(access_token: str = Depends(oauth2_scheme)):
    print("====VALIDATE ACCESSTOKEN===")
    if access_token.startswith("Bearer "):
        access_token = access_token[len("Bearer ") :]
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    print("===AUTHORIZATION TOKEN===", access_token)
    
    indentity = await validate_token(TOKEN=access_token)
    print("DecodeData", indentity)
    if indentity is not None and indentity["token_type"] == "access_token":

        return indentity

    else:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Access Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

 
