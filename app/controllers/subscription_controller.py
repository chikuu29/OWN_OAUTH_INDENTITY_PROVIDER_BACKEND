from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from uuid import UUID
from datetime import datetime, timedelta, timezone

from app.models.subscriptions import Subscription, SubscriptionStatus, SubscriptionApp, SubscriptionFeature
from app.models.plans import Plan, PlanVersion
from app.models.transactions import Transaction
from app.models.apps import App
from app.models.features import Feature

class SubscriptionController:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subscription(self, tenant_id: int, plan_code: str, currency="INR", country="IN"):
        """
        Creates a new PENDING subscription (or active if free).
        Does NOT commit, just flushes. Caller should commit.
        """
        # 1. Fetch Plan Version
        plan_stmt = select(PlanVersion).join(Plan).filter(Plan.plan_code == plan_code).order_by(desc(PlanVersion.created_at))
        result = await self.db.execute(plan_stmt)
        plan_version = result.scalars().first()
        
        if not plan_version:
            raise ValueError(f"Plan not found: {plan_code}")

        start_date = datetime.now(timezone.utc).date()
        # Logic for duration? assuming monthly default for now or fetch from plan
        days = 30 if plan_version.billing_cycle == "monthly" else 365
        end_date = start_date + timedelta(days=days)

        new_sub = Subscription(
            tenant_id=tenant_id,
            plan_version_id=plan_version.id,
            plan_code=plan_code,
            status=SubscriptionStatus.active, # Default active? Or pending payment? Typically active upon creation in this flow?
                                              # Actually usually pending until payment. But here we might be creating it AFTER payment is verified?
                                              # In `complete_activation` it was created active. Let's default active for now, or caller sets status.
            start_date=start_date,
            end_date=end_date,
            auto_renew=True
        )
        self.db.add(new_sub)
        await self.db.flush()
        return new_sub

    async def add_app_to_subscription(self, subscription_id: UUID, app_id: UUID):
        """
        Adds an app to the subscription.
        """
        sub_app = SubscriptionApp(
            subscription_id=subscription_id,
            app_id=app_id,
            is_active=True,
            status="active"
        )
        self.db.add(sub_app)
        # return sub_app

    async def add_feature_to_subscription(self, subscription_id: UUID, feature_id: UUID):
        """
        Adds a feature to the subscription.
        """
        sub_feat = SubscriptionFeature(
            subscription_id=subscription_id,
            feature_id=feature_id,
            is_active=True,
            status="active"
        )
        self.db.add(sub_feat)

    async def activate_subscription(self, subscription_id: UUID, order_items: dict = None):
        """
        Activates a subscription, tenant, and links apps/features.
        """
        # 1. Fetch Subscription with Tenant
        stmt = select(Subscription).filter(Subscription.id == subscription_id)
        result = await self.db.execute(stmt)
        subscription = result.scalars().first()
        
        if not subscription:
            return None

        # 2. Activate Subscription
        subscription.status = SubscriptionStatus.active
        
        # 3. Activate Tenant
        # We need to fetch tenant model or relationship? 
        # Relationship is lazy loaded usually, but better to update efficiently.
        # Since we have tenant_id on subscription:
        from app.models.tenant import Tenant, TenantStatusEnum
        tenant_stmt = select(Tenant).filter(Tenant.id == subscription.tenant_id)
        t_result = await self.db.execute(tenant_stmt)
        tenant = t_result.scalars().first()
        if tenant:
             tenant.tenant_active = True
             tenant.status =  TenantStatusEnum.active

        # 4. Link Apps and Features from Order Items
        if order_items and "apps" in order_items:
            for app_data in order_items["apps"]:
                app_id_str = app_data.get("app_id")
                if app_id_str:
                    await self.add_app_to_subscription(subscription.id, UUID(app_id_str))
                
                # Link Features
                for feat_data in app_data.get("features", []):
                    feat_id_str = feat_data.get("feature_id")
                    if feat_id_str:
                        await self.add_feature_to_subscription(subscription.id, UUID(feat_id_str))

        await self.db.commit()
        return subscription

    async def upgrade_subscription(self, subscription_id: UUID, new_plan_code: str):
        """
        Upgrades subscription to a new plan.
        """
        # This is complex: proration, changing plan_version_id, etc.
        # For now, just basic Skeleton
        pass

    async def downgrade_subscription(self, subscription_id: UUID, new_plan_code: str):
        pass
