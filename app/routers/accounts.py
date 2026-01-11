from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status,BackgroundTasks
from uuid import UUID
from sqlalchemy import func, desc, or_
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from app.db.database import get_db, AsyncSessionLocal
from app.models.auth import User
from app.schemas.tanent import TenantCreate

# from app.crud.client import create_oauth_client
from app.controllers.account_controller import AccountController
from app.controllers.tenant_link_controller import create_tenant_link, get_tenant_link, mark_link_used
from app.controllers.plan_controller import get_plan
from app.controllers.subscription_controller import SubscriptionController
from app.models.subscriptions import Subscription, SubscriptionStatus, SubscriptionBilling, PaymentStatus
from datetime import datetime, timedelta, timezone
import uuid
import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy.ext.asyncio import AsyncSession
import razorpay
import json

from app.core.response import ResponseHandler, APIResponse
from app.models.tenant import Role, Tenant, TenantProfile
from app.schemas.tanent import TenantCreate, TenantProfileCreate
from app.schemas.auth_schemas import UserRegisterSchema
from app.core.db_helpers import model_to_dict
from sqlalchemy.orm import selectinload
from app.services.email_service import send_tenant_registration_email
from app.schemas.tenant_link import TenantLinkOut
from app.schemas.tenant_link import ActivationComplete
from app.models.subscriptions import Subscription
from app.models.plans import Plan, PlanVersion
from app.models.apps import App
from app.models.features import Feature
from app.models.tenant import TenantStatusEnum
from app.models.transactions import Transaction, TransactionStatus
from app.models.orders import Order, OrderStatus
from app.models.apps import AppPricing # Added import
from app.models.plans import CurrencyEnum, CountryEnum # Added import
from app.schemas.payment import PaymentVerificationRequest, PaymentStatusResponse,PaymentStatusRequest
from app.core.logger import create_logger

# tenant link helpers imported above
logger = create_logger('accounts')

async def process_free_activation_task(tenant_id: int, order_id: UUID, transaction_id: UUID, plan_code: str):
    """
    Background task to process subscription activation for free plans.
    """
    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"[Background] Starting free activation for tenant {tenant_id}")
            
            # Fetch objects to ensure they exist and link properly in this session
            order_res = await db.execute(select(Order).filter(Order.id == order_id))
            order = order_res.scalars().first()
            
            txn_res = await db.execute(select(Transaction).filter(Transaction.id == transaction_id))
            transaction = txn_res.scalars().first()
            
            if not order or not transaction:
                logger.error(f"[Background] Activation failed: Order {order_id} or Transaction {transaction_id} not found")
                return

            sub_controller = SubscriptionController(db, tenant_id=tenant_id, plan_code=plan_code)
            # This handles activation, root user, billing, and background emails
            subscription = await sub_controller.create_subscription_from_order(order)
            
            transaction.subscription_id = subscription.id
            transaction.status = TransactionStatus.SUCCESS # Mark as success AFTER activation
            await db.commit()
            logger.info(f"[Background] Free activation successful for tenant {tenant_id}. Subscription {subscription.id}")
        except Exception as e:
            logger.error(f"[Background] Error in free activation for tenant {tenant_id}: {str(e)}")
            # For free plans, if background task fails, we might want to mark transaction as failed 
            # so the user can see it in history/confirmation
            try:
                 txn_res = await db.execute(select(Transaction).filter(Transaction.id == transaction_id))
                 txn = txn_res.scalars().first()
                 if txn:
                      txn.status = TransactionStatus.FAILED
                      await db.commit()
            except: pass
            await db.rollback()


router = APIRouter(
    prefix="/account",  # Optional: Define a prefix for all client routes
    tags=["account"],  # Optional: Add a tag for better documentation grouping
)


@router.post("/register/auth_user", response_model=APIResponse)
async def register_authuser(
    user: UserRegisterSchema, db: AsyncSession = Depends(get_db)
):
    print("====CALLING REGISTER AUTH USER===")
    try:
        account_controller = AccountController(db=db)
        user_data = await account_controller.register_user(user)

        user_data = model_to_dict(user_data, exclude_fields=["hashed_password"])

        return ResponseHandler.success(
            message="User registration successful", data=[user_data]
        )

    except Exception as e:
        # Handle any unexpected errors
        # print(type(e))
        # print(e)
        # error_dict = {"error": "Validation Error", "message": str(e)}
        return ResponseHandler.error(
            message="User registration failed", error_details=e.args[0]
        )


