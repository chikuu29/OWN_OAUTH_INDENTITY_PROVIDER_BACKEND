from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from uuid import UUID
from app.models.plan import Plan as PlanModel
from app.schemas.plan import PlanCreate


async def create_plan(db: AsyncSession, plan_data: PlanCreate):
    # Enforce unique constraint: plan_code + billing_cycle + currency + country
    result = await db.execute(
        select(PlanModel).filter(
            PlanModel.plan_code == plan_data.plan_code,
            PlanModel.billing_cycle == plan_data.billing_cycle,
            PlanModel.currency == plan_data.currency,
            PlanModel.country == plan_data.country,
        )
    )
    existing = result.scalars().first()
    if existing:
        raise ValueError("Plan with same code/billing/currency/country already exists")

    db_plan = PlanModel(
        plan_code=plan_data.plan_code,
        plan_name=plan_data.plan_name,
        price=plan_data.price,
        currency=plan_data.currency,
        country=plan_data.country,
        billing_cycle=plan_data.billing_cycle,
        max_users=plan_data.max_users,
        max_branches=plan_data.max_branches,
        storage_limit_gb=plan_data.storage_limit_gb,
        is_active=plan_data.is_active,
    )

    db.add(db_plan)
    await db.commit()
    await db.refresh(db_plan)

    return db_plan


async def get_plan(db: AsyncSession, plan_uuid: UUID):
    result = await db.execute(select(PlanModel).filter(PlanModel.uuid == plan_uuid))
    return result.scalars().first()


async def list_plans(db: AsyncSession, page: int = 1, limit: int = 10):
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    offset = (page - 1) * limit

    total = await db.scalar(select(func.count()).select_from(PlanModel))
    result = await db.execute(select(PlanModel).offset(offset).limit(limit))
    plans = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total // limit) + (1 if total % limit != 0 else 0),
        "plans": plans,
    }
