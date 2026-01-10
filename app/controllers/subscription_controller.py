from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from app.models.subscriptions import Subscription, SubscriptionStatus, SubscriptionApp, SubscriptionFeature, SubscriptionCycle
from app.models.plans import Plan, PlanVersion
from app.models.transactions import Transaction
from app.models.orders import Order
from app.models.apps import App
from app.models.features import Feature

logger = logging.getLogger(__name__)

class SubscriptionError(Exception):
    """Base exception for subscription-related errors."""
    pass

class PlanNotFoundError(SubscriptionError):
    """Raised when a specified plan code is not found."""
    pass
class SubscriptionController:
    def __init__(self, db: AsyncSession, tenant_id: int, tenant_uuid:Optional[str] = None,plan_code:str="FREE_TRIAL"):
        self.db = db
        self.tenant_id = tenant_id
        self.tenant_uuid = tenant_uuid
        self.plan_code = plan_code

    

    async def create_subscription(self, currency="INR", country="IN"):
        """
        Creates a new PENDING subscription (or active if free).
        Does NOT commit, just flushes. Caller should commit.
        """
        try:
            logger.info(f"Creating subscription for tenant {self.tenant_id} with plan {self.plan_code}")
            
            # 1. Fetch Plan Version
            plan_stmt = select(PlanVersion).join(Plan).filter(Plan.plan_code == self.plan_code).order_by(desc(PlanVersion.created_at))
            result = await self.db.execute(plan_stmt)
            plan_version = result.scalars().first()
            
            if not plan_version:
                logger.error(f"Plan not found: {self.plan_code}")
                raise PlanNotFoundError(f"Plan not found: {self.plan_code}")

            start_date = datetime.now(timezone.utc).date()
            # Logic for duration
            days = 30 if plan_version.billing_cycle == "monthly" else 365
            end_date = start_date + timedelta(days=days)

            new_sub = Subscription(
                tenant_id=self.tenant_id,
                status=SubscriptionStatus.active,
                auto_renew=True
            )
            self.db.add(new_sub)
            await self.db.flush()

            logger.info(f"Subscription {new_sub.id} created. Initializing cycle with plan version {plan_version.id}")
            
            # Create First Billing Cycle
            new_cycle = SubscriptionCycle(
                subscription_id=new_sub.id,
                plan_version_id=plan_version.id,
                plan_code=self.plan_code,
                start_date=start_date,
                end_date=end_date,
                status=SubscriptionStatus.active
            )
            self.db.add(new_cycle)
            await self.db.flush()
            
            logger.info(f"Successfully created subscription and initial cycle for tenant {self.tenant_id}")
            return new_sub
            
        except PlanNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error creating subscription for tenant {self.tenant_id}")
            raise SubscriptionError(f"Failed to create subscription: {str(e)}")

    async def create_subscription_from_order(self, order: Order, background_tasks = None):
        """
        Creates and activates a subscription based on a paid order.
        """
        try:
            if not self.plan_code:
                 raise SubscriptionError("Controller missing plan_code context")
                 
            # Create Subscription (Pending/Active)
            # Note: create_subscription does a flush.
            subscription = await self.create_subscription()
            
            # Activate and Link Items
            # This will also set tenant to active and link apps/features
            await self.activate_subscription(subscription.id, order_items=order.items, background_tasks=background_tasks)
            
            return subscription
        except SubscriptionError:
            # Re-raise known errors
            raise
        except Exception as e:
            logger.exception(f"Failed to process subscription from order {order.id}")
            raise SubscriptionError(f"Subscription processing from order failed: {str(e)}")

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

    async def activate_subscription(self, subscription_id: UUID, order_items: dict = None, background_tasks = None):
        """
        Activates a subscription, tenant, and links apps/features.
        Sends a confirmation email in the background.
        """
        try:
            logger.info(f"Activating subscription {subscription_id}")
            
            # 1. Fetch Subscription with Tenant
            stmt = select(Subscription).filter(Subscription.id == subscription_id)
            result = await self.db.execute(stmt)
            subscription = result.scalars().first()
            
            if not subscription:
                logger.warning(f"Activation failed: Subscription {subscription_id} not found")
                return None

            # 2. Activate Subscription
            subscription.status = SubscriptionStatus.active
            
            # 3. Activate Tenant
            from app.models.tenant import Tenant, TenantStatusEnum
            tenant_stmt = select(Tenant).filter(Tenant.id == subscription.tenant_id)
            t_result = await self.db.execute(tenant_stmt)
            tenant = t_result.scalars().first()
            
            root_username = None
            root_password = None
            
            if tenant:
                 logger.info(f"Activating tenant {tenant.id} for subscription {subscription_id}")
                 tenant.tenant_active = True
                 tenant.status = TenantStatusEnum.active
                 
                 # 3.1 Create Root User for Tenant
                 try:
                     from app.controllers.account_controller import AccountController
                     account_controller = AccountController(self.db)
                     root_user, root_password = await account_controller.create_root_user(
                         tenant_id=tenant.id,
                         tenant_email=tenant.tenant_email,
                         tenant_name=tenant.tenant_name
                     )
                     root_username = root_user.username
                     logger.info(f"Root user {root_username} created/verified for tenant {tenant.id}")
                 except Exception as e:
                     logger.error(f"Failed to create root user for tenant {tenant.id}: {e}")
                     # We don't necessarily want to fail the whole activation if root user fails 
                     # but we should log it prominently.

            # 4. Link Apps and Features from Order Items (Optimized - bulk insert)
            if order_items and "apps" in order_items:
                apps_to_add = []
                features_to_add = []
                
                for app_data in order_items["apps"]:
                    app_id_str = app_data.get("app_id")
                    if app_id_str:
                        # Collect app
                        apps_to_add.append(SubscriptionApp(
                            subscription_id=subscription.id,
                            app_id=UUID(app_id_str),
                            is_active=True,
                            status="active"
                        ))
                    
                    # Collect Features
                    for feat_data in app_data.get("features", []):
                        feat_id_str = feat_data.get("feature_id")
                        if feat_id_str:
                            features_to_add.append(SubscriptionFeature(
                                subscription_id=subscription.id,
                                feature_id=UUID(feat_id_str),
                                is_active=True,
                                status="active"
                            ))
                
                # Bulk add all apps and features
                if apps_to_add:
                    self.db.add_all(apps_to_add)
                    logger.info(f"Adding {len(apps_to_add)} apps to subscription {subscription_id}")
                if features_to_add:
                    self.db.add_all(features_to_add)
                    logger.info(f"Adding {len(features_to_add)} features to subscription {subscription_id}")

            await self.db.commit()
            await self.db.refresh(subscription) # Important to get cycles loaded

            # 5. Send Confirmation Email (Background)
            if tenant and subscription.current_cycle:
                 try:
                     from app.services.email_service import send_subscription_confirmation_email
                     
                     cycle = subscription.current_cycle
                     plan_name = cycle.plan_code or "Selected Plan"
                     start_date_str = cycle.start_date.strftime("%Y-%m-%d") if cycle.start_date else "N/A"
                     end_date_str = cycle.end_date.strftime("%Y-%m-%d") if cycle.end_date else "N/A"
                     
                     email_args = (
                         tenant.tenant_email,
                         tenant.tenant_name,
                         plan_name,
                         start_date_str,
                         end_date_str,
                         root_username,
                         root_password
                     )
                     
                     if background_tasks:
                         background_tasks.add_task(send_subscription_confirmation_email, *email_args)
                         logger.info(f"Email task added to BackgroundTasks for tenant {tenant.tenant_email}")
                     else:
                         # Fallback for non-FASTAPI contexts (though still async)
                         import asyncio
                         asyncio.create_task(send_subscription_confirmation_email(*email_args))
                         logger.info(f"Email task created via asyncio.create_task for tenant {tenant.tenant_email}")
                 except Exception as e:
                     logger.error(f"Failed to prepare/dispatch confirmation email for subscription {subscription_id}: {e}")

            logger.info(f"Subscription {subscription_id} fully activated")
            return subscription
            
        except Exception as e:
            logger.exception(f"Error activating subscription {subscription_id}")
            await self.db.rollback()
            raise SubscriptionError(f"Activation failed: {str(e)}")

    async def upgrade_subscription(self, subscription_id: UUID, new_plan_code: str):
        """
        Upgrades subscription to a new plan.
        """
        # This is complex: proration, changing plan_version_id, etc.
        # For now, just basic Skeleton
        pass

    async def downgrade_subscription(self, subscription_id: UUID, new_plan_code: str):
        pass
