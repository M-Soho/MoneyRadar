"""Tests for experiment tracking and reporting."""

import pytest
from datetime import datetime, timedelta, UTC
from monetization_engine.models import (
    Product, Plan, Subscription, Experiment, ExperimentStatus
)
from monetization_engine.experiments import ExperimentTracker, ExperimentReporter


def test_create_experiment(db_session):
    """Test creating a new experiment."""
    tracker = ExperimentTracker(db_session)
    
    experiment = tracker.create_experiment(
        name="Test Price Increase",
        hypothesis="Raising price will increase ARPU without affecting churn",
        change_description="Increase Pro plan from $49 to $59",
        metric_tracked="arpu",
        affected_segment={"plan_id": 1}
    )
    
    assert experiment.id is not None
    assert experiment.name == "Test Price Increase"
    assert experiment.status == ExperimentStatus.DRAFT


def test_start_experiment(db_session):
    """Test starting an experiment."""
    # Create test data
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=49.0,
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=49.0,
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30)
    )
    db_session.add(subscription)
    db_session.commit()
    
    # Create and start experiment
    tracker = ExperimentTracker(db_session)
    experiment = tracker.create_experiment(
        name="Test Experiment",
        hypothesis="Test hypothesis",
        change_description="Test change",
        metric_tracked="arpu",
        affected_segment={"plan_id": plan.id}
    )
    
    started_exp = tracker.start_experiment(experiment.id)
    
    assert started_exp.status == ExperimentStatus.RUNNING
    assert started_exp.baseline_value is not None
    assert started_exp.started_at is not None


def test_experiment_reporter(db_session):
    """Test experiment reporting."""
    # Create a completed experiment
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=49.0,
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    experiment = Experiment(
        name="Price Test",
        hypothesis="Test",
        change_description="Increase price",
        metric_tracked="arpu",
        affected_segment={"plan_id": plan.id},
        status=ExperimentStatus.COMPLETED,
        baseline_value=100.0,
        actual_value=110.0,
        outcome="Positive result",
        started_at=datetime.now(UTC) - timedelta(days=30),
        ended_at=datetime.now(UTC)
    )
    db_session.add(experiment)
    db_session.commit()
    
    # Generate report
    reporter = ExperimentReporter(db_session)
    report = reporter.generate_summary_report(experiment.id)
    
    assert report["experiment_id"] == experiment.id
    assert report["name"] == "Price Test"
    assert report["improvement_percent"] == 10.0
    assert report["status"] == "completed"


def test_get_learnings(db_session):
    """Test getting learnings from experiments."""
    # Create multiple completed experiments
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=49.0,
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    for i in range(3):
        experiment = Experiment(
            name=f"Experiment {i}",
            hypothesis="Test",
            change_description=f"Change {i}",
            metric_tracked="arpu",
            affected_segment={"plan_id": plan.id},
            status=ExperimentStatus.COMPLETED,
            baseline_value=100.0,
            actual_value=100.0 + (i * 5),
            outcome=f"Result {i}",
            started_at=datetime.now(UTC) - timedelta(days=30 + i),
            ended_at=datetime.now(UTC) - timedelta(days=i)
        )
        db_session.add(experiment)
    
    db_session.commit()
    
    reporter = ExperimentReporter(db_session)
    learnings = reporter.get_learnings()
    
    assert len(learnings) == 3
    assert all("improvement_percent" in learning for learning in learnings)


def test_start_experiment_not_found(db_session):
    """Test starting non-existent experiment raises error."""
    tracker = ExperimentTracker(db_session)
    
    with pytest.raises(ValueError, match="Experiment 999 not found"):
        tracker.start_experiment(999)


def test_start_experiment_invalid_status(db_session):
    """Test starting experiment that's not in DRAFT status."""
    tracker = ExperimentTracker(db_session)
    
    # Create experiment already running
    experiment = Experiment(
        name="Running Experiment",
        hypothesis="Test",
        change_description="Test",
        metric_tracked="arpu",
        affected_segment={"plan_id": 1},
        status=ExperimentStatus.RUNNING
    )
    db_session.add(experiment)
    db_session.commit()
    
    with pytest.raises(ValueError, match="must be in DRAFT status"):
        tracker.start_experiment(experiment.id)