@router.get("/auth_users")
async def get_oauth_users(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),  # Default page = 1 (>=1)
    limit: int = Query(10, le=100),  # Max limit = 100
):
    # Calculate offset for pagination
    offset = (page - 1) * limit

    # Fetch total records for pagination meta
    total = await db.scalar(select(func.count()).select_from(User))

    # Fetch paginated results
    result = await db.execute(
        select(User).options(selectinload(User.tenant)).offset(offset).limit(limit)
    )
    users = result.scalars().all()

    if not users:
        raise HTTPException(status_code=404, detail="No auth user found")

    return {
        "message": "Auth Users fetched successfully",
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total // limit) + (1 if total % limit != 0 else 0),  # Total pages
        "data": [user.to_dict(include_tenat=False) for user in users],
        "success": True,
    }


@router.post("/register/tenant/", response_model=APIResponse)
async def register_tanets(client: TenantCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    print(f"==CALLING register_tanets====")
    print(f"Client", client)
    try:
        account_controller = AccountController(db=db)
        db_client = await account_controller.create_tenant(client)

        # Create activation link valid for 24 hours (returns DB link and raw token)
        link, raw_token = await create_tenant_link(
            db=db, 
            tenant_uuid=str(db_client.tenant_uuid), 
            hours_valid=24,
            extra_payload=db_client.to_dict()
        )

        # Build activation URL using DOMAIN_NAME env if available (send raw token)
        DOMAIN = os.getenv("DOMAIN_NAME", "http://localhost:5173/account")
        activation_url = f"{DOMAIN}/setup/{raw_token}"

        # Send activation email in background (will await coroutine when run)
        background_tasks.add_task(
            send_tenant_registration_email,
            db_client.tenant_email,
            db_client.tenant_name,
            activation_url,
        )

        return ResponseHandler.success(
            message="Tenant registered successfully", data=[db_client.to_dict()]
        )

    except Exception as e:
        # Handle any unexpected errors
        return ResponseHandler.error(
            message="Tenant registration failed", error_details={"detail": str(e)}
        )


@router.get("/tenants")
async def get_tenant(
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),  # Default page = 1 (>=1)
    limit: int = Query(10, le=100),
):  
    # Calculate offset for pagination
    offset = (page - 1) * limit

    if tenant_id:
        # Fetch specific tenant
        result = await db.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        tenant = result.scalars().first()

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        return {
            "message": "Tenant fetched successfully",
            "total": 1,
            "page": 1,
            "limit": 1,
            "pages": 1,
            "data": [tenant.to_dict()],
            "success": True,
        }

    # Fetch total records for pagination
    total = await db.scalar(select(func.count()).select_from(Tenant))

    # Fetch all tenants with pagination
    result = await db.execute(select(Tenant).offset(offset).limit(limit))
    tenants = result.unique().scalars().all()

    return {
        "message": "Tenants fetched successfully",
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total // limit) + (1 if total % limit != 0 else 0),  # Total pages calculation
        "data": [tenant.to_dict() for tenant in tenants],
        "success": True,
    }


@router.get("/tenants-with-roles")
async def get_tenants_with_roles(db: AsyncSession = Depends(get_db)):
    # Fetch all tenants and their roles
    result = await db.execute(select(Tenant).options(selectinload(Tenant.roles)))
    tenants = result.scalars().all()

    # Transform data to desired structure
    tenants_with_roles = [
        {
            "tenant_id": tenant.tenant_id,
            "name": tenant.tenant_name,
            "roles": [role.role_name for role in tenant.roles],
            "isActive": tenant.tenant_active,
            "created_at": tenant.created_at
        }
        for tenant in tenants
    ]

    return tenants_with_roles


