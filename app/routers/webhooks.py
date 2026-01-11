from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.response import ResponseHandler, APIResponse
from app.db.database import get_db
import logging
import json

# Import Controller Logic
from app.controllers.payment_webhook_controller import (
    verify_razorpay_signature,
    handle_payment_success,
    handle_payment_failure,
    handle_order_paid
)

from app.core.logger import create_logger

logger = create_logger('webhooks')
router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)

@router.post("/razorpay", response_model=APIResponse)
async def razorpay_webhook(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook endpoint to handle payment events (e.g., from Stripe, Razorpay).
    """
    try:
        logger.info("Razorpay webhook received")
        
        # 1. Get Raw Body for Signature Verification
        body_bytes = await request.body()
        signature = request.headers.get("X-Razorpay-Signature")

        # 2. Verify Signature
        if signature:
             try:
                 verify_razorpay_signature(body_bytes, signature)
             except ValueError:
                 raise HTTPException(status_code=400, detail="Invalid signature")
        else:
             logger.warning("Missing X-Razorpay-Signature header. Skipping verification (dev mode?) or strictly failing.")
             # Uncomment to enforce:
             # raise HTTPException(status_code=400, detail="Missing signature")
        
        # 3. Parse Payload
        payload = json.loads(body_bytes)
        # logger.debug(f"Payload: {payload}")
        print(payload)
        event_type = payload.get("event")
        data = payload.get("payload", {}).get("payment", {}).get("entity", {})
        
        # Also check for order entity if relevant
        order_data = payload.get("payload", {}).get("order", {}).get("entity", {})

        logger.info(f"Received webhook event: {event_type}")
        print(order_data)
        # 4. Handle specific events via Controller
        if event_type == "payment.captured":
            await handle_payment_success(data, order_data, db, background_tasks)
        elif event_type == "payment.failed":
            await handle_payment_failure(data, db)
        elif event_type == "order.paid":
             await handle_order_paid(order_data, db)
        
        # Return success (200 OK) to acknowledge receipt
        return ResponseHandler.success(message="Webhook received successfully")

    except json.JSONDecodeError:
        return ResponseHandler.error(message="Invalid JSON payload", error_details={"detail": "Could not parse request body"})
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        # Return 400 or 500 depending on the error, but usually webhooks check for 200
        return ResponseHandler.error(message="Webhook processing failed", error_details={"detail": str(e)})
