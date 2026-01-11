from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.transactions import Transaction, TransactionStatus
from app.models.orders import Order, OrderStatus
from app.models.subscriptions import Subscription, SubscriptionStatus
from app.controllers.subscription_controller import SubscriptionController
import razorpay
import os
from .base_controller import BaseController
from fastapi import BackgroundTasks
from typing import Optional

class PaymentWebhookController(BaseController):
    def __init__(self, db: AsyncSession, background_tasks: Optional[BackgroundTasks] = None):
        super().__init__(db, background_tasks=background_tasks, logger_name='webhooks')

    def verify_razorpay_signature(self, body: bytes, signature: str):
        """
        Verifies the Razorpay webhook signature.
        """
        webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
        if not webhook_secret:
            self.logger.warning("RAZORPAY_WEBHOOK_SECRET not set. Skipping signature verification.")
            return

        client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))
        
        try:
            client.utility.verify_webhook_signature(body.decode('utf-8'), signature, webhook_secret)
            self.logger.info("Signature verification successful")
        except Exception as e:
            self.logger.error(f"Signature verification failed: {e}")
            raise ValueError("Invalid signature")

    async def handle_payment_success(self, payment_data: dict, order_data: dict):
        """
        Handle successful payment (payment.captured).
        """
        try:
            razorpay_payment_id = payment_data.get("id")
            razorpay_order_id = payment_data.get("order_id")
            
            self.logger.info(f"Processing successful payment: {razorpay_payment_id} for order {razorpay_order_id}")

            stmt = select(Transaction).filter(Transaction.provider_order_id == razorpay_order_id)
            result = await self.db.execute(stmt)
            transaction = result.scalars().first()

            if transaction:
                # Fetch Order first as we need it for both cases
                order_stmt = select(Order).filter(Order.provider_order_id == razorpay_order_id)
                order_result = await self.db.execute(order_stmt)
                order = order_result.scalars().first()
                
                sub_controller = SubscriptionController(
                    self.db,
                    tenant_id=transaction.tenant_id,
                    plan_code=transaction.plan_code,
                    background_tasks=self.background_tasks
                )
                
                if order:
                    self.logger.info(f"Creating new subscription from Order {order.id}")
                    new_sub = await sub_controller.create_subscription_from_order(order)
                    transaction.subscription_id = new_sub.id
                    self.logger.info(f"Created and activated new subscription {new_sub.id}")
                    
                    transaction.status = TransactionStatus.SUCCESS
                    transaction.provider_payment_id = razorpay_payment_id
                else:
                    self.logger.warning("No Order found to create subscription.")

                await self.db.commit()
                self.logger.info("Transaction and Subscription processed.")
            else:
                self.logger.warning(f"Transaction not found for order id: {razorpay_order_id}")

        except Exception as e:
            self.logger.error(f"Failed to handle payment success: {e}")
            await self.db.rollback()
            raise e

    async def handle_payment_failure(self, payment_data: dict):
        """
        Handle failed payment (payment.failed).
        """
        try:
            razorpay_order_id = payment_data.get("order_id")
            razorpay_payment_id = payment_data.get("id")

            self.logger.info(f"Processing failed payment: {razorpay_payment_id}")

            stmt = select(Transaction).filter(Transaction.provider_order_id == razorpay_order_id)
            result = await self.db.execute(stmt)
            transaction = result.scalars().first()

            if transaction:
                transaction.status = TransactionStatus.FAILED
                transaction.provider_payment_id = razorpay_payment_id
                transaction.payment_details = payment_data
                await self.db.commit()
                self.logger.info("Transaction marked as FAILED.")
            else:
                self.logger.warning(f"Transaction not found for order id: {razorpay_order_id}")

        except Exception as e:
            self.logger.error(f"Failed to handle payment failure: {e}")
            await self.db.rollback()
            raise e

    async def handle_order_paid(self, order_data: dict):
        """
        Handle order.paid event. Updates Order status.
        """
        try:
            razorpay_order_id = order_data.get("id")
            
            stmt = select(Order).filter(Order.provider_order_id == razorpay_order_id)
            result = await self.db.execute(stmt)
            order = result.scalars().first()

            if order:
                order.status = OrderStatus.COMPLETED
                await self.db.commit()
                self.logger.info(f"Order {order.id} marked as COMPLETED.")

        except Exception as e:
            self.logger.error(f"Failed to handle order paid: {e}")
            await self.db.rollback()
            raise e
