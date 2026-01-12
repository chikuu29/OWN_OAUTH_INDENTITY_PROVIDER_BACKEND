from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from typing import Optional
import logging
import uuid

from app.models.subscriptions import Subscription, SubscriptionStatus, SubscriptionApp, SubscriptionFeature, SubscriptionCycle
from app.models.plans import Plan, PlanVersion
from app.models.transactions import Transaction
from app.models.orders import Order
from app.models.apps import App
from app.models.features import Feature

from app.core.logger import create_logger
from .base_controller import BaseController
from fastapi import BackgroundTasks

class SubscriptionError(Exception):
    """Base exception for subscription-related errors."""
    pass

class PlanNotFoundError(SubscriptionError):
    """Raised when a specified plan code is not found."""
    pass
class SubscriptionController(BaseController):
    def __init__(
        self, 
        db: AsyncSession, 
        tenant_id: int, 
        tenant_uuid: Optional[str] = None, 
        plan_code: str = "FREE_TRIAL", 
        background_tasks: Optional[BackgroundTasks] = None
    ):
        super().__init__(db, background_tasks=background_tasks, logger_name='subscriptions')
        self.tenant_id = tenant_id
        self.tenant_uuid = tenant_uuid
        self.plan_code = plan_code

    

    async def create_subscription(self, currency="INR", country="IN"):
        """
        Creates a new PENDING subscription (or active if free).
        Does NOT commit, just flushes. Caller should commit.
        """
        try:
            self.logger.info(f"Creating subscription for tenant {self.tenant_id} with plan {self.plan_code}")
            
            # 1. Fetch Plan Version
            plan_stmt = select(PlanVersion).join(Plan).filter(Plan.plan_code == self.plan_code).order_by(desc(PlanVersion.created_at))
            result = await self.db.execute(plan_stmt)
            plan_version = result.scalars().first()
            
            if not plan_version:
                self.logger.error(f"Plan not found: {self.plan_code}")
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

            self.logger.info(f"Subscription {new_sub.id} created. Initializing cycle with plan version {plan_version.id}")
            
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
            
            self.logger.info(f"Successfully created subscription and initial cycle for tenant {self.tenant_id}")
            return new_sub
            
        except PlanNotFoundError:
            raise
        except Exception as e:
            self.logger.exception(f"Unexpected error creating subscription for tenant {self.tenant_id}")
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
            await self.activate_subscription(subscription.id, order_items=order.items, background_tasks=background_tasks, order=order)
            
            return subscription
        except SubscriptionError:
            # Re-raise known errors
            raise
        except Exception as e:
            self.logger.exception(f"Failed to process subscription from order {order.id}")
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

    async def activate_subscription(self, subscription_id: UUID, order_items: dict = None, background_tasks = None, order: Order = None):
        """
        Activates a subscription, tenant, and links apps/features.
        Sends a confirmation email with PDF invoice in the background.
        """
        try:
            self.logger.info(f"Activating subscription {subscription_id}")
            
            # 1. Fetch Subscription with Tenant and Cycles (Eager Loading to avoid MissingGreenlet)
            from sqlalchemy.orm import selectinload
            stmt = select(Subscription).options(selectinload(Subscription.cycles)).filter(Subscription.id == subscription_id)
            result = await self.db.execute(stmt)
            subscription = result.scalars().first()
            
            if not subscription:
                self.logger.warning(f"Activation failed: Subscription {subscription_id} not found")
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
                 self.logger.info(f"Activating tenant {tenant.id} for subscription {subscription_id}")
                 tenant.tenant_active = True
                 tenant.status = TenantStatusEnum.active
                 
                 # 3.1 Create Root User for Tenant
                 try:
                     from app.controllers.account_controller import AccountController
                     account_controller = AccountController(db=self.db)
                     root_user, root_password = await account_controller.create_root_user(
                         tenant_id=tenant.id,
                         tenant_email=tenant.tenant_email,
                         tenant_name=tenant.tenant_name
                     )
                     root_username = root_user.username
                     self.logger.info(f"Root user {root_username} created/verified for tenant {tenant.id}")
                 except Exception as e:
                     self.logger.error(f"Failed to create root user for tenant {tenant.id}: {e}")

            # 4. Link Apps and Features from Order Items (Optimized - bulk insert)
            if order_items and "apps" in order_items:
                apps_to_add = []
                features_to_add = []
                
                for app_data in order_items["apps"]:
                    app_id_str = app_data.get("app_id")
                    if app_id_str:
                        apps_to_add.append(SubscriptionApp(
                            subscription_id=subscription.id,
                            app_id=UUID(app_id_str),
                            is_active=True,
                            status="active"
                        ))
                    
                    for feat_data in app_data.get("features", []):
                        feat_id_str = feat_data.get("feature_id")
                        if feat_id_str:
                            features_to_add.append(SubscriptionFeature(
                                subscription_id=subscription.id,
                                feature_id=UUID(feat_id_str),
                                is_active=True,
                                status="active"
                            ))
                
                if apps_to_add:
                    self.db.add_all(apps_to_add)
                if features_to_add:
                    self.db.add_all(features_to_add)

            # 4.5 Create Billing Record (The Invoice)
            billing_record = None
            invoice_summary = None
            if order:
                from app.models.subscriptions import SubscriptionBilling, PaymentStatus
                billing_record = SubscriptionBilling(
                    subscription_id=subscription.id,
                    base_amount=order.total_amount - order.tax_amount + order.discount_amount,
                    discount_amount=order.discount_amount,
                    tax_amount=order.tax_amount,
                    total_amount=order.total_amount,
                    currency=order.currency or "INR",
                    payment_status=PaymentStatus.paid,
                    payment_reference=order.provider_order_id,
                    billing_date=date.today()
                )
                self.db.add(billing_record)
                await self.db.flush() # Populate ID and other defaults
                
                # Capture itemized billing for invoice/email
                line_items = []
                if order.items:
                    # 1. Base Plan
                    line_items.append({
                        "name": f"Plan: {order.items.get('plan_code', 'Standard')}",
                        "price": float(order.items.get('plan_price', 0.0))
                    })
                    
                    # 1b. Included Plan Features (Eagerly load from PlanVersion)
                    try:
                        from app.models.plans import PlanVersion
                        plan_stmt = select(PlanVersion).options(selectinload(PlanVersion.features)).filter(PlanVersion.id == subscription.cycles[0].plan_version_id)
                        plan_res = await self.db.execute(plan_stmt)
                        plan_ver = plan_res.scalars().first()
                        if plan_ver and plan_ver.features:
                            for feat in plan_ver.features:
                                line_items.append({
                                    "name": f"  - Included: {feat.name}",
                                    "price": 0.0
                                })
                    except Exception as e:
                        self.logger.warning(f"Could not load plan features for invoice: {e}")

                    # 2. Apps and their features
                    for app_item in order.items.get('apps', []):
                        line_items.append({
                            "name": f"App: {app_item.get('name', 'Unknown App')}",
                            "price": float(app_item.get('base_price', 0.0))
                        })
                        for feat_item in app_item.get('features', []):
                            price = float(feat_item.get('price', 0.0))
                            label = "Addon" if price > 0 else "Included"
                            line_items.append({
                                "name": f"  - {label}: {feat_item.get('code', 'Feature')}",
                                "price": price
                            })

                # Capture for invoice BEFORE commit expires it
                invoice_summary = {
                    'id': str(billing_record.id),
                    'date': billing_record.billing_date.strftime("%Y-%m-%d"),
                    'amount': float(billing_record.base_amount),
                    'tax': float(billing_record.tax_amount),
                    'discount': float(billing_record.discount_amount),
                    'total': float(billing_record.total_amount),
                    'currency': str(billing_record.currency.value if hasattr(billing_record.currency, 'value') else billing_record.currency),
                    'items': line_items # NEW
                }

            # Capture essential info before commit (which expires the objects)
            target_email = tenant.tenant_email if tenant else None
            target_name = tenant.tenant_name if tenant else None

            await self.db.commit()
            
            # 5. Generate and Send Confirmation Email (Background)
            if target_email and subscription:
                 try:
                     from app.services.email_service import send_subscription_confirmation_email
                     from app.services.invoice_service import generate_invoice_pdf
                     
                     # Re-fetch cycles specifically to ensure they are loaded for this session
                     # We already did this above for features, but let's be sure for the background task
                     stmt = select(Subscription).options(selectinload(Subscription.cycles)).filter(Subscription.id == subscription_id)
                     sub_result = await self.db.execute(stmt)
                     sub_with_cycles = sub_result.scalars().first()

                     attachments = []
                     plan_name = "Selected Plan"
                     start_date_str = "N/A"
                     end_date_str = "N/A"

                     if sub_with_cycles and sub_with_cycles.current_cycle:
                         cycle = sub_with_cycles.current_cycle
                         plan_name = cycle.plan_code or "Selected Plan"
                         start_date_str = cycle.start_date.strftime("%Y-%m-%d") if cycle.start_date else "N/A"
                         end_date_str = cycle.end_date.strftime("%Y-%m-%d") if cycle.end_date else "N/A"

                     if invoice_summary:
                         invoice_data = {
                             'invoice_number': invoice_summary['id'][:8].upper(),
                             'date': invoice_summary['date'],
                             'amount': invoice_summary['amount'],
                             'tax': invoice_summary['tax'],
                             'discount': invoice_summary['discount'],
                             'total': invoice_summary['total'],
                             'currency': invoice_summary['currency'],
                             'plan_name': plan_name,
                             'line_items': invoice_summary.get('items', []) # RENAMED
                         }
                         tenant_info = {
                             'name': target_name,
                             'email': target_email,
                             'address': "" # Future: Add from tenant profile
                         }
                         pdf_content = generate_invoice_pdf(invoice_data, tenant_info)
                         attachments.append({
                             "filename": f"Invoice_{invoice_data['invoice_number']}.pdf",
                             "content": pdf_content,
                             "content_type": "application/pdf"
                         })

                     payment_info = {
                         "order_id": order.provider_order_id if order else "N/A",
                         "amount": str(order.total_amount) if order else "0.00",
                         "currency": str(order.currency) if order else "INR",
                         "line_items": invoice_summary.get('items', []) if invoice_summary else [] # RENAMED
                     }

                     email_args = (
                         target_email,
                         target_name,
                         plan_name,
                         start_date_str,
                         end_date_str,
                         root_username,
                         root_password,
                         attachments,
                         payment_info
                     )
                     # 6. Mark Tenant Activation Link as Used (NEW)
                     try:
                         from app.controllers.tenant_link_controller import mark_link_used
                         from app.models.tenant_link import TenantLink
                         link_stmt = select(TenantLink).filter(
                             TenantLink.tenant_id == tenant.tenant_uuid,
                             TenantLink.request_type == "activation",
                             TenantLink.is_used == False
                         )
                         link_res = await self.db.execute(link_stmt)
                         link_obj = link_res.scalars().first()
                         if link_obj:
                             await mark_link_used(self.db, link_obj)
                             self.logger.info(f"Activation link for tenant {tenant.id} marked as used.")
                     except Exception as link_err:
                         self.logger.warning(f"Failed to mark activation link as used: {link_err}")

                     if background_tasks:
                         background_tasks.add_task(send_subscription_confirmation_email, *email_args)
                     else:
                         import asyncio
                         asyncio.create_task(send_subscription_confirmation_email(*email_args))
                 except Exception as e:
                     self.logger.error(f"Failed to prepare/dispatch confirmation email: {e}")

            self.logger.info(f"Subscription {subscription_id} fully activated")
            return subscription
            
        except Exception as e:
            self.logger.exception(f"Error activating subscription {subscription_id}")
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
