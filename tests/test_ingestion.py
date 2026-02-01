"""Tests for ingestion module."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, patch

from monetization_engine.ingestion import StripeIngestion
from monetization_engine.ingestion.usage import UsageTracker
from monetization_engine.models import (
    Product, Plan, Subscription, RevenueEvent, RevenueEventType,
    UsageRecord, MRRSnapshot
)


def test_stripe_ingestion_init(db_session):
    """Test StripeIngestion initialization."""
    ingestion = StripeIngestion(db_session)
    assert ingestion.db == db_session


def test_usage_tracker_init(db_session):
    """Test UsageTracker initialization."""
    tracker = UsageTracker(db_session)
    assert tracker.db == db_session


def test_usage_tracker_record_usage(db_session):
    """Test recording usage data."""
    # Create subscription
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        limits={"api_calls": 1000},
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=29.0
    )
    db_session.add(subscription)
    db_session.commit()
    
    tracker = UsageTracker(db_session)
    
    # Record usage with required period fields
    period_start = datetime.now(UTC) - timedelta(hours=1)
    period_end = datetime.now(UTC)
    
    tracker.record_usage(
        customer_id="cus_test",
        metric_name="api_calls",
        quantity=150,
        period_start=period_start,
        period_end=period_end
    )
    
    # Verify usage record was created
    records = db_session.query(UsageRecord).all()
    assert len(records) == 1
    assert records[0].metric_name == "api_calls"
    assert records[0].quantity == 150


def test_revenue_event_creation(db_session):
    """Test creating revenue events."""
    # Create subscription
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=29.0
    )
    db_session.add(subscription)
    db_session.commit()
    
    # Create a revenue event
    event = RevenueEvent(
        subscription_id=subscription.id,
        event_type=RevenueEventType.SUBSCRIPTION_CREATED,
        stripe_event_id="evt_test",
        amount=29.0,
        mrr_delta=29.0,
        occurred_at=datetime.now(UTC)
    )
    db_session.add(event)
    db_session.commit()
    
    # Verify event was created
    events = db_session.query(RevenueEvent).all()
    assert len(events) == 1
    assert events[0].event_type == RevenueEventType.SUBSCRIPTION_CREATED
    assert events[0].mrr_delta == 29.0


def test_usage_tracker_no_active_subscription(db_session):
    """Test usage recording fails for inactive subscription."""
    tracker = UsageTracker(db_session)
    
    # Try to record usage for non-existent customer
    with pytest.raises(ValueError, match="No active subscription"):
        tracker.record_usage(
            customer_id="cus_nonexistent",
            metric_name="api_calls",
            quantity=100,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC)
        )


def test_usage_tracker_get_usage_summary(db_session):
    """Test getting usage summary for subscription."""
    # Create subscription with limits
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        limits={"api_calls": 10000, "storage_gb": 100},
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Add multiple usage records
    period_start = datetime.now(UTC) - timedelta(days=10)
    period_end = datetime.now(UTC)
    
    usage1 = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=3000,
        limit=10000,
        period_start=period_start,
        period_end=period_end
    )
    db_session.add(usage1)
    
    usage2 = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=2500,
        limit=10000,
        period_start=period_start,
        period_end=period_end
    )
    db_session.add(usage2)
    
    usage3 = UsageRecord(
        subscription_id=subscription.id,
        metric_name="storage_gb",
        quantity=45,
        limit=100,
        period_start=period_start,
        period_end=period_end
    )
    db_session.add(usage3)
    db_session.commit()
    
    # Get summary
    tracker = UsageTracker(db_session)
    summary = tracker.get_usage_summary(subscription.id)
    
    # Verify summary
    assert "api_calls" in summary
    assert "storage_gb" in summary
    assert summary["api_calls"]["total"] == 5500  # 3000 + 2500
    assert summary["api_calls"]["limit"] == 10000
    assert summary["api_calls"]["utilization"] == 0.55  # 5500/10000
    assert summary["storage_gb"]["total"] == 45
    assert summary["storage_gb"]["utilization"] == 0.45  # 45/100


def test_usage_tracker_bulk_import(db_session):
    """Test bulk importing usage data."""
    # Create multiple subscriptions
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        limits={"api_calls": 1000},
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    # Customer 1
    sub1 = Subscription(
        stripe_subscription_id="sub_1",
        customer_id="cus_1",
        plan_id=plan.id,
        status="active",
        mrr=29.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
    )
    db_session.add(sub1)
    
    # Customer 2
    sub2 = Subscription(
        stripe_subscription_id="sub_2",
        customer_id="cus_2",
        plan_id=plan.id,
        status="active",
        mrr=29.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
    )
    db_session.add(sub2)
    db_session.commit()
    
    # Bulk import data
    tracker = UsageTracker(db_session)
    usage_data = [
        {
            "customer_id": "cus_1",
            "metric_name": "api_calls",
            "quantity": 500,
            "period_start": datetime.now(UTC) - timedelta(hours=1),
            "period_end": datetime.now(UTC)
        },
        {
            "customer_id": "cus_2",
            "metric_name": "api_calls",
            "quantity": 750,
            "period_start": datetime.now(UTC) - timedelta(hours=1),
            "period_end": datetime.now(UTC)
        },
        {
            "customer_id": "cus_nonexistent",  # Should fail but not crash
            "metric_name": "api_calls",
            "quantity": 100,
            "period_start": datetime.now(UTC) - timedelta(hours=1),
            "period_end": datetime.now(UTC)
        }
    ]
    
    count = tracker.bulk_import_usage(usage_data)
    
    # Should import 2 out of 3 (last one fails)
    assert count == 2
    
    # Verify records were created
    records = db_session.query(UsageRecord).all()
    assert len(records) == 2


def test_usage_summary_with_date_filters(db_session):
    """Test usage summary with period filters."""
    # Create subscription
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        limits={"api_calls": 10000},
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=30),
        current_period_end=datetime.now(UTC)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Add usage records from different periods
    # Old usage (30 days ago)
    old_usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=1000,
        limit=10000,
        period_start=datetime.now(UTC) - timedelta(days=30),
        period_end=datetime.now(UTC) - timedelta(days=20)
    )
    db_session.add(old_usage)
    
    # Recent usage (7 days ago)
    recent_usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=2000,
        limit=10000,
        period_start=datetime.now(UTC) - timedelta(days=7),
        period_end=datetime.now(UTC)
    )
    db_session.add(recent_usage)
    db_session.commit()
    
    tracker = UsageTracker(db_session)
    
    # Get all usage
    all_summary = tracker.get_usage_summary(subscription.id)
    assert all_summary["api_calls"]["total"] == 3000  # 1000 + 2000
    
    # Get only recent usage (last 10 days)
    recent_summary = tracker.get_usage_summary(
        subscription.id,
        period_start=datetime.now(UTC) - timedelta(days=10),
        period_end=datetime.now(UTC)
    )
    assert recent_summary["api_calls"]["total"] == 2000  # Only recent


def test_usage_record_with_no_limit(db_session):
    """Test recording usage when plan has no limit for metric."""
    # Create subscription with plan that has no limits
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Enterprise",
        price_monthly=299.0,
        limits={},  # No limits
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=299.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.commit()
    
    tracker = UsageTracker(db_session)
    
    period_start = datetime.now(UTC) - timedelta(hours=1)
    period_end = datetime.now(UTC)
    
    usage = tracker.record_usage(
        customer_id="cus_test",
        metric_name="api_calls",
        quantity=50000,  # No limit
        period_start=period_start,
        period_end=period_end
    )
    
    # Verify limit is None
    assert usage.limit is None
    assert usage.quantity == 50000


def test_mrr_snapshot_creation(db_session):
    """Test creating MRR snapshots."""
    # Create snapshot
    snapshot = MRRSnapshot(
        date=datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0),
        total_mrr=100.0,
        new_mrr=50.0,
        expansion_mrr=30.0,
        contraction_mrr=10.0,
        churned_mrr=20.0
    )
    db_session.add(snapshot)
    db_session.commit()
    
    # Verify snapshot
    snapshots = db_session.query(MRRSnapshot).all()
    assert len(snapshots) == 1
    assert snapshots[0].total_mrr == 100.0
    assert snapshots[0].new_mrr == 50.0


def test_subscription_status_transitions(db_session):
    """Test subscription status changes."""
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=29.0
    )
    db_session.add(subscription)
    db_session.commit()
    
    # Update status
    subscription.status = "canceled"
    subscription.canceled_at = datetime.now(UTC)
    db_session.commit()
    
    # Verify update
    sub = db_session.query(Subscription).filter_by(stripe_subscription_id="sub_test").first()
    assert sub.status == "canceled"
    assert sub.canceled_at is not None


def test_usage_record_with_limits(db_session):
    """Test usage records with plan limits."""
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        limits={"api_calls": 1000, "storage_gb": 10},
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=29.0
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create usage record
    usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=750,
        limit=1000,
        period_start=datetime.now(UTC) - timedelta(days=1),
        period_end=datetime.now(UTC)
    )
    db_session.add(usage)
    db_session.commit()
    
    # Verify usage
    records = db_session.query(UsageRecord).all()
    assert len(records) == 1
    assert records[0].quantity == 750
    assert records[0].limit == 1000
    assert records[0].quantity / records[0].limit == 0.75  # 75% utilization



def test_stripe_ingestion_init(db_session):
    """Test StripeIngestion initialization."""
    ingestion = StripeIngestion(db_session)
    assert ingestion.db == db_session


def test_usage_tracker_record_usage(db_session):
    """Test recording usage data with period info."""
    # Create subscription
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        limits={"api_calls": 1000},
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=29.0
    )
    db_session.add(subscription)
    db_session.commit()
    
    tracker = UsageTracker(db_session)
    
    period_start = datetime.now(UTC) - timedelta(days=1)
    period_end = datetime.now(UTC)
    
    tracker.record_usage(
        customer_id="cus_test",
        metric_name="api_calls",
        quantity=150,
        period_start=period_start,
        period_end=period_end
    )
    
    # Verify usage record was created
    records = db_session.query(UsageRecord).all()
    assert len(records) == 1
    assert records[0].metric_name == "api_calls"
    assert records[0].quantity == 150


def test_process_revenue_events(db_session):
    """Test processing revenue events."""
    # Create subscription
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=29.0
    )
    db_session.add(subscription)
    db_session.commit()
    
    # Create a revenue event
    event = RevenueEvent(
        subscription_id=subscription.id,
        event_type=RevenueEventType.SUBSCRIPTION_CREATED,
        stripe_event_id="evt_test",
        amount=29.0,
        mrr_delta=29.0,
        occurred_at=datetime.now(UTC)
    )
    db_session.add(event)
    db_session.commit()
    
    # Verify event was created
    events = db_session.query(RevenueEvent).all()
    assert len(events) == 1
    assert events[0].event_type == RevenueEventType.SUBSCRIPTION_CREATED
    assert events[0].mrr_delta == 29.0

def test_webhook_subscription_created(db_session):
    """Test handling subscription.created webhook."""
    # Create product and plan first
    product = Product(name="Test Product", stripe_product_id="prod_123")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        stripe_price_id="price_123",
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.commit()
    
    # Create webhook event data
    event_data = {
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_webhook123",
                "customer": "cus_webhook",
                "status": "active",
                "current_period_start": int(datetime.now(UTC).timestamp()),
                "current_period_end": int((datetime.now(UTC) + timedelta(days=30)).timestamp()),
                "items": {
                    "data": [{
                        "price": {
                            "id": "price_123",
                            "unit_amount": 9900,
                            "recurring": {"interval": "month"}
                        },
                        "quantity": 1
                    }]
                }
            }
        }
    }
    
    ingestion = StripeIngestion(db_session)
    ingestion.process_webhook_event(event_data)
    
    # Verify subscription was created
    subscription = db_session.query(Subscription).filter(
        Subscription.stripe_subscription_id == "sub_webhook123"
    ).first()
    
    assert subscription is not None
    assert subscription.customer_id == "cus_webhook"
    assert subscription.mrr == 99.0
    assert subscription.status == "active"
    
    # Verify revenue event was created
    event = db_session.query(RevenueEvent).filter(
        RevenueEvent.subscription_id == subscription.id
    ).first()
    
    assert event is not None
    assert event.event_type == RevenueEventType.SUBSCRIPTION_CREATED
    assert event.mrr_delta == 99.0


def test_webhook_subscription_upgraded(db_session):
    """Test handling subscription upgrade webhook."""
    # Create existing subscription
    product = Product(name="Test Product", stripe_product_id="prod_123")
    db_session.add(product)
    db_session.flush()
    
    starter_plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        stripe_price_id="price_starter",
        effective_from=datetime.now(UTC)
    )
    db_session.add(starter_plan)
    
    pro_plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        stripe_price_id="price_pro",
        effective_from=datetime.now(UTC)
    )
    db_session.add(pro_plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_upgrade",
        customer_id="cus_upgrade",
        plan_id=starter_plan.id,
        status="active",
        mrr=29.0,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.commit()
    
    # Webhook event for upgrade
    event_data = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_upgrade",
                "customer": "cus_upgrade",
                "status": "active",
                "current_period_start": int(datetime.now(UTC).timestamp()),
                "current_period_end": int((datetime.now(UTC) + timedelta(days=30)).timestamp()),
                "items": {
                    "data": [{
                        "price": {
                            "id": "price_pro",
                            "unit_amount": 9900,
                            "recurring": {"interval": "month"}
                        },
                        "quantity": 1
                    }]
                }
            }
        }
    }
    
    ingestion = StripeIngestion(db_session)
    ingestion.process_webhook_event(event_data)
    
    # Verify subscription was updated
    db_session.refresh(subscription)
    assert subscription.mrr == 99.0
    
    # Verify upgrade event was created
    event = db_session.query(RevenueEvent).filter(
        RevenueEvent.subscription_id == subscription.id,
        RevenueEvent.event_type == RevenueEventType.SUBSCRIPTION_UPGRADED
    ).first()
    
    assert event is not None
    assert event.mrr_delta == 70.0  # 99 - 29


def test_webhook_subscription_downgraded(db_session):
    """Test handling subscription downgrade webhook."""
    # Create existing subscription
    product = Product(name="Test Product", stripe_product_id="prod_123")
    db_session.add(product)
    db_session.flush()
    
    pro_plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        stripe_price_id="price_pro",
        effective_from=datetime.now(UTC)
    )
    db_session.add(pro_plan)
    
    starter_plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        stripe_price_id="price_starter",
        effective_from=datetime.now(UTC)
    )
    db_session.add(starter_plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_downgrade",
        customer_id="cus_downgrade",
        plan_id=pro_plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.commit()
    
    # Webhook event for downgrade
    event_data = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_downgrade",
                "customer": "cus_downgrade",
                "status": "active",
                "current_period_start": int(datetime.now(UTC).timestamp()),
                "current_period_end": int((datetime.now(UTC) + timedelta(days=30)).timestamp()),
                "items": {
                    "data": [{
                        "price": {
                            "id": "price_starter",
                            "unit_amount": 2900,
                            "recurring": {"interval": "month"}
                        },
                        "quantity": 1
                    }]
                }
            }
        }
    }
    
    ingestion = StripeIngestion(db_session)
    ingestion.process_webhook_event(event_data)
    
    # Verify subscription was updated
    db_session.refresh(subscription)
    assert subscription.mrr == 29.0
    
    # Verify downgrade event was created
    event = db_session.query(RevenueEvent).filter(
        RevenueEvent.subscription_id == subscription.id,
        RevenueEvent.event_type == RevenueEventType.SUBSCRIPTION_DOWNGRADED
    ).first()
    
    assert event is not None
    assert event.mrr_delta == -70.0  # 29 - 99


def test_webhook_subscription_deleted(db_session):
    """Test handling subscription.deleted webhook."""
    # Create subscription
    product = Product(name="Test Product", stripe_product_id="prod_123")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        stripe_price_id="price_pro",
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_cancel",
        customer_id="cus_cancel",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.commit()
    
    # Webhook event for cancellation
    event_data = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_cancel",
                "customer": "cus_cancel",
                "status": "canceled",
                "current_period_start": int(datetime.now(UTC).timestamp()),
                "current_period_end": int((datetime.now(UTC) + timedelta(days=30)).timestamp()),
                "items": {
                    "data": [{
                        "price": {
                            "id": "price_pro",
                            "unit_amount": 9900,
                            "recurring": {"interval": "month"}
                        },
                        "quantity": 1
                    }]
                }
            }
        }
    }
    
    ingestion = StripeIngestion(db_session)
    ingestion.process_webhook_event(event_data)
    
    # Verify subscription was canceled
    db_session.refresh(subscription)
    assert subscription.status == "canceled"
    assert subscription.mrr == 0.0
    assert subscription.canceled_at is not None
    
    # Verify cancellation event was created
    event = db_session.query(RevenueEvent).filter(
        RevenueEvent.subscription_id == subscription.id,
        RevenueEvent.event_type == RevenueEventType.SUBSCRIPTION_CANCELED
    ).first()
    
    assert event is not None
    assert event.mrr_delta == -99.0


def test_webhook_payment_succeeded(db_session):
    """Test handling invoice.payment_succeeded webhook."""
    # Create subscription
    product = Product(name="Test Product", stripe_product_id="prod_123")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        stripe_price_id="price_pro",
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_payment",
        customer_id="cus_payment",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.commit()
    
    # Webhook event for payment
    event_data = {
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_success",
                "subscription": "sub_payment",
                "amount_paid": 9900,
                "currency": "usd"
            }
        }
    }
    
    ingestion = StripeIngestion(db_session)
    ingestion.process_webhook_event(event_data)
    
    # Verify payment event was created
    event = db_session.query(RevenueEvent).filter(
        RevenueEvent.subscription_id == subscription.id,
        RevenueEvent.event_type == RevenueEventType.PAYMENT_SUCCEEDED
    ).first()
    
    assert event is not None
    assert event.amount == 99.0
    assert event.currency == "USD"


def test_webhook_payment_failed(db_session):
    """Test handling invoice.payment_failed webhook."""
    # Create subscription
    product = Product(name="Test Product", stripe_product_id="prod_123")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        stripe_price_id="price_pro",
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_fail",
        customer_id="cus_fail",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.commit()
    
    # Webhook event for failed payment
    event_data = {
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_fail",
                "subscription": "sub_fail",
                "amount_due": 9900,
                "currency": "usd",
                "attempt_count": 2
            }
        }
    }
    
    ingestion = StripeIngestion(db_session)
    ingestion.process_webhook_event(event_data)
    
    # Verify payment failure event was created
    event = db_session.query(RevenueEvent).filter(
        RevenueEvent.subscription_id == subscription.id,
        RevenueEvent.event_type == RevenueEventType.PAYMENT_FAILED
    ).first()
    
    assert event is not None
    assert event.amount == 99.0
    assert event.event_metadata["attempt_count"] == 2


def test_calculate_mrr_annual_subscription(db_session):
    """Test MRR calculation for annual subscriptions."""
    product = Product(name="Test Product", stripe_product_id="prod_123")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro Annual",
        price_monthly=83.25,  # $999/year / 12
        price_annual=999.0,
        stripe_price_id="price_annual",
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.commit()
    
    # Subscription data with annual billing
    subscription_data = {
        "id": "sub_annual",
        "customer": "cus_annual",
        "status": "active",
        "current_period_start": int(datetime.now(UTC).timestamp()),
        "current_period_end": int((datetime.now(UTC) + timedelta(days=365)).timestamp()),
        "items": {
            "data": [{
                "price": {
                    "id": "price_annual",
                    "unit_amount": 99900,
                    "recurring": {"interval": "year"}
                },
                "quantity": 1
            }]
        }
    }
    
    ingestion = StripeIngestion(db_session)
    mrr = ingestion._calculate_mrr(subscription_data)
    
    assert mrr == 83.25  # 999 / 12


def test_webhook_unhandled_event(db_session):
    """Test handling unhandled webhook event types."""
    event_data = {
        "type": "customer.created",
        "data": {
            "object": {
                "id": "cus_123"
            }
        }
    }
    
    ingestion = StripeIngestion(db_session)
    # Should not raise an error, just log and ignore
    ingestion.process_webhook_event(event_data)


@patch('stripe.Product.list')
@patch('stripe.Price.list')
def test_sync_products_and_plans_new_product(mock_price_list, mock_product_list, db_session):
    """Test syncing new products and plans from Stripe."""
    # Mock Stripe responses
    mock_product = Mock()
    mock_product.id = "prod_test123"
    mock_product.name = "Premium Plan"
    mock_product.description = "Our premium offering"
    
    mock_product_list.return_value = Mock(data=[mock_product])
    
    mock_price = Mock()
    mock_price.id = "price_test123"
    mock_price.nickname = "Monthly Premium"
    mock_price.unit_amount = 9900  # $99.00
    mock_price.currency = "usd"
    mock_price.recurring = Mock(interval="month")
    mock_price.metadata = {"api_calls": "10000", "storage_gb": "100"}
    mock_price.created = int(datetime.now(UTC).timestamp())
    
    mock_price_list.return_value = Mock(data=[mock_price])
    
    # Sync products
    ingestion = StripeIngestion(db_session)
    ingestion.sync_products_and_plans()
    
    # Verify product was created
    products = db_session.query(Product).all()
    assert len(products) == 1
    assert products[0].stripe_product_id == "prod_test123"
    assert products[0].name == "Premium Plan"
    
    # Verify plan was created
    plans = db_session.query(Plan).all()
    assert len(plans) == 1
    assert plans[0].name == "Monthly Premium"
    assert plans[0].price_monthly == 99.0


@patch('stripe.Product.list')
@patch('stripe.Price.list')
def test_sync_products_existing_product(mock_price_list, mock_product_list, db_session):
    """Test syncing when product already exists."""
    # Create existing product
    product = Product(
        name="Old Name",
        stripe_product_id="prod_existing"
    )
    db_session.add(product)
    db_session.commit()
    
    # Mock Stripe responses
    mock_product = Mock()
    mock_product.id = "prod_existing"
    mock_product.name = "Updated Name"
    mock_product.description = "Updated description"
    
    mock_product_list.return_value = Mock(data=[mock_product])
    
    mock_price = Mock()
    mock_price.id = "price_new"
    mock_price.nickname = None  # Test fallback naming
    mock_price.unit_amount = 4900
    mock_price.currency = "usd"
    mock_price.recurring = Mock(interval="month")
    mock_price.metadata = {}
    mock_price.created = int(datetime.now(UTC).timestamp())
    
    mock_price_list.return_value = Mock(data=[mock_price])
    
    # Sync products
    ingestion = StripeIngestion(db_session)
    ingestion.sync_products_and_plans()
    
    # Should not create duplicate product
    products = db_session.query(Product).all()
    assert len(products) == 1
    
    # Plan should be created
    plans = db_session.query(Plan).all()
    assert len(plans) == 1
    assert plans[0].name.startswith("Plan price_ne")  # Fallback name


@patch('stripe.Product.list')
@patch('stripe.Price.list')
def test_sync_annual_plan(mock_price_list, mock_product_list, db_session):
    """Test syncing annual subscription plan."""
    # Mock Stripe responses
    mock_product = Mock()
    mock_product.id = "prod_annual"
    mock_product.name = "Annual Plan"
    mock_product.description = "Yearly subscription"
    
    mock_product_list.return_value = Mock(data=[mock_product])
    
    mock_price = Mock()
    mock_price.id = "price_annual"
    mock_price.nickname = "Annual"
    mock_price.unit_amount = 99000  # $990.00/year
    mock_price.currency = "usd"
    mock_price.recurring = Mock(interval="year")
    mock_price.metadata = {}
    mock_price.created = int(datetime.now(UTC).timestamp())
    
    mock_price_list.return_value = Mock(data=[mock_price])
    
    # Sync products
    ingestion = StripeIngestion(db_session)
    ingestion.sync_products_and_plans()
    
    # Verify plan pricing
    plans = db_session.query(Plan).all()
    assert len(plans) == 1
    assert plans[0].price_annual == 990.0
    assert plans[0].price_monthly == 82.5  # 990/12


@patch('stripe.Product.list')
@patch('stripe.Price.list')
def test_sync_existing_plan(mock_price_list, mock_product_list, db_session):
    """Test that existing plans are not duplicated."""
    # Create existing product and plan
    product = Product(
        name="Existing Product",
        stripe_product_id="prod_existing"
    )
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Existing Plan",
        price_monthly=49.0,
        stripe_price_id="price_existing",
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.commit()
    
    # Mock Stripe responses
    mock_product = Mock()
    mock_product.id = "prod_existing"
    mock_product.name = "Existing Product"
    mock_product.description = "Test"
    
    mock_product_list.return_value = Mock(data=[mock_product])
    
    mock_price = Mock()
    mock_price.id = "price_existing"
    mock_price.nickname = "Existing Plan"
    mock_price.unit_amount = 4900
    mock_price.currency = "usd"
    mock_price.recurring = Mock(interval="month")
    mock_price.metadata = {}
    mock_price.created = int(datetime.now(UTC).timestamp())
    
    mock_price_list.return_value = Mock(data=[mock_price])
    
    # Sync products
    ingestion = StripeIngestion(db_session)
    ingestion.sync_products_and_plans()
    
    # Should not create duplicate plan
    plans = db_session.query(Plan).all()
    assert len(plans) == 1


def test_handle_subscription_updated_creates_if_missing(db_session):
    """Test that updated event creates subscription if it doesn't exist."""
    # Create product and plan
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        stripe_price_id="price_test",
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.commit()
    
    ingestion = StripeIngestion(db_session)
    
    # Process updated event for non-existent subscription
    event_data = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_new",
                "customer": "cus_test",
                "status": "active",
                "current_period_start": int(datetime.now(UTC).timestamp()),
                "current_period_end": int((datetime.now(UTC) + timedelta(days=30)).timestamp()),
                "items": {
                    "data": [
                        {
                            "price": {
                                "id": "price_test",
                                "unit_amount": 2900,
                                "recurring": {"interval": "month"}
                            },
                            "quantity": 1
                        }
                    ]
                }
            }
        }
    }
    
    ingestion.process_webhook_event(event_data)
    
    # Should create subscription
    subscriptions = db_session.query(Subscription).all()
    assert len(subscriptions) == 1
    assert subscriptions[0].stripe_subscription_id == "sub_new"


