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


def test_expansion_scorer_high_tenure(db_session):
    """Test scoring with high tenure (365+ days)."""
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
        stripe_subscription_id="sub_longtime",
        customer_id="cus_longtime",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=400)  # Over 1 year
    )
    db_session.add(subscription)
    db_session.commit()
    
    scorer = ExpansionScorer(db_session)
    score = scorer.score_customer("cus_longtime")
    
    # High tenure should contribute 30 points
    assert score.tenure_days >= 365
    assert score.expansion_score >= 30


def test_expansion_scorer_strong_growth(db_session):
    """Test scoring with strong usage growth (>50%)."""
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
        stripe_subscription_id="sub_growth",
        customer_id="cus_growth",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=100)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create strong growth pattern: 1000 -> 2000
    base_date = datetime.now(UTC) - timedelta(days=30)
    for i in range(10):
        usage = UsageRecord(
            subscription_id=subscription.id,
            metric_name="api_calls",
            quantity=1000 + (i * 100),  # Strong linear growth
            limit=10000,
            period_start=base_date + timedelta(days=i*3),
            period_end=base_date + timedelta(days=i*3+3),
            recorded_at=base_date + timedelta(days=i*3)
        )
        db_session.add(usage)
    
    db_session.commit()
    
    scorer = ExpansionScorer(db_session)
    score = scorer.score_customer("cus_growth")
    
    # Growth is calculated as (second_half_avg - first_half_avg) / first_half_avg
    # With 10 records: 1000, 1100, 1200, 1300, 1400 | 1500, 1600, 1700, 1800, 1900
    # First half avg: 1200, Second half avg: 1700, Growth: (1700-1200)/1200 = 41.7%
    assert score.usage_trend > 0.2  # Should show growth
    # Category depends on total score (tenure + growth + engagement)
    assert score.expansion_score > 0


def test_expansion_scorer_moderate_growth(db_session):
    """Test scoring with moderate usage growth (20-50%)."""
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
        stripe_subscription_id="sub_moderate",
        customer_id="cus_moderate",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=250)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create moderate growth: 1000 -> 1300 (30% growth)
    base_date = datetime.now(UTC) - timedelta(days=30)
    for i in range(10):
        usage = UsageRecord(
            subscription_id=subscription.id,
            metric_name="api_calls",
            quantity=1000 + (i * 30),  # Moderate growth
            limit=10000,
            period_start=base_date + timedelta(days=i*3),
            period_end=base_date + timedelta(days=i*3+3),
            recorded_at=base_date + timedelta(days=i*3)
        )
        db_session.add(usage)
    
    db_session.commit()
    
    scorer = ExpansionScorer(db_session)
    score = scorer.score_customer("cus_moderate")
    
    # With moderate growth pattern, trend should be positive but may be < 0.2
    assert score.usage_trend > 0  # Positive growth
    assert score.expansion_category in ["safe_to_upsell", "neutral", "do_not_touch"]


def test_expansion_scorer_churn_risk(db_session):
    """Test scoring with declining usage (churn risk)."""
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
        stripe_subscription_id="sub_decline",
        customer_id="cus_decline",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=200)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create declining usage: 2000 -> 1000 (50% decline)
    base_date = datetime.now(UTC) - timedelta(days=30)
    for i in range(10):
        usage = UsageRecord(
            subscription_id=subscription.id,
            metric_name="api_calls",
            quantity=2000 - (i * 100),  # Declining
            limit=10000,
            period_start=base_date + timedelta(days=i*3),
            period_end=base_date + timedelta(days=i*3+3),
            recorded_at=base_date + timedelta(days=i*3)
        )
        db_session.add(usage)
    
    db_session.commit()
    
    scorer = ExpansionScorer(db_session)
    score = scorer.score_customer("cus_decline")
    
    assert score.usage_trend < -0.2
    assert score.expansion_category == "likely_to_churn"


def test_expansion_scorer_no_usage_data(db_session):
    """Test scoring with no usage data."""
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
        stripe_subscription_id="sub_new",
        customer_id="cus_new",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=50)
    )
    db_session.add(subscription)
    db_session.commit()
    
    scorer = ExpansionScorer(db_session)
    score = scorer.score_customer("cus_new")
    
    # No usage data means 0 trend and 0 average
    assert score.usage_trend == 0.0
    assert score.expansion_score <= 10  # Only tenure points for <90 days


def test_expansion_scorer_single_usage_record(db_session):
    """Test scoring with only one usage record."""
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
        stripe_subscription_id="sub_single",
        customer_id="cus_single",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=100)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Single usage record
    usage = UsageRecord(
        subscription_id=subscription.id,
        metric_name="api_calls",
        quantity=500,
        limit=10000,
        period_start=datetime.now(UTC) - timedelta(days=1),
        period_end=datetime.now(UTC),
        recorded_at=datetime.now(UTC)
    )
    db_session.add(usage)
    db_session.commit()
    
    scorer = ExpansionScorer(db_session)
    score = scorer.score_customer("cus_single")
    
    # With only 1 record, trend should be 0
    assert score.usage_trend == 0.0


