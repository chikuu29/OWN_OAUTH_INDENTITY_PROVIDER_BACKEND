from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.client import OAuthClientCreate 
from app.crud.client import create_oauth_client
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import APIResponse


router = APIRouter(
    prefix="/clients",  # Optional: Define a prefix for all client routes
    tags=["Clients"],   # Optional: Add a tag for better documentation grouping
)

@router.post("/",response_model=APIResponse)
async def register_oauth_client(client:OAuthClientCreate, db: AsyncSession  = Depends(get_db)):
        print(f"==CALLING register_oauth_client====")
        print(f"Client",client)
        try:
            db_client= await create_oauth_client(db=db,client=client)
            print('db_client',db_client)
            response = APIResponse(
                success=True,
                message="Client registered successfully",
                data=[{
                    "client_id": db_client.client_id,
                    "client_secret": db_client.client_secret,
                    "redirect_url": db_client.redirect_url
                }],
                error={}  # No error in this case
            )
            return response

        except Exception as e:
            # If an error occurs, return a failed response with the error message
            return APIResponse(
                success=False,
                message="Client registration failed",
                data=[],
                error={"detail": str(e)}  # Include the error message
            )
        # db_client = create_oauth_client(db, client)
        # # print('ffff',db_client)
        # if db_client:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        # return {}

# @router.get("/clients/{client_id}", response_model=schemas.Client)
# def read_client(client_id: int, db: Session = Depends(get_db)):
#     db_client = crud.get_client(db, client_id=client_id)
#     if db_client is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
#     return db_client