def test_subscription_updated_no_mrr_change(db_session):
    """Test subscription updated event with no MRR change."""
    # Create subscription
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        stripe_price_id="price_test",
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.commit()
    
    ingestion = StripeIngestion(db_session)
    
    # Update with same MRR
    event_data = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test",
                "customer": "cus_test",
                "status": "active",
                "current_period_start": int(datetime.now(UTC).timestamp()),
                "current_period_end": int((datetime.now(UTC) + timedelta(days=30)).timestamp()),
                "items": {
                    "data": [
                        {
                            "price": {
                                "id": "price_test",
                                "unit_amount": 9900,
                                "recurring": {"interval": "month"}
                            },
                            "quantity": 1
                        }
                    ]
                }
            }
        }
    }
    
    ingestion.process_webhook_event(event_data)
    
    # Should not create revenue event for zero delta
    events = db_session.query(RevenueEvent).all()
    assert len(events) == 0


def test_payment_succeeded_no_subscription(db_session):
    """Test payment succeeded without subscription ID."""
    ingestion = StripeIngestion(db_session)
    
    # Invoice without subscription
    event_data = {
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_test",
                "subscription": None,  # No subscription
                "amount_paid": 9900,
                "currency": "usd"
            }
        }
    }
    
    # Should handle gracefully
    ingestion.process_webhook_event(event_data)
    
    # No event should be created
    events = db_session.query(RevenueEvent).all()
    assert len(events) == 0


