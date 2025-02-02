from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.client import OAuthClientCreate 
from app.crud.client import create_oauth_client
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ResponseHandler,APIResponse
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
            
            return ResponseHandler.success(
                message="Client registered successfully",
                data=[{
                "client_id": db_client.client_id,
                "client_secret": db_client.client_secret,
                "redirect_url": db_client.redirect_url
                }]
            )

        except Exception as e:
             # Handle any unexpected errors
            return ResponseHandler.error(
                message="Client registration failed",
                error_details={"detail": str(e)}
            )
        