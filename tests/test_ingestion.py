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