def test_record_result_not_found(db_session):
    """Test recording result for non-existent experiment."""
    tracker = ExperimentTracker(db_session)
    
    with pytest.raises(ValueError, match="Experiment 999 not found"):
        tracker.record_result(999, 120.0, "Success")


def test_record_result_success(db_session):
    """Test successfully recording experiment results."""
    tracker = ExperimentTracker(db_session)
    
    # Create experiment
    experiment = tracker.create_experiment(
        name="Test Experiment",
        hypothesis="Test",
        change_description="Test",
        metric_tracked="arpu",
        affected_segment={"plan_id": 1},
        baseline_value=100.0
    )
    
    # Record result
    updated = tracker.record_result(experiment.id, 115.0, "Positive - 15% increase")
    
    assert updated.actual_value == 115.0
    assert updated.outcome == "Positive - 15% increase"
    assert updated.status == ExperimentStatus.COMPLETED
    assert updated.ended_at is not None


def test_calculate_metric_arpu(db_session):
    """Test ARPU calculation with multiple subscriptions."""
    # Create test data
    product = Product(name="Test Product", stripe_product_id="prod_test")
    db_session.add(product)
    db_session.flush()
    
    plan = Plan(
        product_id=product.id,
        name="Pro",
        price_monthly=50.0,
        effective_from=datetime.now(UTC)
    )
    db_session.add(plan)
    db_session.flush()
    
    # Create 3 subscriptions
    for i in range(3):
        sub = Subscription(
            stripe_subscription_id=f"sub_{i}",
            customer_id=f"cus_{i}",
            plan_id=plan.id,
            status="active",
            mrr=50.0 + (i * 10),
            current_period_start=datetime.now(UTC),
            current_period_end=datetime.now(UTC) + timedelta(days=30)
        )
        db_session.add(sub)
    db_session.commit()
    
    tracker = ExperimentTracker(db_session)
    arpu = tracker._calculate_metric("arpu", {"plan_id": plan.id})
    
    # ARPU = (50 + 60 + 70) / 3 = 60.0
    assert arpu == 60.0


def test_calculate_metric_mrr(db_session):
    """Test MRR calculation."""
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
    
    # Create subscriptions
    for i in range(5):
        sub = Subscription(
            stripe_subscription_id=f"sub_{i}",
            customer_id=f"cus_{i}",
            plan_id=plan.id,
            status="active",
            mrr=99.0
        )
        db_session.add(sub)
    db_session.commit()
    
    tracker = ExperimentTracker(db_session)
    mrr = tracker._calculate_metric("mrr", {"plan_id": plan.id})
    
    assert mrr == 495.0  # 99 * 5


def test_calculate_metric_churn_rate(db_session):
    """Test churn rate calculation with canceled subscriptions."""
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
    
    # Create active subscriptions
    for i in range(8):
        sub = Subscription(
            stripe_subscription_id=f"sub_active_{i}",
            customer_id=f"cus_active_{i}",
            plan_id=plan.id,
            status="active",
            mrr=99.0
        )
        db_session.add(sub)
    
    # Create canceled subscriptions (last 30 days)
    for i in range(2):
        sub = Subscription(
            stripe_subscription_id=f"sub_canceled_{i}",
            customer_id=f"cus_canceled_{i}",
            plan_id=plan.id,
            status="canceled",
            mrr=0.0,
            canceled_at=datetime.now(UTC) - timedelta(days=10)
        )
        db_session.add(sub)
    
    db_session.commit()
    
    tracker = ExperimentTracker(db_session)
    churn_rate = tracker._calculate_metric("churn_rate", {"plan_id": plan.id})
    
    # Churn rate = 2 churned / 8 active = 0.25 = 25%
    assert churn_rate == 25.0


