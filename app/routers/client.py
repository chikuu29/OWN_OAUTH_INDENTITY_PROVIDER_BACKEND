from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.client import OAuthClient
from app.schemas.client import OAuthClientCreate

# from app.con.client import create_oauth_client
from app.controllers.application_controller import create_oauth_client
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ResponseHandler, APIResponse

router = APIRouter(
    prefix="/applications",  # Optional: Define a prefix for all client routes
    tags=["applications"],  # Optional: Add a tag for better documentation grouping
)


@router.post("/register")
async def register_oauth_client(
    inputData: OAuthClientCreate, db: AsyncSession = Depends(get_db)
):
    print(f"==CALLING register_oauth_client====")
    print(f"Client", inputData)
    try:
        db_client = await create_oauth_client(db=db, client_data=inputData)
        print("db_client", db_client)

        return ResponseHandler.success(
            message="Client registered successfully",
            data=[{"client_id": db_client.client_id}],
        )

    except Exception as e:
        # Handle any unexpected errors
        # print(type(e))
        # print(e)
        # error_dict = {"error": "Validation Error", "message": str(e)}
        return ResponseHandler.error(
            message="Client registration Unsuccessfull", error_details=e.args[0]
        )


@router.get("/clients")
async def get_oauth_clients(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),  # Default page = 1 (>=1)
    limit: int = Query(10, le=100),  # Max limit = 100
):
    # Calculate offset for pagination
    offset = (page - 1) * limit

    # Fetch total records for pagination meta
    total = await db.scalar(select(func.count()).select_from(OAuthClient))

    # Fetch paginated results
    result = await db.execute(select(OAuthClient).offset(offset).limit(limit))
    clients = result.scalars().all()

    if not clients:
        raise HTTPException(status_code=404, detail="No OAuth clients found")

    return {
        "message": "Clients fetched successfully",
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total // limit) + (1 if total % limit != 0 else 0),  # Total pages
        "data": [client.to_dict() for client in clients],
        "success":True
    }
