"""Tests for mismatch detection."""

import pytest
from datetime import datetime, timedelta, UTC
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
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=29.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
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


def test_appropriate_usage(db_session):
    """Test subscription with appropriate usage level."""
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
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Appropriate usage - 50% of limit
    usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=5000,
        limit=10000,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end
    )
    db_session.add(usage)
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    results = detector.analyze_all_subscriptions()
    
    # Should not flag as mismatch
    assert len(results['upgrade_candidates']) == 0
    assert len(results['overpriced_customers']) == 0


def test_no_usage_data(db_session):
    """Test subscription with no usage data."""
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
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    results = detector.analyze_all_subscriptions()
    
    # Should handle gracefully
    assert len(results['upgrade_candidates']) == 0
    assert len(results['overpriced_customers']) == 0


def test_multiple_metrics_utilization(db_session):
    """Test utilization calculation with multiple metrics."""
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
    
    # High usage on api_calls (90%)
    usage1 = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=9000,
        limit=10000,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end
    )
    db_session.add(usage1)
    
    # Low usage on storage (10%)
    usage2 = UsageRecord(
        subscription_id=subscription.id,
        metric_name="storage_gb",
        quantity=10,
        limit=100,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end
    )
    db_session.add(usage2)
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    results = detector.analyze_all_subscriptions()
    
    # Average utilization is 50% (0.9 + 0.1) / 2, should be appropriate
    assert len(results['upgrade_candidates']) == 0
    assert len(results['overpriced_customers']) == 0


def test_suggest_upgrade_recommendation(db_session):
    """Test upgrade suggestion with available higher tier."""
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    # Create plan hierarchy
    starter = Plan(
        product_id=product.id,
        name="Starter",
        price_monthly=29.0,
        limits={"api_calls": 1000},
        effective_from=datetime.now(UTC)
    )
    db_session.add(starter)
    
    pro = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=99.0,
        limits={"api_calls": 10000},
        effective_from=datetime.now(UTC)
    )
    db_session.add(pro)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=starter.id,
        status="active",
        mrr=29.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # High usage
    usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=950,
        limit=1000,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end
    )
    db_session.add(usage)
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    results = detector.analyze_all_subscriptions()
    
    # Should suggest Pro plan
    assert len(results['upgrade_candidates']) == 1
    recommendation = results['upgrade_candidates'][0]['recommendation']
    assert "Upgrade" in recommendation or "high usage" in recommendation


def test_no_higher_tier_available(db_session):
    """Test upgrade suggestion when already on highest tier."""
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    # Only one plan (highest tier)
    enterprise = Plan(
        product_id=product.id,
        name="Enterprise",
        price_monthly=999.0,
        limits={"api_calls": 1000000},
        effective_from=datetime.now(UTC)
    )
    db_session.add(enterprise)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=enterprise.id,
        status="active",
        mrr=999.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # High usage even on enterprise
    usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=950000,
        limit=1000000,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end
    )
    db_session.add(usage)
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    results = detector.analyze_all_subscriptions()
    
    # Should still detect but recommend custom pricing
    assert len(results['upgrade_candidates']) == 1


def test_detect_feature_mispricing(db_session):
    """Test detection of mispriced features across customer base."""
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
    
    # Create multiple subscriptions with high usage (>80%)
    for i in range(10):
        sub = Subscription(
            stripe_subscription_id=f"sub_{i}",
            customer_id=f"cus_{i}",
            plan_id=plan.id,
            status="active",
            mrr=99.0,
            current_period_start=datetime.now(UTC) - timedelta(days=15),
            current_period_end=datetime.now(UTC) + timedelta(days=15)
        )
        db_session.add(sub)
        db_session.flush()
        
        # 8 out of 10 have high usage (80%+)
        if i < 8:
            quantity = 9000  # 90% usage
        else:
            quantity = 3000  # 30% usage
        
        usage = UsageRecord(
            subscription_id=sub.id,
            metric_name="api_calls",
            quantity=quantity,
            limit=10000,
            period_start=sub.current_period_start,
            period_end=sub.current_period_end
        )
        db_session.add(usage)
    
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    mispricing = detector.detect_feature_mispricing()
    
    # Should detect that limits are too low (>50% hitting limits)
    assert len(mispricing) == 1
    assert mispricing[0]['plan_name'] == "Pro"
    assert mispricing[0]['high_usage_percentage'] >= 50


def test_alert_deduplication(db_session):
    """Test that duplicate alerts are not created."""
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
        mrr=29.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # High usage
    usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=950,
        limit=1000,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end
    )
    db_session.add(usage)
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    
    # Run analysis twice
    results1 = detector.analyze_all_subscriptions()
    results2 = detector.analyze_all_subscriptions()
    
    # Should only create one alert
    from monetization_engine.models import Alert
    alerts = db_session.query(Alert).filter(
        Alert.customer_id == "cus_test"
    ).all()
    
    assert len(alerts) == 1


def test_usage_without_limit(db_session):
    """Test handling of usage records without limits."""
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
    db_session.flush()
    
    # Usage without limit
    usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=100000,
        limit=None,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end
    )
    db_session.add(usage)
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    results = detector.analyze_all_subscriptions()
    
    # Should handle gracefully (no limit = can't calculate utilization)
    assert len(results['upgrade_candidates']) == 0
    assert len(results['overpriced_customers']) == 0


def test_inactive_subscriptions_ignored(db_session):
    """Test that inactive subscriptions are not analyzed."""
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
    
    # Canceled subscription
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="canceled",
        mrr=0.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    results = detector.analyze_all_subscriptions()
    
    # Should not analyze canceled subscriptions
    assert len(results['upgrade_candidates']) == 0
    assert len(results['overpriced_customers']) == 0


def test_feature_mispricing_no_subscriptions(db_session):
    """Test feature mispricing detection with no active subscriptions."""
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
    db_session.commit()
    
    detector = MismatchDetector(db_session)
    mispricing = detector.detect_feature_mispricing()
    
    # Should return empty list
    assert len(mispricing) == 0
