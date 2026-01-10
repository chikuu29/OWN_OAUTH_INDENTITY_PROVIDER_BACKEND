from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.transactions import Transaction, TransactionStatus
from app.models.orders import Order, OrderStatus
from app.models.subscriptions import Subscription, SubscriptionStatus
from app.controllers.subscription_controller import SubscriptionController
import logging
import razorpay
import os

# Configure logger
logger = logging.getLogger(__name__)

def verify_razorpay_signature(body: bytes, signature: str):
    """
    Verifies the Razorpay webhook signature.
    Raises exception if verification fails.
    """
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not webhook_secret:
        logger.warning("RAZORPAY_WEBHOOK_SECRET not set. Skipping signature verification.")
        return # Or raise error if strict

    client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))
    
    # Razorpay utility expects body as string? documentation says raw body.
    # client.utility.verify_webhook_signature(body, signature, secret)
    # verify_webhook_signature signature: (body: str, signature: str, secret: str) -> bool/None
    # It raises SignatureVerificationError if fails.
    
    try:
        # decode bytes to string if needed, but usually raw bytes preferred for HMAC.
        # Razorpay python lib might handle string. Let's pass decode('utf-8') to be safe if it expects str.
        client.utility.verify_webhook_signature(body.decode('utf-8'), signature, webhook_secret)
        logger.info("Signature verification successful")
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        raise ValueError("Invalid signature")

async def handle_payment_success(payment_data: dict, order_data: dict, db: AsyncSession):
    """
    Handle successful payment (payment.captured).
    Updates Transaction, Order, and activates Subscription.
    """
    try:
        razorpay_payment_id = payment_data.get("id")
        razorpay_order_id = payment_data.get("order_id")
        
        logger.info(f"Processing successful payment: {razorpay_payment_id} for order {razorpay_order_id}")

        # 1. Update Transaction
        # Find transaction by provider_order_id or provider_payment_id
        # Usually we create the transaction with provider_order_id (razorpay_order_id)
        stmt = select(Transaction).filter(Transaction.provider_order_id == razorpay_order_id)
        result = await db.execute(stmt)
        transaction = result.scalars().first()

        if transaction:
            transaction.status = TransactionStatus.SUCCESS
            transaction.provider_payment_id = razorpay_payment_id
            # transaction.payment_details = payment_data # Store full dump
            
            # 2. Activate Subscription
            if transaction.subscription_id:
                # Fetch Order to get items
                order_stmt = select(Order).filter(Order.provider_order_id == razorpay_order_id)
                order_result = await db.execute(order_stmt)
                order = order_result.scalars().first()
                order_items = order.items if order else None

                sub_controller = SubscriptionController(db)
                await sub_controller.activate_subscription(transaction.subscription_id, order_items=order_items)
                logger.info(f"Activating subscription {transaction.subscription_id}")
            
            await db.commit()
            logger.info("Transaction and Subscription updated.")
        else:
            logger.warning(f"Transaction not found for order id: {razorpay_order_id}")

    except Exception as e:
        logger.error(f"Failed to handle payment success: {e}")
        await db.rollback()
        raise e

async def handle_payment_failure(payment_data: dict, db: AsyncSession):
    """
    Handle failed payment (payment.failed).
    """
    try:
        razorpay_order_id = payment_data.get("order_id")
        razorpay_payment_id = payment_data.get("id")
        error_description = payment_data.get("error_description")

        logger.info(f"Processing failed payment: {razorpay_payment_id}")

        stmt = select(Transaction).filter(Transaction.provider_order_id == razorpay_order_id)
        result = await db.execute(stmt)
        transaction = result.scalars().first()

        if transaction:
            transaction.status = TransactionStatus.FAILED
            transaction.provider_payment_id = razorpay_payment_id
            transaction.payment_details = payment_data
            await db.commit()
            logger.info("Transaction marked as FAILED.")
        else:
            logger.warning(f"Transaction not found for order id: {razorpay_order_id}")

    except Exception as e:
        logger.error(f"Failed to handle payment failure: {e}")
        await db.rollback()
        raise e

async def handle_order_paid(order_data: dict, db: AsyncSession):
    """
    Handle order.paid event. Updates Order status.
    """
    try:
        razorpay_order_id = order_data.get("id")
        
        # Update Order table
        stmt = select(Order).filter(Order.provider_order_id == razorpay_order_id)
        result = await db.execute(stmt)
        order = result.scalars().first()

        if order:
            order.status = OrderStatus.COMPLETED
            await db.commit()
            logger.info(f"Order {order.id} marked as COMPLETED.")

    except Exception as e:
        logger.error(f"Failed to handle order paid: {e}")
        await db.rollback()
        raise e