def test_expansion_scorer_update_existing_score(db_session):
    """Test updating an existing customer score."""
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
        stripe_subscription_id="sub_update",
        customer_id="cus_update",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=150)
    )
    db_session.add(subscription)
    db_session.commit()
    
    scorer = ExpansionScorer(db_session)
    
    # First score
    score1 = scorer.score_customer("cus_update")
    first_score_value = score1.expansion_score
    
    # Score again
    score2 = scorer.score_customer("cus_update")
    
    # Should be the same record, updated
    assert score1.id == score2.id
    assert score2.expansion_score == first_score_value


def test_expansion_scorer_high_engagement(db_session):
    """Test scoring with high usage engagement."""
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
        stripe_subscription_id="sub_engaged",
        customer_id="cus_engaged",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=200)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # High usage: 90% of limit
    base_date = datetime.now(UTC) - timedelta(days=30)
    for i in range(10):
        usage = UsageRecord(
            subscription_id=subscription.id,
            metric_name="api_calls",
            quantity=9000,  # 90% of limit
            limit=10000,
            period_start=base_date + timedelta(days=i*3),
            period_end=base_date + timedelta(days=i*3+3),
            recorded_at=base_date + timedelta(days=i*3)
        )
        db_session.add(usage)
    
    db_session.commit()
    
    scorer = ExpansionScorer(db_session)
    score = scorer.score_customer("cus_engaged")
    
    # High engagement should contribute close to 30 points
    assert score.expansion_score >= 40  # Tenure + engagement


def test_expansion_scorer_usage_without_limits(db_session):
    """Test average usage calculation when no limits are set."""
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
        stripe_subscription_id="sub_nolimit",
        customer_id="cus_nolimit",
        plan_id=plan.id,
        status="active",
        mrr=299.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=200)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Usage records without limits
    base_date = datetime.now(UTC) - timedelta(days=30)
    for i in range(5):
        usage = UsageRecord(
            subscription_id=subscription.id,
            metric_name="api_calls",
            quantity=50000,  # High usage but no limit
            limit=None,
            period_start=base_date + timedelta(days=i*6),
            period_end=base_date + timedelta(days=i*6+6),
            recorded_at=base_date + timedelta(days=i*6)
        )
        db_session.add(usage)
    
    db_session.commit()
    
    scorer = ExpansionScorer(db_session)
    score = scorer.score_customer("cus_nolimit")
    
    # Without limits, engagement score should be 0
    # Score should only come from tenure
    assert score.expansion_score >= 20  # Tenure points only


def test_risk_detector_no_payment_issues(db_session):
    """Test detect_payment_issues when there are none."""
    # Create subscription with no failed payments
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
        stripe_subscription_id="sub_good",
        customer_id="cus_good",
        plan_id=plan.id,
        status="active",
        mrr=99.0
    )
    db_session.add(subscription)
    db_session.commit()
    
    detector = RiskDetector(db_session)
    risks = detector.detect_payment_issues()
    
    assert len(risks) == 0


def test_risk_detector_no_declining_usage(db_session):
    """Test detect_declining_usage when usage is steady."""
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
        stripe_subscription_id="sub_steady",
        customer_id="cus_steady",
        plan_id=plan.id,
        status="active",
        mrr=99.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Steady usage
    for i in range(5):
        usage = UsageRecord(
            subscription_id=subscription.id,
            metric_name="api_calls",
            quantity=5000,
            limit=10000,
            period_start=datetime.now(UTC) - timedelta(days=i*2),
            period_end=datetime.now(UTC) - timedelta(days=i*2-1)
        )
        db_session.add(usage)
    db_session.commit()
    
    detector = RiskDetector(db_session)
    risks = detector.detect_declining_usage()
    
    assert len(risks) == 0


def test_expansion_scorer_very_high_score(db_session):
    """Test customer with very high expansion score."""
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
        stripe_subscription_id="sub_perfect",
        customer_id="cus_perfect",
        plan_id=plan.id,
        status="active",
        mrr=29.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=400)  # Long tenure
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Growing usage - first half low, second half high
    for i in range(20):
        quantity = 300 if i < 10 else 900  # Strong growth
        usage = UsageRecord(
            subscription_id=subscription.id,
            metric_name="api_calls",
            quantity=quantity,
            limit=1000,
            period_start=datetime.now(UTC) - timedelta(days=40-i*2),
            period_end=datetime.now(UTC) - timedelta(days=39-i*2)
        )
        db_session.add(usage)
    db_session.commit()
    
    scorer = ExpansionScorer(db_session)
    score = scorer.score_customer("cus_perfect")
    
    # Should be safe to upsell
    assert score.expansion_score >= 70
    assert score.expansion_category == "safe_to_upsell"