def test_payment_failed_no_subscription(db_session):
    """Test payment failed without subscription ID."""
    ingestion = StripeIngestion(db_session)
    
    # Invoice without subscription
    event_data = {
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_test",
                "subscription": None,  # No subscription
                "amount_due": 9900,
                "currency": "usd",
                "attempt_count": 2
            }
        }
    }
    
    # Should handle gracefully
    ingestion.process_webhook_event(event_data)
    
    # No event should be created
    events = db_session.query(RevenueEvent).all()
    assert len(events) == 0


def test_calculate_mrr_snapshot_existing(db_session):
    """Test that existing snapshots are not duplicated."""
    # Create existing snapshot
    snapshot_date = datetime(2026, 1, 15, 0, 0, 0, tzinfo=UTC)
    existing = MRRSnapshot(
        date=snapshot_date,
        total_mrr=1000.0,
        new_mrr=100.0,
        expansion_mrr=50.0,
        contraction_mrr=25.0,
        churned_mrr=10.0
    )
    db_session.add(existing)
    db_session.commit()
    
    ingestion = StripeIngestion(db_session)
    
    # Try to create snapshot for same date
    snapshot = ingestion.calculate_daily_mrr_snapshot(snapshot_date)
    
    # Should return existing snapshot
    assert snapshot.id == existing.id
    assert snapshot.total_mrr == 1000.0
    
    # Should not create duplicate
    snapshots = db_session.query(MRRSnapshot).all()
    assert len(snapshots) == 1


