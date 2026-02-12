from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from uuid import UUID
from typing import Optional
from .base_controller import BaseController
from fastapi import BackgroundTasks

from app.schemas.tanent import TenantCreate
from app.schemas.auth_schemas import UserRegisterSchema
from app.models.tenant import Tenant, Role, Permission
from app.models.auth import User, UserProfile
from app.models.transactions import Transaction, TransactionStatus
from app.models.subscriptions import Subscription, SubscriptionStatus, SubscriptionCycle, SubscriptionApp, SubscriptionFeature
from app.models.plans import Plan, PlanVersion
from app.models.apps import App


pwd_context = CryptContext(schemes=["bcrypt"])


class AccountController(BaseController):
    def __init__(self, db: AsyncSession, tenant_uuid: Optional[UUID] = None, background_tasks: Optional[BackgroundTasks] = None):
        super().__init__(db, background_tasks=background_tasks, logger_name='accounts')
        self.tenant_uuid = tenant_uuid
        self.tenant_id: Optional[int] = None

    async def _ensure_tenant_loaded(self):
        """Ensure tenant_id (int) is loaded from tenant_uuid"""
        if self.tenant_id:
            return

        if not self.tenant_uuid:
            raise ValueError("Tenant UUID not set in controller")

        stmt = select(Tenant).filter(Tenant.tenant_uuid == self.tenant_uuid)
        result = await self.db.execute(stmt)
        tenant = result.scalars().first()
        
        if not tenant:
            raise ValueError("Tenant not found")
        
        self.tenant_id = tenant.id

    async def create_tenant(self, client: TenantCreate):
        """Create a new tenant"""
        result = await self.db.execute(
            select(Tenant).filter(
                or_(
                    Tenant.tenant_name == str(client.tenant_name).lower(),
                    Tenant.tenant_email == client.tenant_email,
                )
            )
        )
        existing_in_db = result.scalars().first()

        if existing_in_db:
            raise ValueError("Tenant with this name or email already exists")

        db_client = Tenant(
            tenant_name=str(client.tenant_name).lower(),
            tenant_email=client.tenant_email
        )

        self.db.add(db_client)
        await self.db.commit()
        await self.db.refresh(db_client)

        return db_client

    async def register_user(self, user_data: UserRegisterSchema, is_active: bool = True, is_root_user: bool = False, is_superuser: bool = False):
        """Register a new user"""
        result = await self.db.execute(
            select(User).filter(
                (User.username == user_data.username) | (User.email == user_data.email)
            )
        )
        existing_user = result.scalars().first()

        if existing_user:
            raise ValueError(
                {
                    "value": {
                        "username": {"msg": "Username may be already exists"},
                        "email": {"msg": "Email may be already exists"},
                    }
                }
            )

        tenant_result = await self.db.execute(
            select(Tenant).filter(Tenant.tenant_name == user_data.tenant_name)
        )
        tenant = tenant_result.scalars().first()
        if not tenant:
            raise ValueError(
                {"value": {"tenant_name": {"msg": "Invalid tenant name or May not found"}}}
            )

        new_user = User(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            username=user_data.username,
            email=user_data.email,
            phone_number=user_data.phone_number,
            hashed_password=pwd_context.hash(user_data.password),
            tenant_id=tenant.id,
            is_active=is_active,
            is_root_user=is_root_user,
            is_superuser=is_superuser,
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        if user_data.profile:
            user_profile = UserProfile(
                user_id=new_user.id,
                bio=user_data.profile.bio,
                profile_picture=user_data.profile.profile_picture,
                address=user_data.profile.address,
                city=user_data.profile.city,
                country=user_data.profile.country,
            )
            self.db.add(user_profile)
            await self.db.commit()

        return new_user

    async def create_root_user(self, tenant_id: int, tenant_email: str, tenant_name: str):
        """
        Create a root/admin user for a tenant upon subscription activation.
        Uses tenant email as username and generates a default password.
        """
        # Check if root user already exists
        result = await self.db.execute(
            select(User).filter(
                (User.tenant_id == tenant_id) & (User.email == tenant_email)
            )
        )
        existing_user = result.scalars().first()

        if existing_user:
            # Root user already exists, skip creation
            return existing_user, None

        # Generate a default password (tenant should change this later)
        default_password = f"Welcome@{tenant_name[:8]}123"

        # Build registration schema to reuse validation and profile handling
        root_user_data = UserRegisterSchema(
            first_name="Admin",
            last_name="User",
            username=tenant_email,
            email=tenant_email,
            password=default_password,
            tenant_name=tenant_name,
            profile=None,
        )

        # Use the existing register_user method to create the root user
        root_user = await self.register_user(
            root_user_data, 
            is_active=True, 
            is_root_user=True, 
            is_superuser=False
        )
        return root_user, default_password



    async def check_onboarding_status(self, request_id: int):
        """
        Check the status of a payment transaction and its associated subscription.
        Returns detailed history and status for frontend polling.
        """
        # Ensure we have the tenant loaded
        await self._ensure_tenant_loaded()

        # Determine a query to fetch related transactions for counting/history
        transactions_query = None
        transaction = None
        link = None
        
        from app.models.tenant_link import TenantLink

        # 1. Validate Request ID belongs to this tenant
        if request_id:
             # Find Link by ID
             stmt = select(TenantLink).filter(TenantLink.id == request_id)
             result = await self.db.execute(stmt)
             link = result.scalars().first()
             if not link:
                 raise ValueError({"detail": "Invalid request ID"})
             
             # Check if link belongs to the current tenant (the one initialized in controller)
             if str(link.tenant_id) != str(self.tenant_uuid):
                 raise ValueError({"detail": "Request ID does not belong to this tenant"})
        else:
             raise ValueError({"detail": "Request ID is required"})

        # 2. Fetch ALL transactions for this tenant
        # User requirement: history of all attempts and success check across all.
        transactions_query = select(Transaction).filter(Transaction.tenant_id == self.tenant_id).order_by(Transaction.created_at.desc())

        # Execute the query to get the related transactions list
        result = await self.db.execute(transactions_query)
        transactions = result.scalars().all()

        # Build history and count
        history = []
        success_count = 0
        for txn in transactions:
            history.append({
                "id": str(txn.id),
                "amount": float(txn.amount),
                "status": txn.status.value if hasattr(txn.status, 'value') else str(txn.status),
                "date": txn.created_at.strftime("%b %d, %Y %H:%M") if txn.created_at else "N/A",
                "method": txn.payment_method or "N/A",
                "provider_order_id": txn.provider_order_id
            })
            if txn.status == TransactionStatus.SUCCESS:
                success_count += 1

        transaction_count = len(transactions)
        payment_completed = success_count > 0

        
        # Prioritize finding a SUCCESS transaction to return as the current status
        # If multiple exist, the first one in the list (most recent) is fine.
        # If none exist, fallback to the most recent attempt.
        success_transaction = next((t for t in transactions if t.status == TransactionStatus.SUCCESS), None)
        
        transaction = success_transaction if success_transaction else (transactions[0] if transactions else None)
        
        if not transaction:
             # No transactions yet?
             return {
                "valid": True,
                "status": "PENDING", # Default
                "subscription_status": "inactive",
                "razorpay_order_id": None,
                "transaction_id": None,
                "amount": 0,
                "currency": "INR",
                "message": "No transactions found",
                "transaction_count": 0,
                "payment_completed": False,
                "history": [],
                "retry_allowed": True
            }

        # Check Subscription status if payment completed (look for THE subscription)
        subscription_status = "inactive"
        if payment_completed:
            # Find the active subscription
            from sqlalchemy import desc
            # Ensure we use self.tenant_id here too!
            sub_stmt = select(Subscription).filter(
                Subscription.tenant_id == self.tenant_id
            ).order_by(desc(Subscription.created_at))
            sub_result = await self.db.execute(sub_stmt)
            subscription = sub_result.scalars().first()
            if subscription:
                subscription_status = subscription.status.value if hasattr(subscription.status, 'value') else str(subscription.status)

        status_map = {
            TransactionStatus.SUCCESS: "SUCCESS",
            TransactionStatus.PENDING: "PENDING",
            TransactionStatus.FAILED: "FAILED"
        }
        status_str = status_map.get(transaction.status, "PENDING")

        refund_eligible = False
        message = f"Transaction is current {status_str}"
        
        if success_count > 1:
             refund_eligible = True
             message = f"Transaction is {status_str}. Note: Multiple successful payments detected; duplicate charges may be eligible for refund."

        return {
            "valid": True,
            "status": status_str,
            "subscription_status": subscription_status,
            "razorpay_order_id": transaction.provider_order_id,
            "transaction_id": str(transaction.id),
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "message": message,
            "transaction_count": transaction_count,
            "payment_completed": payment_completed,
            "history": history,
            "retry_allowed": not payment_completed,
            "refund_eligible": refund_eligible
        }


    async def build_account_authorization_context(self):
        """
        Build an authorization context for the account.
        Returns subscription info and permissions.
        """
        await self._ensure_tenant_loaded()

        # 1. Fetch active subscription
        from sqlalchemy import desc
        from sqlalchemy.orm import selectinload
        
        sub_stmt = select(Subscription).filter(
            Subscription.tenant_id == self.tenant_id,
            Subscription.status == SubscriptionStatus.active
        ).order_by(desc(Subscription.created_at)).options(
            selectinload(Subscription.cycles).selectinload(SubscriptionCycle.plan_version).selectinload(PlanVersion.plan),
            selectinload(Subscription.cycles).selectinload(SubscriptionCycle.plan_version).selectinload(PlanVersion.features),
            selectinload(Subscription.subscribed_apps).selectinload(SubscriptionApp.app).selectinload(App.features),
            selectinload(Subscription.subscribed_features).selectinload(SubscriptionFeature.feature)
        )
        
        sub_result = await self.db.execute(sub_stmt)
        subscription = sub_result.scalars().first()

        context = {
            "subscription": {
                "plan": None,
                "status": "inactive",
                "features": []
            },
            "roles": [],
            "permissions": []
        }

        if subscription:
            context["subscription"]["status"] = subscription.status.value
            if subscription.current_cycle and subscription.current_cycle.plan_version:
                context["subscription"]["plan"] = subscription.current_cycle.plan_version.plan.plan_code
            
            # Use the existing property to get all features
            features = subscription.all_active_features
            context["subscription"]["features"] = [f.code for f in features]

        # 2. Fetch Roles and Permissions for the tenant
        stmt = select(Role).filter(Role.tenant_id == self.tenant_id).options(
            selectinload(Role.permissions)
        )
        roles_result = await self.db.execute(stmt)
        roles = roles_result.scalars().all()
        
        for role in roles:
            if role.is_active:
                context["roles"].append(role.role_name)
                for perm in role.permissions:
                    context["permissions"].append(perm.permission_name)
        
        # Deduplicate roles and permissions
        context["roles"] = list(set(context["roles"]))
        context["permissions"] = list(set(context["permissions"]))

        return context