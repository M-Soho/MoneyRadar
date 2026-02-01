"""Tests for API endpoints."""

import pytest
import json
from datetime import datetime, timedelta, UTC
from flask import Flask

from monetization_engine.api.app import app
from monetization_engine.models import (
    Product, Plan, Subscription, MRRSnapshot,
    RevenueEvent, RevenueEventType, Alert, AlertType, AlertSeverity,
    Experiment, ExperimentStatus
)


@pytest.fixture
def client(db_session):
    """Create Flask test client."""
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_data(db_session):
    """Create sample data for API tests."""
    # Create product and plan
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
    
    # Create subscription
    subscription = Subscription(
        stripe_subscription_id="sub_test",
        customer_id="cus_test",
        plan_id=plan.id,
        status="active",
        mrr=29.0,
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
        created_at=datetime.now(UTC) - timedelta(days=100)
    )
    db_session.add(subscription)
    db_session.flush()
    
    # Create MRR snapshot
    snapshot = MRRSnapshot(
        date=datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0),
        total_mrr=29.0,
        new_mrr=29.0,
        expansion_mrr=0.0,
        contraction_mrr=0.0,
        churned_mrr=0.0
    )
    db_session.add(snapshot)
    
    # Create alert
    alert = Alert(
        alert_type=AlertType.DECLINING_USAGE,
        severity=AlertSeverity.WARNING,
        subscription_id=subscription.id,
        customer_id="cus_test",
        title="Test Alert",
        description="Test description",
        is_resolved=False
    )
    db_session.add(alert)
    
    # Create experiment
    experiment = Experiment(
        name="Test Experiment",
        hypothesis="Test hypothesis",
        change_description="Test change",
        metric_tracked="arpu",
        status=ExperimentStatus.DRAFT
    )
    db_session.add(experiment)
    
    db_session.commit()
    
    return {
        "product": product,
        "plan": plan,
        "subscription": subscription,
        "snapshot": snapshot,
        "alert": alert,
        "experiment": experiment
    }


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['service'] == 'MoneyRadar'


def test_get_mrr(client, sample_data):
    """Test GET /api/revenue/mrr endpoint."""
    response = client.get('/api/revenue/mrr')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'current_mrr' in data
    assert 'latest_snapshot' in data
    assert data['current_mrr'] == 29.0


def test_get_mrr_snapshots(client, sample_data):
    """Test GET /api/revenue/snapshots endpoint."""
    response = client.get('/api/revenue/snapshots?days=30')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'snapshots' in data
    assert isinstance(data['snapshots'], list)
    assert len(data['snapshots']) > 0


def test_analyze_mismatches(client, sample_data):
    """Test GET /api/analysis/mismatches endpoint."""
    response = client.get('/api/analysis/mismatches')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'upgrade_candidates' in data
    assert 'overpriced_customers' in data
    assert isinstance(data['upgrade_candidates'], list)
    assert isinstance(data['overpriced_customers'], list)


def test_list_alerts(client, sample_data):
    """Test GET /api/alerts endpoint."""
    response = client.get('/api/alerts')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'alerts' in data
    assert isinstance(data['alerts'], list)
    assert len(data['alerts']) > 0
    
    # Check alert structure
    alert = data['alerts'][0]
    assert 'id' in alert
    assert 'alert_type' in alert
    assert 'severity' in alert
    assert 'title' in alert


def test_list_resolved_alerts(client, sample_data):
    """Test GET /api/alerts?resolved=true endpoint."""
    response = client.get('/api/alerts?resolved=true')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'alerts' in data
    assert isinstance(data['alerts'], list)


def test_resolve_alert(client, sample_data):
    """Test POST /api/alerts/<id>/resolve endpoint."""
    alert_id = sample_data['alert'].id
    
    response = client.post(f'/api/alerts/{alert_id}/resolve')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['message'] == 'Alert resolved'
    assert data['alert_id'] == alert_id


