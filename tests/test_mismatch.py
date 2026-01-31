"""Tests for mismatch detection."""

import pytest
from datetime import datetime, timedelta
from monetization_engine.models import Product, Plan, Subscription, UsageRecord
from monetization_engine.analysis import MismatchDetector


def test_high_usage_detection(db_session):
    """Test detection of high usage customers."""
    # Create test data
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        limits={"api_calls": 1000},
        effective_from=datetime.utcnow()
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=29.0,
        current_period_start=datetime.utcnow() - timedelta(days=15),
        current_period_end=datetime.utcnow() + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # High usage - 90% of limit
    usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=900,
        limit=1000,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end
    )
    db_session.add(usage)
    db_session.commit()
    
    # Run detection
    detector = MismatchDetector(db_session)
    results = detector.analyze_all_subscriptions()
    
    # Should identify as upgrade candidate
    assert len(results['upgrade_candidates']) == 1
    assert results['upgrade_candidates'][0]['customer_id'] == 'cus_test'


def test_low_usage_detection(db_session):
    """Test detection of low usage customers."""
    # Similar setup but with low usage
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Enterprise",
        price_monthly=299.0,
        limits={"api_calls": 100000},
        effective_from=datetime.utcnow()
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=299.0,
        current_period_start=datetime.utcnow() - timedelta(days=15),
        current_period_end=datetime.utcnow() + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Low usage - only 5% of limit
    usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=5000,
        limit=100000,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end
    )
    db_session.add(usage)
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    results = detector.analyze_all_subscriptions()
    
    # Should identify as overpriced
    assert len(results['overpriced_customers']) == 1
    assert results['overpriced_customers'][0]['customer_id'] == 'cus_test'
