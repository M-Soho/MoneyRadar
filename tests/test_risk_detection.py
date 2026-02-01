"""Tests for risk detection."""

import pytest
from datetime import datetime, timedelta, UTC
from monetization_engine.models import (
    Product, Plan, Subscription, UsageRecord, 
    RevenueEvent, RevenueEventType, MRRSnapshot, Alert
)
from monetization_engine.analysis import RiskDetector, ExpansionScorer


def test_detect_declining_usage(db_session):
    """Test detection of declining usage patterns."""
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
        current_period_start=datetime.now(UTC) - timedelta(days=30),
        current_period_end=datetime.now(UTC) + timedelta(days=30),
        created_at=datetime.now(UTC) - timedelta(days=60)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create declining usage pattern
    base_date = datetime.now(UTC) - timedelta(days=30)
    for i in range(10):
        usage = UsageRecord(
            subscription_id=subscription.id,
            metric_name="api_calls",
            quantity=1000 - (i * 50),  # Declining usage
            limit=1000,
            period_start=base_date + timedelta(days=i*3),
            period_end=base_date + timedelta(days=i*3+3),
            recorded_at=base_date + timedelta(days=i*3)
        )
        db_session.add(usage)
    
    db_session.commit()
    
    # Run detection
    detector = RiskDetector(db_session)
    alerts = detector.detect_declining_usage()
    
    assert len(alerts) > 0
    assert alerts[0].customer_id == "cus_test"


def test_detect_payment_issues(db_session):
    """Test detection of payment issues."""
    # Create test data
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
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create payment failure event
    event = RevenueEvent(
        subscription_id=subscription.id,
        event_type=RevenueEventType.PAYMENT_FAILED,
        stripe_event_id="evt_test",
        amount=99.0,
        occurred_at=datetime.now(UTC),
        event_metadata={"attempt_count": 3}
    )
    db_session.add(event)
    db_session.commit()
    
    # Run detection
    detector = RiskDetector(db_session)
    alerts = detector.detect_payment_issues()
    
    assert len(alerts) > 0
    assert alerts[0].customer_id == "cus_test"


def test_expansion_scorer(db_session):
    """Test expansion readiness scoring."""
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
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=200)  # Good tenure
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create growing usage pattern
    base_date = datetime.now(UTC) - timedelta(days=30)
    for i in range(10):
        usage = UsageRecord(
            subscription_id=subscription.id,
            metric_name="api_calls",
            quantity=500 + (i * 30),  # Growing usage
            limit=1000,
            period_start=base_date + timedelta(days=i*3),
            period_end=base_date + timedelta(days=i*3+3),
            recorded_at=base_date + timedelta(days=i*3)
        )
        db_session.add(usage)
    
    db_session.commit()
    
    # Score customer
    scorer = ExpansionScorer(db_session)
    score = scorer.score_customer("cus_test")
    
    assert score.expansion_score > 0
    assert score.expansion_category in ["safe_to_upsell", "neutral", "do_not_touch", "likely_to_churn"]
    assert score.tenure_days >= 200


def test_detect_downgrades(db_session):
    """Test detection of plan downgrades."""
    # Create test data
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
        mrr=29.0,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create downgrade event
    event = RevenueEvent(
        subscription_id=subscription.id,
        event_type=RevenueEventType.SUBSCRIPTION_DOWNGRADED,
        stripe_event_id="evt_test",
        amount=29.0,
        mrr_delta=-70.0,  # Downgraded from $99 to $29
        occurred_at=datetime.now(UTC) - timedelta(days=2)
    )
    db_session.add(event)
    db_session.commit()
    
    # Run detection
    detector = RiskDetector(db_session)
    alerts = detector.detect_downgrades()
    
    assert len(alerts) > 0
    assert alerts[0].customer_id == "cus_test"
    assert "downgrade" in alerts[0].title.lower()


def test_detect_mrr_decline(db_session):
    """Test detection of overall MRR decline."""
    # Create MRR snapshots showing decline
    # Earlier snapshot (older date, first in desc order will be latest chronologically)
    snapshot1 = MRRSnapshot(
        date=datetime.now(UTC) - timedelta(days=6),
        total_mrr=10000.0,
        new_mrr=500.0,
        expansion_mrr=200.0,
        contraction_mrr=100.0,
        churned_mrr=150.0
    )
    db_session.add(snapshot1)
    
    # Recent snapshot with significantly lower MRR (20% decline to exceed 15% threshold)
    snapshot2 = MRRSnapshot(
        date=datetime.now(UTC),
        total_mrr=8000.0,  # 20% decline from 10000
        new_mrr=300.0,
        expansion_mrr=100.0,
        contraction_mrr=200.0,
        churned_mrr=800.0
    )
    db_session.add(snapshot2)
    db_session.commit()
    
    # Run detection
    detector = RiskDetector(db_session)
    alerts = detector.detect_mrr_decline(lookback_days=7)
    
    assert len(alerts) > 0
    assert "mrr" in alerts[0].title.lower()


def test_scan_all_risks(db_session):
    """Test comprehensive risk scan."""
    # Create subscription with multiple risk factors
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
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Add payment failure
    event = RevenueEvent(
        subscription_id=subscription.id,
        event_type=RevenueEventType.PAYMENT_FAILED,
        stripe_event_id="evt_test",
        amount=99.0,
        occurred_at=datetime.now(UTC),
        event_metadata={"attempt_count": 2}
    )
    db_session.add(event)
    db_session.commit()
    
    # Run comprehensive scan
    detector = RiskDetector(db_session)
    results = detector.scan_all_risks()
    
    assert "critical" in results
    assert "warning" in results
    assert "informational" in results
    assert isinstance(results["critical"], list)
    assert isinstance(results["warning"], list)


def test_no_duplicate_alerts(db_session):
    """Test that duplicate alerts are not created."""
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
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create payment failure
    event = RevenueEvent(
        subscription_id=subscription.id,
        event_type=RevenueEventType.PAYMENT_FAILED,
        stripe_event_id="evt_test",
        amount=99.0,
        occurred_at=datetime.now(UTC),
        event_metadata={"attempt_count": 2}
    )
    db_session.add(event)
    db_session.commit()
    
    # Run detection twice
    detector = RiskDetector(db_session)
    alerts1 = detector.detect_payment_issues()
    alerts2 = detector.detect_payment_issues()
    
    # Second run should not create duplicates
    assert len(alerts1) > 0
    assert len(alerts2) == 0


def test_expansion_scorer_inactive_subscription(db_session):
    """Test expansion scorer with inactive subscription."""
    scorer = ExpansionScorer(db_session)
    
    # Should raise error for non-existent customer
    with pytest.raises(ValueError):
        scorer.score_customer("cus_nonexistent")

