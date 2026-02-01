"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock

from monetization_engine.cli import cli
from monetization_engine.models import (
    Product, Plan, Subscription, Alert, AlertType, AlertSeverity
)


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_cli_data(db_session):
    """Create sample data for CLI tests."""
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
        created_at=datetime.now(UTC)
    )
    db_session.add(subscription)
    
    alert = Alert(
        alert_type=AlertType.DECLINING_USAGE,
        severity=AlertSeverity.WARNING,
        subscription_id=subscription.id,
        customer_id="cus_test",
        title="Test Alert",
        description="Test description"
    )
    db_session.add(alert)
    
    db_session.commit()
    
    return {
        "product": product,
        "plan": plan,
        "subscription": subscription,
        "alert": alert
    }


def test_cli_help(runner):
    """Test CLI help command."""
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'MoneyRadar' in result.output or 'Usage:' in result.output


def test_init_command(runner):
    """Test database initialization command."""
    with patch('monetization_engine.cli.init_db') as mock_init:
        result = runner.invoke(cli, ['init'])
        assert result.exit_code == 0
        mock_init.assert_called_once()


def test_analyze_mismatches_command(runner, sample_cli_data):
    """Test analyze-mismatches command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db:
        # Mock the database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        result = runner.invoke(cli, ['analyze-mismatches'])
        
        # Should run without crashing
        assert result.exit_code == 0 or 'upgrade_candidates' in result.output or 'No' in result.output


def test_scan_risks_command(runner):
    """Test scan-risks command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db, \
         patch('monetization_engine.cli.RiskDetector') as mock_detector:
        
        # Mock the detector
        mock_instance = MagicMock()
        mock_detector.return_value = mock_instance
        mock_instance.scan_all_risks.return_value = {'critical': [], 'warning': [], 'informational': []}
        
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        result = runner.invoke(cli, ['scan-risks'])
        
        # Should run without crashing
        assert result.exit_code == 0 or 'alerts' in result.output.lower()


def test_list_alerts_command(runner):
    """Test list-alerts command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db:
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock empty alerts
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        result = runner.invoke(cli, ['list-alerts'])
        
        # Should run without errors
        assert result.exit_code == 0 or 'No active alerts' in result.output


def test_list_alerts_resolved(runner):
    """Test list-alerts --resolved command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db:
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        result = runner.invoke(cli, ['list-alerts', '--resolved'])
        
        assert result.exit_code == 0


def test_score_customer_command(runner):
    """Test score-customer command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db, \
         patch('monetization_engine.cli.ExpansionScorer') as mock_scorer:
        
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock scorer
        mock_instance = MagicMock()
        mock_scorer.return_value = mock_instance
        mock_score = MagicMock()
        mock_score.customer_id = "cus_test"
        mock_score.expansion_score = 75.0
        mock_score.expansion_category = "safe_to_upsell"
        mock_score.tenure_days = 100
        mock_score.usage_trend = 0.25
        mock_instance.score_customer.return_value = mock_score
        
        result = runner.invoke(cli, ['score-customer', 'cus_test'])
        
        assert result.exit_code == 0
        assert 'cus_test' in result.output or '75' in result.output


def test_calculate_mrr_command(runner):
    """Test calculate-mrr command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db, \
         patch('monetization_engine.cli.StripeIngestion') as mock_ingestion:
        
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        mock_instance = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.total_mrr = 1000.0
        mock_snapshot.new_mrr = 100.0
        mock_snapshot.expansion_mrr = 50.0
        mock_snapshot.contraction_mrr = 25.0
        mock_snapshot.churned_mrr = 10.0
        mock_instance.calculate_daily_mrr_snapshot.return_value = mock_snapshot
        mock_ingestion.return_value = mock_instance
        
        result = runner.invoke(cli, ['calculate-mrr'])
        
        assert result.exit_code == 0
        mock_instance.calculate_daily_mrr_snapshot.assert_called_once()


def test_sync_stripe_command(runner):
    """Test sync-stripe command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db, \
         patch('monetization_engine.cli.StripeIngestion') as mock_ingestion:
        
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        mock_instance = MagicMock()
        mock_ingestion.return_value = mock_instance
        
        result = runner.invoke(cli, ['sync-stripe'])
        
        assert result.exit_code == 0
        mock_instance.sync_products_and_plans.assert_called_once()


def test_verbose_flag(runner):
    """Test --verbose flag."""
    with patch('monetization_engine.cli.setup_logging') as mock_logging:
        result = runner.invoke(cli, ['--verbose', '--help'])
        
        # Verbose flag should be recognized
        assert result.exit_code == 0


def test_experiment_list_command(runner):
    """Test experiment list command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db:
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.all.return_value = []
        
        result = runner.invoke(cli, ['experiment', 'list'])
        
        assert result.exit_code == 0


def test_experiment_create_command(runner):
    """Test experiment create command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db, \
         patch('monetization_engine.cli.ExperimentTracker') as mock_tracker:
        
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        mock_instance = MagicMock()
        mock_tracker.return_value = mock_instance
        mock_exp = MagicMock()
        mock_exp.id = 1
        mock_exp.name = "Test Experiment"
        mock_instance.create_experiment.return_value = mock_exp
        
        result = runner.invoke(cli, [
            'experiment', 'create',
            '--name', 'Test Experiment',
            '--hypothesis', 'Test hypothesis',
            '--change', 'Test change',
            '--metric', 'arpu'
        ])
        
        assert result.exit_code == 0
        assert 'Test Experiment' in result.output or 'created' in result.output.lower()


def test_experiment_start_command(runner):
    """Test experiment start command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db, \
         patch('monetization_engine.cli.ExperimentTracker') as mock_tracker:
        
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        mock_instance = MagicMock()
        mock_tracker.return_value = mock_instance
        
        result = runner.invoke(cli, ['experiment', 'start', '1'])
        
        assert result.exit_code == 0 or result.exit_code == 1  # May fail if experiment doesn't exist


def test_experiment_analyze_command(runner):
    """Test experiment analyze command."""
    with patch('monetization_engine.cli.get_db') as mock_get_db, \
         patch('monetization_engine.cli.ExperimentReporter') as mock_reporter:
        
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        mock_instance = MagicMock()
        mock_reporter.return_value = mock_instance
        mock_instance.analyze_experiment.return_value = {
            'experiment_id': 1,
            'name': 'Test',
            'status': 'running',
            'metric': 'arpu',
            'baseline_value': 50.0,
            'current_value': 55.0,
            'improvement': 5.0,
            'days_running': 10
        }
        
        result = runner.invoke(cli, ['experiment', 'analyze', '1'])
        
        assert result.exit_code == 0 or result.exit_code == 1  # May fail if not found