def test_resolve_nonexistent_alert(client, sample_data):
    """Test resolving non-existent alert."""
    response = client.post('/api/alerts/99999/resolve')
    assert response.status_code == 404


def test_scan_risks(client, sample_data):
    """Test POST /api/alerts/scan endpoint."""
    response = client.post('/api/alerts/scan')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'alerts_created' in data
    assert isinstance(data['alerts_created'], int)


def test_get_customer_score(client, sample_data):
    """Test GET /api/customers/<id>/score endpoint."""
    response = client.get('/api/customers/cus_test/score')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'customer_id' in data
    assert 'expansion_score' in data
    assert 'expansion_category' in data
    assert 'tenure_days' in data
    assert data['customer_id'] == 'cus_test'


def test_get_nonexistent_customer_score(client, sample_data):
    """Test getting score for non-existent customer."""
    response = client.get('/api/customers/cus_nonexistent/score')
    assert response.status_code == 404


def test_list_experiments(client, sample_data):
    """Test GET /api/experiments endpoint."""
    response = client.get('/api/experiments')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'experiments' in data
    assert isinstance(data['experiments'], list)
    assert len(data['experiments']) > 0


def test_get_experiment(client, sample_data):
    """Test GET /api/experiments/<id> endpoint."""
    experiment_id = sample_data['experiment'].id
    
    response = client.get(f'/api/experiments/{experiment_id}')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['id'] == experiment_id
    assert data['name'] == 'Test Experiment'
    assert data['status'] == 'draft'


def test_create_experiment(client, sample_data):
    """Test POST /api/experiments endpoint."""
    experiment_data = {
        "name": "New Experiment",
        "hypothesis": "Price increase will boost revenue",
        "change_description": "Increase plan price from $29 to $39",
        "metric_tracked": "arpu",
        "affected_segment": {"plan_id": sample_data['plan'].id}
    }
    
    response = client.post(
        '/api/experiments',
        data=json.dumps(experiment_data),
        content_type='application/json'
    )
    assert response.status_code == 201
    
    data = json.loads(response.data)
    assert 'id' in data
    assert data['name'] == 'New Experiment'
    assert data['status'] == 'draft'


def test_start_experiment(client, sample_data):
    """Test POST /api/experiments/<id>/start endpoint."""
    experiment_id = sample_data['experiment'].id
    
    response = client.post(f'/api/experiments/{experiment_id}/start')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'running'
    assert 'started_at' in data


def test_complete_experiment(client, sample_data):
    """Test POST /api/experiments/<id>/complete endpoint."""
    # First start the experiment
    experiment_id = sample_data['experiment'].id
    client.post(f'/api/experiments/{experiment_id}/start')
    
    # Then complete it
    completion_data = {
        "actual_value": 35.50,
        "outcome": "Successful - 22% increase in ARPU"
    }
    
    response = client.post(
        f'/api/experiments/{experiment_id}/complete',
        data=json.dumps(completion_data),
        content_type='application/json'
    )
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'completed'
    assert data['actual_value'] == 35.50
    assert 'ended_at' in data


def test_sync_stripe(client, sample_data):
    """Test POST /api/admin/sync-stripe endpoint."""
    response = client.post('/api/admin/sync-stripe')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'message' in data


def test_calculate_mrr_snapshot(client, sample_data):
    """Test POST /api/admin/calculate-mrr-snapshot endpoint."""
    response = client.post('/api/admin/calculate-mrr-snapshot')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'message' in data
    assert 'total_mrr' in data


def test_stripe_webhook_signature_verification(client):
    """Test Stripe webhook signature verification."""
    # Without proper signature, should fail
    response = client.post(
        '/webhooks/stripe',
        data=json.dumps({"type": "customer.subscription.created"}),
        content_type='application/json'
    )
    # Should return 400 because signature is missing/invalid
    assert response.status_code == 400