def test_calculate_mrr_snapshot_with_events(db_session):
    """Test MRR snapshot calculation with various events."""
    # Create subscriptions
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    # Active subscription
    sub1 = Subscription(
        stripe_subscription_id="sub_1",
        customer_id="cus_1",
        plan_id=plan.id,
        status="active",
        mrr=99.0
    )
    db_session.add(sub1)
    
    # Another active subscription
    sub2 = Subscription(
        stripe_subscription_id="sub_2",
        customer_id="cus_2",
        plan_id=plan.id,
        status="active",
        mrr=99.0
    )
    db_session.add(sub2)
    db_session.flush()
    
    # Create events for today
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # New subscription
    event1 = RevenueEvent(
        subscription_id=sub1.id,
        event_type=RevenueEventType.SUBSCRIPTION_CREATED,
        stripe_event_id="evt_1",
        mrr_delta=99.0,
        occurred_at=today + timedelta(hours=10)
    )
    db_session.add(event1)
    
    # Upgrade
    event2 = RevenueEvent(
        subscription_id=sub2.id,
        event_type=RevenueEventType.SUBSCRIPTION_UPGRADED,
        stripe_event_id="evt_2",
        mrr_delta=50.0,
        occurred_at=today + timedelta(hours=11)
    )
    db_session.add(event2)
    
    # Downgrade
    event3 = RevenueEvent(
        subscription_id=sub2.id,
        event_type=RevenueEventType.SUBSCRIPTION_DOWNGRADED,
        stripe_event_id="evt_3",
        mrr_delta=-20.0,
        occurred_at=today + timedelta(hours=12)
    )
    db_session.add(event3)
    
    # Cancellation
    event4 = RevenueEvent(
        subscription_id=sub1.id,
        event_type=RevenueEventType.SUBSCRIPTION_CANCELED,
        stripe_event_id="evt_4",
        mrr_delta=-99.0,
        occurred_at=today + timedelta(hours=13)
    )
    db_session.add(event4)
    db_session.commit()
    
    ingestion = StripeIngestion(db_session)
    snapshot = ingestion.calculate_daily_mrr_snapshot(today)
    
    # Verify snapshot
    assert snapshot.total_mrr == 198.0  # Both subs active
    assert snapshot.new_mrr == 99.0
    assert snapshot.expansion_mrr == 50.0
    assert snapshot.contraction_mrr == 20.0
    assert snapshot.churned_mrr == 99.0


