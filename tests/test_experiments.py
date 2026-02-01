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
