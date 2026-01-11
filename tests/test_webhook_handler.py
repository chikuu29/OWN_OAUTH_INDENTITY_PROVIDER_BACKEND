import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.controllers.payment_webhook_controller import handle_payment_success
from app.models.transactions import Transaction, TransactionStatus
from app.models.orders import Order
from app.models.subscriptions import Subscription

@pytest.mark.asyncio
async def test_handle_payment_success_logic():
    # 1. Setup Mock Data
    order_id = "order_test_123"
    payment_id = "pay_test_456"
    tenant_id = 1
    
    payment_data = {
        "id": payment_id,
        "order_id": order_id
    }
    
    # Mock Database Session
    db = AsyncMock()
    
    # Mock Transaction Object
    mock_transaction = MagicMock(spec=Transaction)
    mock_transaction.tenant_id = tenant_id
    mock_transaction.plan_code = "PREMIUM"
    mock_transaction.status = TransactionStatus.PENDING
    
    # Mock Order Object
    mock_order = MagicMock(spec=Order)
    mock_order.id = uuid4()
    mock_order.provider_order_id = order_id
    
    # Mock Subscription Object
    mock_subscription = MagicMock(spec=Subscription)
    mock_subscription.id = uuid4()

    # 2. Setup DB Execution Mocks
    # First execution for Transaction
    mock_transaction_result = MagicMock()
    mock_transaction_result.scalars.return_value.first.return_value = mock_transaction
    
    # Second execution for Order
    mock_order_result = MagicMock()
    mock_order_result.scalars.return_value.first.return_value = mock_order
    
    db.execute.side_effect = [mock_transaction_result, mock_order_result]

    # 3. Mock SubscriptionController
    with patch("app.controllers.payment_webhook_controller.SubscriptionController") as MockSubController:
        mock_controller_instance = MockSubController.return_value
        mock_controller_instance.create_subscription_from_order = AsyncMock(return_value=mock_subscription)
        
        # 4. Run the handler
        await handle_payment_success(payment_data, {}, db)
        
        # 5. Assertions
        # Check transaction updates
        assert mock_transaction.status == TransactionStatus.SUCCESS
        assert mock_transaction.provider_payment_id == payment_id
        assert mock_transaction.subscription_id == mock_subscription.id
        
        # Check DB operations
        assert db.commit.called
        assert MockSubController.called
        mock_controller_instance.create_subscription_from_order.assert_called_once_with(mock_order, None)

@pytest.mark.asyncio
async def test_handle_payment_success_no_transaction():
    db = AsyncMock()
    db.execute.return_value.scalars.return_value.first.return_value = None
    
    # Should log a warning and not crash
    await handle_payment_success({"id": "pay_1", "order_id": "ord_1"}, {}, db)
    
    assert not db.commit.called
