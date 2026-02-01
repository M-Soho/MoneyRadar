"""Tests for risk detection."""

import pytest
from datetime import datetime, timedelta
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
        current_period_start=datetime.utcnow() - timedelta(days=30),
        current_period_end=datetime.utcnow() + timedelta(days=30),
        created_at=datetime.utcnow() - timedelta(days=60)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create declining usage pattern
    base_date = datetime.utcnow() - timedelta(days=30)
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
        effective_from=datetime.utcnow()
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create payment failure event
    event = RevenueEvent(
        subscription_id=subscription.id,
        event_type=RevenueEventType.PAYMENT_FAILED,
        stripe_event_id="evt_test",
        amount=99.0,
        occurred_at=datetime.utcnow(),
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
        current_period_end=datetime.utcnow() + timedelta(days=15),
        created_at=datetime.utcnow() - timedelta(days=200)  # Good tenure
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create growing usage pattern
    base_date = datetime.utcnow() - timedelta(days=30)
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