def test_subscription_created_no_plan(db_session):
    """Test subscription created event with unknown plan."""
    ingestion = StripeIngestion(db_session)
    
    # Event with unknown price ID
    event_data = {
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_test",
                "customer": "cus_test",
                "status": "active",
                "current_period_start": int(datetime.now(UTC).timestamp()),
                "current_period_end": int((datetime.now(UTC) + timedelta(days=30)).timestamp()),
                "items": {
                    "data": [
                        {
                            "price": {
                                "id": "price_unknown",
                                "unit_amount": 2900,
                                "recurring": {"interval": "month"}
                            },
                            "quantity": 1
                        }
                    ]
                }
            }
        }
    }
    
    # Should handle gracefully (log warning but not crash)
    ingestion.process_webhook_event(event_data)
    
    # No subscription should be created
    subscriptions = db_session.query(Subscription).all()
    assert len(subscriptions) == 0


def test_subscription_deleted_nonexistent(db_session):
    """Test deletion event for non-existent subscription."""
    ingestion = StripeIngestion(db_session)
    
    # Delete event for non-existent subscription
    event_data = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_nonexistent",
                "customer": "cus_test",
                "status": "canceled"
            }
        }
    }
    
    # Should handle gracefully
    ingestion.process_webhook_event(event_data)
    
    # No error should be raised
    assert True
