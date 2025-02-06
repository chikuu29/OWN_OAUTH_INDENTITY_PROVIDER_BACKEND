from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.tanent import TenantCreate 
# from app.crud.client import create_oauth_client
from app.controllers.account_controller import create_tenant
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ResponseHandler,APIResponse
from app.models.tenant import Tenant


from sqlalchemy.orm import class_mapper

def to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in class_mapper(obj.__class__).columns}

router = APIRouter(
    prefix="/account",  # Optional: Define a prefix for all client routes
    tags=["account"],   # Optional: Add a tag for better documentation grouping
)

@router.post("/register/tenant/",response_model=APIResponse)
async def register_tanets(client:TenantCreate, db: AsyncSession  = Depends(get_db)):
        print(f"==CALLING register_tanets====")
        print(f"Client",client)
        try:
            db_client= await create_tenant(db=db,client=client)
            # print('db_client',to_dict(db_client))
            return ResponseHandler.success(
                message="Tenant registered successfully",
                data=[db_client.to_dict()]
            )

        except Exception as e:
             # Handle any unexpected errors
            return ResponseHandler.error(
                message="Tenant registration failed",
                error_details={"detail": str(e)}
            )
        


@router.get("/tenant/{tenant_id}", response_model=APIResponse)
async def get_tenant(tenant_id: UUID,db: AsyncSession  = Depends(get_db)):
    result = await db.execute(select(Tenant).filter(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return ResponseHandler.success(
                message="Fetch Date",
                data=[tenant.to_dict()]
            ) # Convert ORM to Pydantic