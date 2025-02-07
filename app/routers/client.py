from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.client import OAuthClientCreate 
# from app.con.client import create_oauth_client
from app.controllers.application_controller import create_oauth_client
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ResponseHandler,APIResponse
router = APIRouter(
    prefix="/applications",  # Optional: Define a prefix for all client routes
    tags=["applications"],   # Optional: Add a tag for better documentation grouping
)

@router.post("/register",response_model=APIResponse)
async def register_oauth_client(inputData:OAuthClientCreate, db: AsyncSession  = Depends(get_db)):
        print(f"==CALLING register_oauth_client====")
        print(f"Client",inputData)
        try:
            db_client= await create_oauth_client(db=db,client_data=inputData)
            print('db_client',db_client)
            
            return ResponseHandler.success(
                message="Client registered successfully",
                data=[{
                "client_id": db_client.client_id
                }]
            )

        except Exception as e:
             # Handle any unexpected errors
            # print(type(e))
            # print(e)
            # error_dict = {"error": "Validation Error", "message": str(e)}
            return ResponseHandler.error(
                message="Client registration Unsuccessfull",
                error_details=e.args[0]
            )
        