@router.get("/validate/{token}", response_model=APIResponse)
async def validate_activation_link(token: str, db: AsyncSession = Depends(get_db)):
    try:
        link = await get_tenant_link(db, token)
        if not link:
            return ResponseHandler.not_found(message="Activation link not found")

        # if link.is_used:
        #     return ResponseHandler.error(message="Activation link already used", error_details={"token": token})
        if link.is_used:
            if link.expires_at and link.expires_at < datetime.now(timezone.utc):
                return ResponseHandler.error(message="Activation link expired", error_details={"token": token})

        # Decode the token to get the payload
        from app.controllers.tenant_link_controller import JWT_SECRET, JWT_ALGO
        import jwt
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        except Exception as e:
             return ResponseHandler.error(message="Invalid token structure", error_details={"detail": str(e)})

        data = [{
            "tenant_id": link.tenant_id,
            "request_type": link.request_type,
            "is_used": link.is_used,
            "created_at": link.created_at.isoformat() if link.created_at else None,
            "expires_at": link.expires_at.isoformat() if link.expires_at else None,
            **payload
        }]

        return ResponseHandler.success(message="Activation link valid", data=data)

    except Exception as e:
        return ResponseHandler.error(message="Failed to validate link", error_details={"detail": str(e)})


@router.post("/resend-activation/{token}", response_model=APIResponse)
async def resend_activation_link(token: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Resends the activation link for a tenant if the original link has expired or reached the user.
    Uses the old token to identify the tenant.
    """
    try:
        # 1. Find the link by the old token hash
        old_link = await get_tenant_link(db, token)
        if not old_link:
            return ResponseHandler.not_found(message="Original activation link not found")

        # 2. Get the tenant associated with this link (link.tenant_id is the tenant_uuid)
        result = await db.execute(select(Tenant).filter(Tenant.tenant_uuid == old_link.tenant_id))
        tenant = result.scalars().first()
        
        if not tenant:
            return ResponseHandler.not_found(message="Tenant not found for this link")

        if tenant.is_active:
             return ResponseHandler.error(message="Tenant is already active", error_details={"tenant_uuid": str(tenant.tenant_uuid)})

        # 3. Create a new activation link (valid for 24 hours)
        new_link, new_raw_token = await create_tenant_link(
            db=db, 
            tenant_uuid=str(tenant.tenant_uuid), 
            hours_valid=24,
            extra_payload=tenant.to_dict()
        )

        # 4. Build activation URL
        DOMAIN = os.getenv("DOMAIN_NAME", "http://localhost:5173/account")
        activation_url = f"{DOMAIN}/setup/{new_raw_token}"

        # 5. Send activation email in background
        background_tasks.add_task(
            send_tenant_registration_email,
            tenant.tenant_email,
            tenant.tenant_name,
            activation_url,
        )

        return ResponseHandler.success(
            message="New activation link sent successfully", 
            data=[{"tenant_email": tenant.tenant_email}]
        )

    except Exception as e:
        return ResponseHandler.error(
            message="Failed to resend activation link", 
            error_details={"detail": str(e)}
        )



@router.post("/tenant/profile", response_model=APIResponse)
async def upsert_tenant_profile(
    profile_data: TenantProfileCreate, 
    tenant_id: int = Query(...), 
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check if tenant exists
        result = await db.execute(select(Tenant).filter(Tenant.id == tenant_id))
        tenant = result.scalars().first()
        if not tenant:
            return ResponseHandler.not_found(message="Tenant not found")

        # Check if profile already exists
        result = await db.execute(select(TenantProfile).filter(TenantProfile.tenant_id == tenant_id))
        profile = result.scalars().first()

        if profile:
            # Update existing profile
            has_changed = False
            for key, value in profile_data.model_dump(exclude_unset=True).items():
                if getattr(profile, key) != value:
                    setattr(profile, key, value)
                    has_changed = True
            
            if not has_changed:
                return ResponseHandler.success(
                    message="No data changed", 
                    data=[profile.to_dict()]
                )
            
            message = "Tenant profile updated successfully"
        else:
            # Create new profile
            profile = TenantProfile(tenant_id=tenant_id, **profile_data.model_dump())
            db.add(profile)
            message = "Tenant profile created successfully"

        await db.commit()
        await db.refresh(profile)

        return ResponseHandler.success(
            message=message, 
            data=[profile.to_dict()]
        )
    except Exception as e:
        await db.rollback()
        return ResponseHandler.error(message="Failed to update tenant profile", error_details={"detail": str(e)})


@router.get("/tenant/profile", response_model=APIResponse)
async def get_tenant_profile(tenant_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(TenantProfile).filter(TenantProfile.tenant_id == tenant_id)
        )
        profile = result.scalars().first()
        if not profile:
            return ResponseHandler.not_found(message="Tenant profile not found")

        return ResponseHandler.success(
            message="Tenant profile fetched successfully", 
            data=[profile.to_dict()]
        )
    except Exception as e:
        return ResponseHandler.error(message="Failed to fetch tenant profile", error_details={"detail": str(e)})










@router.post("/verify-payment", response_model=APIResponse)
async def verify_payment(payload: PaymentVerificationRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Step 1: Verify price server-side based on plan + apps + features + coupon.
    Step 2: Create Order in DB.
    Step 3: Create Razorpay Order (if amount > 0) or mock order.
    Step 4: Create Transaction (PENDING if paid, SUCCESS if free).
    """
    print(f"========== STARTING PAYMENT VERIFICATION ==========")
    print(f"Payload: {payload.dict()}")
    try:
        # 1. Fetch Tenant
        print(f"Step 1: Fetching Tenant {payload.tenant_uuid}")
        stmt = select(Tenant).filter(Tenant.tenant_uuid == payload.tenant_uuid)
        result = await db.execute(stmt)
        tenant = result.scalars().first()
        if not tenant:
            print(f"Error: Tenant not found")
            return ResponseHandler.not_found(message="Tenant not found")

        # 2. Server-side Price Calculation
        print(f"Step 2: Calculating Prices")
        # Fetch Plan
        plan_stmt = select(PlanVersion).join(Plan).filter(Plan.plan_code == payload.plan_code).order_by(desc(PlanVersion.created_at))
        plan_result = await db.execute(plan_stmt)
        plan_version = plan_result.scalars().first()
        if not plan_version:
             # Fallback if plan_code is FREE_TRIAL or check strict
             if payload.plan_code == "FREE_TRIAL":
                 plan_price = 0
             else:
                 print(f"Error: Plan not found {payload.plan_code}")
                 return ResponseHandler.not_found(message=f"Plan not found: {payload.plan_code}")
        else:
             plan_price = float(plan_version.price)
        print(f"Plan Price: {plan_price}")

        # Fetch Apps
        apps_price = 0
        apps_details = []
        if payload.apps:
            # We need to join App with AppPricing to get the price
            # Assuming CurrencyEnum.INR and CountryEnum.IN for now as defaults, or logic could be expanded to infer from tenant/request
            target_currency = CurrencyEnum.INR
            target_country = CountryEnum.IN

            app_stmt = (
                select(App, AppPricing)
                .join(AppPricing, AppPricing.app_id == App.id)
                .filter(
                    App.id.in_(payload.apps),
                    AppPricing.currency == target_currency,
                    AppPricing.country == target_country
                )
            )
            app_result = await db.execute(app_stmt)
            db_apps_with_pricing = app_result.all() # returns list of (App, AppPricing) tuples
            # specific serialization for debugging
            debug_apps = []
            for app, pricing in db_apps_with_pricing:
                debug_apps.append({
                    "app_name": app.name,
                    "app_id": str(app.id),
                    "price": float(pricing.price),
                    "currency": pricing.currency,
                    "country": pricing.country
                })
            print(f"Apps with Pricing: {json.dumps(debug_apps, indent=4)}")
            print(f"Apps found: {len(db_apps_with_pricing)}")

            for app, pricing in db_apps_with_pricing:
                base_price = float(pricing.price)
                app_snapshot = {
                    "app_id": str(app.id),
                    "name": app.name,
                    "base_price": base_price,
                    "features": []
                }
                print(f"App: {app.name}, Base Price: {base_price} ,app_snapshot: {app_snapshot}")
                # Addon Features
                addon_price_sum = 0
                if app.id in payload.features:
                    selected_feature_codes = payload.features[app.id]
                    # Fetch ALL selected features (including base ones)
                    feat_stmt = select(Feature).filter(Feature.app_id == app.id, Feature.code.in_(selected_feature_codes))
                    feat_result = await db.execute(feat_stmt)
                    features = feat_result.scalars().all()
                    for f in features:
                        f_price = float(f.addon_price) if f.addon_price and not f.is_base_feature else 0.0
                        addon_price_sum += f_price
                        app_snapshot["features"].append({
                            "feature_id": str(f.id),
                            "code": f.code,
                            "price": f_price,
                            "is_base": f.is_base_feature
                        })

                app_total = base_price + addon_price_sum
                apps_price += app_total
                app_snapshot["total_price"] = app_total
                apps_details.append(app_snapshot)
        
        print(f"Apps Price: {apps_price}")

        subtotal = plan_price + apps_price
        
        # Apply Coupon
        discount_amount = 0
        if payload.coupon:
            print(f"Applying Coupon: {payload.coupon.code}")
            # Server-side validation of coupon could go here
            code = payload.coupon.code.upper()
            percentage = 0
            if code == "WELCOME100": percentage = 1.0
            elif code == "WELCOME10": percentage = 0.1
            elif code == "SAAS20": percentage = 0.2
            elif code == "LAUNCH50": percentage = 0.5
            elif code == payload.coupon.code: percentage = payload.coupon.percentage # fallback
            
            discount_amount = subtotal * percentage
        
        print(f"Discount: {discount_amount}")

        taxable_amount = subtotal - discount_amount
        tax_rate = 0.18
        tax = taxable_amount * tax_rate
        grand_total = taxable_amount + tax
        
        print(f"Calculated Grand Total: {grand_total}")
        print(f"Payload Grand Total: {payload.grand_total}")

        # Verify Grand Total (Tolerance of 1.0)
        if abs(grand_total - payload.grand_total) > 1.0:
             print(f"ERROR: Price mismatch")
             return ResponseHandler.error(
                 message="Price mismatch", 
                 error_details={
                    "detail": "Price mismatch between server and Client: {} Server: {} Diff: {}".format(payload.grand_total, grand_total, grand_total - payload.grand_total)  
                 }
            )

        # 3. Create Order in DB
        print(f"Step 3: Creating Order in DB")
        new_order = Order(
            tenant_id=tenant.id,
            total_amount=grand_total,
            tax_amount=tax,
            discount_amount=discount_amount,
            currency="INR",
            items={
                "plan_code": payload.plan_code,
                "plan_price": plan_price,
                "apps": apps_details,
                "coupon": payload.coupon.dict() if payload.coupon else None
            },
            status=OrderStatus.PENDING
        )
        db.add(new_order)
        await db.flush() # Flush to get ID
        print(f"Order Created with ID: {new_order.id}")

        # 4. Create Razorpay Order
        print(f"Step 4: Creating Razorpay Order")
        razorpay_key = os.getenv("RAZORPAY_KEY_ID")
        razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET")
        
        if not razorpay_key or not razorpay_secret:
             print("Error: Razorpay keys missing")
             return ResponseHandler.error(message="Payment gateway configuration missing",error_details={"detail": "Payment gateway configuration missing"})

        client = razorpay.Client(auth=(razorpay_key, razorpay_secret))
        
        amount_in_paise = int(grand_total * 100)
        order_id = None
        
        if amount_in_paise > 0:
            order_data = {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": f"rcpt_{tenant.id}_{int(datetime.now().timestamp())}",
                "notes": {
                    "tenant_uuid": str(tenant.tenant_uuid),
                    "plan_code": payload.plan_code,
                    "db_order_id": str(new_order.id)
                }
            }
            order = client.order.create(data=order_data)
            order_id = order['id']
            # Update order with provider id
            new_order.provider_order_id = order_id
        else:
            # Free transaction
            order_id = "order_free_" + uuid.uuid4().hex[:10]
            new_order.provider_order_id = order_id
        
        print(f"Razorpay Order ID: {order_id}")

        # 5. Create Transaction
        print(f"Step 5: Creating Transaction")
        is_free = (grand_total <= 0)
        
        transaction = Transaction(
            tenant_id=tenant.id,
            order_id=new_order.id, # Link to Order
            amount=grand_total,
            currency="INR",
            provider="razorpay",
            provider_order_id=order_id,
            status=TransactionStatus.PENDING, # Always PENDING initially, background task will update it
            plan_code=payload.plan_code,
            billing_cycle="monthly",
            payment_details={ # Store snapshot in transaction too
                 "plan_price": plan_price,
                 "apps_total": apps_price,
                 "tax": tax,
                 "discount": discount_amount,
                 "is_free": is_free
            },
            payment_method="online"
        )
        db.add(transaction)
        
        if is_free:
            logger.info(f"Offloading free activation for tenant {tenant.id} to background")
            new_order.status = OrderStatus.COMPLETED
            await db.commit() # Save order and transaction first
            
            background_tasks.add_task(
                process_free_activation_task,
                tenant.id,
                new_order.id,
                transaction.id,
                payload.plan_code
            )
        else:
            await db.commit() # Commit for paid transactions (stays PENDING)
        
        await db.refresh(transaction)
        
        print(f"Transaction Created: {transaction.id}, Status: {transaction.status}")
        print(f"========== VERIFICATION COMPLETE ==========")

        return ResponseHandler.success(
            message="Order created",
            data={
                "valid": True,
                "razorpay_order_id": order_id,
                "transaction_id": str(transaction.id), # Ensure string for JSON
                "order_id": str(new_order.id),
                "amount": grand_total,
                "currency": "INR",
                "key_id": razorpay_key
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"EXCEPTION: {str(e)}")
        return ResponseHandler.error(message="Payment verification failed", error_details={"detail": str(e)})


@router.post("/payment-status", response_model=APIResponse)
async def get_payment_status(payload: PaymentStatusRequest, db: AsyncSession = Depends(get_db)):
    """
    Check the status of a payment transaction and its associated subscription.
    This is used by the frontend to poll after a Razorpay checkout.
    """
    try:
        # 1. Fetch Transaction
        stmt = select(Transaction).filter(Transaction.id == payload.transaction_id)
        result = await db.execute(stmt)
        transaction = result.scalars().first()
        
        if not transaction:
            return ResponseHandler.not_found(message="Transaction not found")

        # 2. Check Subscription (if transaction successful)
        subscription_status = "inactive"
        if transaction.status == TransactionStatus.SUCCESS:
            sub_stmt = select(Subscription).filter(Subscription.tenant_id == transaction.tenant_id)
            sub_result = await db.execute(sub_stmt)
            subscription = sub_result.scalars().first()
            if subscription:
                subscription_status = subscription.status.value if hasattr(subscription.status, 'value') else str(subscription.status)

        # 3. Formulate Response
        status_map = {
            TransactionStatus.SUCCESS: "SUCCESS",
            TransactionStatus.PENDING: "PENDING",
            TransactionStatus.FAILED: "FAILED"
        }
        
        status_str = status_map.get(transaction.status, "PENDING")

        response_data = PaymentStatusResponse(
            valid=True,
            status=status_str,
            subscription_status=subscription_status,
            razorpay_order_id=transaction.provider_order_id,
            transaction_id=transaction.id,
            amount=float(transaction.amount),
            currency=transaction.currency,
            message=f"Transaction is current {status_str}"
        )

        return ResponseHandler.success(
            message="Payment status fetched",
            data=[response_data.dict()]
        )

    except Exception as e:
        logger.error(f"Error fetching payment status: {str(e)}")
        return ResponseHandler.error(message="Failed to fetch payment status", error_details={"detail": str(e)})


@router.get("/payment-history", response_model=APIResponse)
async def get_payment_history(tenant_uuid: UUID, db: AsyncSession = Depends(get_db)):
    """
    Fetch transaction history for a tenant.
    """
    try:
        # Transaction already has relationship with Tenant
        stmt = select(Transaction).join(Tenant).filter(Tenant.tenant_uuid == tenant_uuid).order_by(Transaction.created_at.desc())
        result = await db.execute(stmt)
        transactions = result.scalars().all()
        
        history = []
        for txn in transactions:
            history.append({
                "id": str(txn.id),
                "amount": float(txn.amount),
                "status": txn.status.value if hasattr(txn.status, 'value') else str(txn.status),
                "date": txn.created_at.strftime("%b %d, %Y %H:%M") if txn.created_at else "N/A",
                "method": txn.payment_method or "N/A",
                "provider_order_id": txn.provider_order_id
            })
            
        return ResponseHandler.success(
            message="Payment history fetched",
            data=history
        )
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        import traceback
        traceback.print_exc()
        return ResponseHandler.error(message="Failed to fetch payment history", error_details={"detail": str(e)})
