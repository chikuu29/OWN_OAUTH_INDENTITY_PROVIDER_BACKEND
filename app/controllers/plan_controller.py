from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from uuid import UUID
from app.models.plans import Plan as PlanModel, PlanVersion as PlanVersionModel
from app.schemas.plan import PlanCreate
from sqlalchemy.orm import selectinload

async def create_plan(db: AsyncSession, plan_data: PlanCreate):
    # Check if plan_code already exists
    result = await db.execute(
        select(PlanModel).filter(PlanModel.plan_code == plan_data.plan_code)
    )
    existing = result.scalars().first()
    if existing:
        raise ValueError(f"Plan with code '{plan_data.plan_code}' already exists")

    # 1. Create the Logical Plan
    db_plan = PlanModel(
        plan_code=plan_data.plan_code,
        name=plan_data.plan_name,
        is_active=plan_data.is_active,
    )
    db.add(db_plan)
    await db.flush()  # Get db_plan.id

    # 2. Create the first Version (V1)
    db_version = PlanVersionModel(
        plan_id=db_plan.id,
        version=1,
        price=plan_data.price,
        currency=plan_data.currency,
        country=plan_data.country,
        billing_cycle=plan_data.billing_cycle,
        max_users=plan_data.max_users,
        max_branches=plan_data.max_branches,
        storage_limit_gb=plan_data.storage_limit_gb,
        is_current=True
    )
    db.add(db_version)
    
    await db.commit()
    await db.refresh(db_plan)

    # Reload with versions
    result = await db.execute(
        select(PlanModel)
        .options(selectinload(PlanModel.versions))
        .filter(PlanModel.id == db_plan.id)
    )
    return result.scalars().first()

async def update_plan(db: AsyncSession, plan_uuid: UUID, plan_data: PlanCreate):
    # Fetch existing plan
    result = await db.execute(
        select(PlanModel)
        .options(selectinload(PlanModel.versions))
        .filter(PlanModel.id == plan_uuid) # Assuming id is the UUID one or rename if needed
    )
    plan = result.scalars().first()
    if not plan:
        raise ValueError("Plan not found")

    # 1. Find the latest version number
    latest_version_num = max([v.version for v in plan.versions]) if plan.versions else 0
    
    # 2. Mark current versions as false (for this region/currency/cycle combination)
    # Actually, for simplicity, we just mark ALL current as false if we want a single global current,
    # but the unique constraint is on plan_id, version, currency, country.
    for v in plan.versions:
        if v.is_current and v.currency == plan_data.currency and v.country == plan_data.country and v.billing_cycle == plan_data.billing_cycle:
            v.is_current = False

    # 3. Create the new Version record
    new_version = PlanVersionModel(
        plan_id=plan.id,
        version=latest_version_num + 1,
        price=plan_data.price,
        currency=plan_data.currency,
        country=plan_data.country,
        billing_cycle=plan_data.billing_cycle,
        max_users=plan_data.max_users,
        max_branches=plan_data.max_branches,
        storage_limit_gb=plan_data.storage_limit_gb,
        is_current=True
    )
    db.add(new_version)
    
    await db.commit()
    await db.refresh(plan)
    return plan

async def get_plan(db: AsyncSession, plan_uuid: UUID):
    result = await db.execute(
        select(PlanModel)
        .options(selectinload(PlanModel.versions))
        .filter(PlanModel.id == plan_uuid)
    )
    return result.scalars().first()

async def list_plans(db: AsyncSession, page: int = 1, limit: int = 10):
    if page < 1: page = 1
    if limit < 1: limit = 10
    offset = (page - 1) * limit

    total = await db.scalar(select(func.count()).select_from(PlanModel))
    result = await db.execute(
        select(PlanModel)
        .options(selectinload(PlanModel.versions))
        .offset(offset).limit(limit)
    )
    plans = result.scalars().unique().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total // limit) + (1 if total % limit != 0 else 0),
        "plans": plans,
    }
