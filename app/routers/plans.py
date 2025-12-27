from fastapi import APIRouter, Depends, Query
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.plan import PlanCreate
from app.controllers.plan_controller import create_plan, get_plan, list_plans
from app.core.response import ResponseHandler, APIResponse

router = APIRouter(
    prefix="/plans",
    tags=["plans"],
)


@router.post("/", response_model=APIResponse)
async def create_plan_endpoint(inputData: PlanCreate, db: AsyncSession = Depends(get_db)):
    try:
        db_plan = await create_plan(db, inputData)

        plan_dict = {
            "uuid": str(db_plan.uuid),
            "id": db_plan.id,
            "plan_code": db_plan.plan_code,
            "plan_name": db_plan.plan_name,
            "price": db_plan.price,
            "currency": getattr(db_plan.currency, "value", str(db_plan.currency)),
            "country": getattr(db_plan.country, "value", str(db_plan.country)),
            "billing_cycle": getattr(db_plan.billing_cycle, "value", str(db_plan.billing_cycle)),
            "max_users": db_plan.max_users,
            "max_branches": db_plan.max_branches,
            "storage_limit_gb": db_plan.storage_limit_gb,
            "is_active": db_plan.is_active,
            "created_at": db_plan.created_at.isoformat() if db_plan.created_at else None,
        }

        return ResponseHandler.success(message="Plan created successfully", data=[plan_dict])

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

        plans_data = []
        for p in result["plans"]:
            plans_data.append(
                {
                    "uuid": str(p.uuid),
                    "id": p.id,
                    "plan_code": p.plan_code,
                    "plan_name": p.plan_name,
                    "price": p.price,
                    "currency": getattr(p.currency, "value", str(p.currency)),
                    "country": getattr(p.country, "value", str(p.country)),
                    "billing_cycle": getattr(p.billing_cycle, "value", str(p.billing_cycle)),
                    "max_users": p.max_users,
                    "max_branches": p.max_branches,
                    "storage_limit_gb": p.storage_limit_gb,
                    "is_active": p.is_active,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
            )

        # meta = {k: v for k, v in result.items() if k != "plans"}

        return ResponseHandler.success(message="Plans fetched successfully", data=plans_data)

    except Exception as e:
        return ResponseHandler.error(message="Failed to fetch plans", error_details={"detail": str(e)})


@router.get("/{plan_uuid}", response_model=APIResponse)
async def get_plan_endpoint(plan_uuid: UUID, db: AsyncSession = Depends(get_db)):
    try:
        p = await get_plan(db=db, plan_uuid=plan_uuid)
        if not p:
            return ResponseHandler.not_found(message="Plan not found", error_details={"plan_uuid": str(plan_uuid)})

        plan_dict = {
            "uuid": str(p.uuid),
            "id": p.id,
            "plan_code": p.plan_code,
            "plan_name": p.plan_name,
            "price": p.price,
            "currency": getattr(p.currency, "value", str(p.currency)),
            "country": getattr(p.country, "value", str(p.country)),
            "billing_cycle": getattr(p.billing_cycle, "value", str(p.billing_cycle)),
            "max_users": p.max_users,
            "max_branches": p.max_branches,
            "storage_limit_gb": p.storage_limit_gb,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }

        return ResponseHandler.success(message="Plan fetched successfully", data=[plan_dict])

    except Exception as e:
        return ResponseHandler.error(message="Failed to fetch plan", error_details={"detail": str(e)})