def test_calculate_metric_conversion_rate(db_session):
    """Test conversion rate calculation (currently returns 0.0)."""
    tracker = ExperimentTracker(db_session)
    
    # Conversion rate not yet implemented, should return 0.0
    conversion = tracker._calculate_metric("conversion_rate", {"plan_id": 1})
    assert conversion == 0.0


def test_calculate_metric_unknown(db_session):
    """Test unknown metric returns 0.0."""
    tracker = ExperimentTracker(db_session)
    
    unknown = tracker._calculate_metric("unknown_metric", {"plan_id": 1})
    assert unknown == 0.0


def test_calculate_metric_empty_segment(db_session):
    """Test metric calculation with no subscriptions."""
    tracker = ExperimentTracker(db_session)
    
    # No subscriptions exist
    arpu = tracker._calculate_metric("arpu", {"plan_id": 999})
    assert arpu == 0.0


def test_count_affected_customers(db_session):
    """Test control/variant split calculation."""
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
    
    # Create 10 subscriptions
    for i in range(10):
        sub = Subscription(
            stripe_subscription_id=f"sub_{i}",
            customer_id=f"cus_{i}",
            plan_id=plan.id,
            status="active",
            mrr=99.0
        )
        db_session.add(sub)
    db_session.commit()
    
    tracker = ExperimentTracker(db_session)
    control, variant = tracker._count_affected_customers({"plan_id": plan.id})
    
    # 50/50 split
    assert control == 5
    assert variant == 5


def test_analyze_experiment_with_target_met(db_session):
    """Test experiment analysis when target is met."""
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
    
    # Create subscriptions with average MRR of 115 (higher than target)
    for i in range(3):
        sub = Subscription(
            stripe_subscription_id=f"sub_{i}",
            customer_id=f"cus_{i}",
            plan_id=plan.id,
            status="active",
            mrr=115.0
        )
        db_session.add(sub)
    db_session.flush()
    
    experiment = Experiment(
        name="Price Test",
        hypothesis="Test",
        change_description="Increase price",
        metric_tracked="arpu",
        affected_segment={"plan_id": plan.id},
        status=ExperimentStatus.COMPLETED,
        baseline_value=100.0,
        target_value=110.0,
        actual_value=115.0,
        started_at=datetime.now() - timedelta(days=30),
        ended_at=datetime.now()
    )
    db_session.add(experiment)
    db_session.commit()
    
    tracker = ExperimentTracker(db_session)
    analysis = tracker.analyze_experiment(experiment.id)
    
    assert analysis["target_met"] is True
    assert analysis["improvement_percent"] == 15.0


def test_analyze_experiment_target_not_met(db_session):
    """Test experiment analysis when target is not met."""
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
    
    # Create subscriptions with average MRR of 105 (higher than baseline but below target)
    for i in range(2):
        sub = Subscription(
            stripe_subscription_id=f"sub_{i}",
            customer_id=f"cus_{i}",
            plan_id=plan.id,
            status="active",
            mrr=105.0
        )
        db_session.add(sub)
    db_session.flush()
    
    experiment = Experiment(
        name="Price Test",
        hypothesis="Test",
        change_description="Increase price",
        metric_tracked="arpu",
        affected_segment={"plan_id": plan.id},
        status=ExperimentStatus.COMPLETED,
        baseline_value=100.0,
        target_value=120.0,
        actual_value=105.0,
        started_at=datetime.now() - timedelta(days=30),
        ended_at=datetime.now()
    )
    db_session.add(experiment)
    db_session.commit()
    
    tracker = ExperimentTracker(db_session)
    analysis = tracker.analyze_experiment(experiment.id)
    
    assert analysis["target_met"] is False
    assert analysis["improvement_percent"] == 5.0


