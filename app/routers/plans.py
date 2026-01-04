from fastapi import APIRouter, Depends, Query, HTTPException
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.plan import PlanCreate, PlanOut
from app.controllers.plan_controller import create_plan, get_plan, list_plans, update_plan
from app.core.response import ResponseHandler, APIResponse

router = APIRouter(
    prefix="/plans",
    tags=["plans"],
)

@router.post("/", response_model=APIResponse)
async def create_plan_endpoint(inputData: PlanCreate, db: AsyncSession = Depends(get_db)):
    try:
        db_plan = await create_plan(db, inputData)
        return ResponseHandler.success(
            message="Plan created successfully", 
            data=[PlanOut.from_orm(db_plan).dict()]
        )
    except ValueError as e:
        return ResponseHandler.error(message="Plan creation failed", error_details={"detail": str(e)})
    except Exception as e:
        return ResponseHandler.error(message="Plan creation failed", error_details={"detail": str(e)})

@router.get("/", response_model=APIResponse)
async def list_plans_endpoint(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    try:
        result = await list_plans(db=db, page=page, limit=limit)
        plans_data = [PlanOut.from_orm(p).dict() for p in result["plans"]]
        return ResponseHandler.success(message="Plans fetched successfully", data=plans_data)
    except Exception as e:
        return ResponseHandler.error(message="Failed to fetch plans", error_details={"detail": str(e)})

@router.get("/{plan_uuid}", response_model=APIResponse)
async def get_plan_endpoint(plan_uuid: UUID, db: AsyncSession = Depends(get_db)):
    try:
        p = await get_plan(db=db, plan_uuid=plan_uuid)
        if not p:
            return ResponseHandler.not_found(message="Plan not found")
        return ResponseHandler.success(
            message="Plan fetched successfully", 
            data=[PlanOut.from_orm(p).dict()]
        )
    except Exception as e:
        return ResponseHandler.error(message="Failed to fetch plan", error_details={"detail": str(e)})

@router.put("/{plan_uuid}", response_model=APIResponse)
async def update_plan_endpoint(plan_uuid: UUID, inputData: PlanCreate, db: AsyncSession = Depends(get_db)):
    try:
        db_plan = await update_plan(db, plan_uuid, inputData)
        return ResponseHandler.success(
            message="Plan updated successfully (New Version Created)", 
            data=[PlanOut.from_orm(db_plan).dict()]
        )
    except ValueError as e:
        return ResponseHandler.error(message="Plan update failed", error_details={"detail": str(e)})
    except Exception as e:
        return ResponseHandler.error(message="Plan update failed", error_details={"detail": str(e)})