def test_analyze_experiment_not_ready(db_session):
    """Test analysis for DRAFT experiment returns not ready."""
    experiment = Experiment(
        name="Draft Experiment",
        hypothesis="Test",
        change_description="Test",
        metric_tracked="arpu",
        affected_segment={"plan_id": 1},
        status=ExperimentStatus.DRAFT
    )
    db_session.add(experiment)
    db_session.commit()
    
    tracker = ExperimentTracker(db_session)
    analysis = tracker.analyze_experiment(experiment.id)
    
    assert analysis["status"] == "not_ready"


def test_get_active_experiments(db_session):
    """Test fetching only running experiments."""
    # Create experiments with different statuses
    statuses = [ExperimentStatus.DRAFT, ExperimentStatus.RUNNING, ExperimentStatus.RUNNING, ExperimentStatus.COMPLETED]
    
    for i, status in enumerate(statuses):
        exp = Experiment(
            name=f"Experiment {i}",
            hypothesis="Test",
            change_description="Test",
            metric_tracked="arpu",
            affected_segment={"plan_id": 1},
            status=status
        )
        db_session.add(exp)
    db_session.commit()
    
    tracker = ExperimentTracker(db_session)
    active = tracker.get_active_experiments()
    
    # Only 2 running experiments
    assert len(active) == 2
    assert all(exp.status == ExperimentStatus.RUNNING for exp in active)


def test_get_experiment_history_filtered(db_session):
    """Test filtering experiment history by metric."""
    # Create experiments with different metrics
    metrics = ["arpu", "arpu", "mrr", "churn_rate"]
    
    for i, metric in enumerate(metrics):
        exp = Experiment(
            name=f"Experiment {i}",
            hypothesis="Test",
            change_description="Test",
            metric_tracked=metric,
            affected_segment={"plan_id": 1},
            status=ExperimentStatus.COMPLETED
        )
        db_session.add(exp)
    db_session.commit()
    
    tracker = ExperimentTracker(db_session)
    history = tracker.get_experiment_history(metric="arpu")
    
    # Should only return ARPU experiments
    assert len(history) == 2
    assert all(exp.metric_tracked == "arpu" for exp in history)


def test_start_experiment_with_baseline_already_set(db_session):
    """Test starting experiment when baseline is already provided."""
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
    
    tracker = ExperimentTracker(db_session)
    experiment = tracker.create_experiment(
        name="Test Experiment",
        hypothesis="Test",
        change_description="Test",
        metric_tracked="arpu",
        affected_segment={"plan_id": plan.id},
        baseline_value=125.0  # Pre-set baseline
    )
    
    started = tracker.start_experiment(experiment.id)
    
    # Should keep the original baseline
    assert started.baseline_value == 125.0
    assert started.status == ExperimentStatus.RUNNING


def test_generate_summary_report_missing_values(db_session):
    """Test summary report with missing baseline or actual values."""
    experiment = Experiment(
        name="Incomplete Experiment",
        hypothesis="Test",
        change_description="Test",
        metric_tracked="arpu",
        affected_segment={"plan_id": 1},
        status=ExperimentStatus.RUNNING,
        started_at=datetime.now()
    )
    db_session.add(experiment)
    db_session.commit()
    
    reporter = ExperimentReporter(db_session)
    report = reporter.generate_summary_report(experiment.id)
    
    # Should handle missing values gracefully
    assert report["baseline_value"] is None
    assert report["actual_value"] is None
    # improvement_percent not in report when values are missing


def test_get_learnings_empty(db_session):
    """Test get learnings when no completed experiments exist."""
    # Create only draft/running experiments
    for i in range(2):
        exp = Experiment(
            name=f"Experiment {i}",
            hypothesis="Test",
            change_description="Test",
            metric_tracked="arpu",
            affected_segment={"plan_id": 1},
            status=ExperimentStatus.RUNNING if i == 0 else ExperimentStatus.DRAFT
        )
        db_session.add(exp)
    db_session.commit()
    
    reporter = ExperimentReporter(db_session)
    learnings = reporter.get_learnings()
    
    # Should return empty list
    assert len(learnings) == 0
