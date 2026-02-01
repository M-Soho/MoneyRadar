"""Command-line interface for MoneyRadar."""

import click
import logging
from datetime import datetime
from tabulate import tabulate

from monetization_engine.database import get_db, init_db
from monetization_engine.logging_config import setup_logging
from monetization_engine.ingestion import StripeIngestion
from monetization_engine.ingestion.usage import UsageTracker
from monetization_engine.analysis import MismatchDetector
from monetization_engine.analysis.risk_detection import RiskDetector, ExpansionScorer
from monetization_engine.experiments import ExperimentTracker, ExperimentReporter

logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """MoneyRadar - Internal Monetization Engine."""
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)


# ============================================================================
# Database Commands
# ============================================================================

@cli.command()
def init():
    """Initialize the database."""
    click.echo("Initializing database...")
    init_db()
    click.echo("✓ Database initialized")


# ============================================================================
# Sync Commands
# ============================================================================

@cli.command()
def sync_stripe():
    """Sync products and plans from Stripe."""
    click.echo("Syncing from Stripe...")
    
    with get_db() as db:
        ingestion = StripeIngestion(db)
        ingestion.sync_products_and_plans()
    
    click.echo("✓ Stripe sync completed")


@cli.command()
def calculate_mrr():
    """Calculate daily MRR snapshot."""
    click.echo("Calculating MRR snapshot...")
    
    with get_db() as db:
        ingestion = StripeIngestion(db)
        snapshot = ingestion.calculate_daily_mrr_snapshot()
    
    click.echo(f"✓ MRR Snapshot: ${snapshot.total_mrr:,.2f}")
    click.echo(f"  New MRR: ${snapshot.new_mrr:,.2f}")
    click.echo(f"  Expansion: ${snapshot.expansion_mrr:,.2f}")
    click.echo(f"  Contraction: ${snapshot.contraction_mrr:,.2f}")
    click.echo(f"  Churned: ${snapshot.churned_mrr:,.2f}")


# ============================================================================
# Analysis Commands
# ============================================================================

@cli.command()
def analyze_mismatches():
    """Analyze usage vs price mismatches."""
    click.echo("Analyzing mismatches...")
    
    with get_db() as db:
        detector = MismatchDetector(db)
        results = detector.analyze_all_subscriptions()
    
    click.echo(f"\n📈 Upgrade Candidates: {len(results['upgrade_candidates'])}")
    if results['upgrade_candidates']:
        data = [
            [
                r['customer_id'][:20],
                r['plan_name'],
                f"${r['mrr']:.2f}",
                f"{r['utilization']*100:.1f}%"
            ]
            for r in results['upgrade_candidates'][:10]
        ]
        click.echo(tabulate(data, headers=['Customer', 'Plan', 'MRR', 'Usage'], tablefmt='simple'))
    
    click.echo(f"\n💰 Overpriced Customers: {len(results['overpriced_customers'])}")
    if results['overpriced_customers']:
        data = [
            [
                r['customer_id'][:20],
                r['plan_name'],
                f"${r['mrr']:.2f}",
                f"{r['utilization']*100:.1f}%"
            ]
            for r in results['overpriced_customers'][:10]
        ]
        click.echo(tabulate(data, headers=['Customer', 'Plan', 'MRR', 'Usage'], tablefmt='simple'))


@cli.command()
def scan_risks():
    """Scan for revenue risks."""
    click.echo("Scanning for risks...")
    
    with get_db() as db:
        detector = RiskDetector(db)
        results = detector.scan_all_risks()
    
    click.echo(f"\n🚨 Critical Alerts: {len(results['critical'])}")
    for alert in results['critical'][:5]:
        click.echo(f"  • {alert.title}")
    
    click.echo(f"\n⚠️  Warning Alerts: {len(results['warning'])}")
    for alert in results['warning'][:5]:
        click.echo(f"  • {alert.title}")
    
    click.echo(f"\nℹ️  Informational: {len(results['informational'])}")


@cli.command()
@click.option('--resolved/--active', default=False)
def list_alerts(resolved):
    """List alerts."""
    with get_db() as db:
        from monetization_engine.models import Alert
        
        alerts = db.query(Alert).filter(
            Alert.is_resolved == resolved
        ).order_by(Alert.created_at.desc()).limit(20).all()
    
    if not alerts:
        click.echo("No alerts found")
        return
    
    data = [
        [
            a.severity.value[:4].upper(),
            a.alert_type.value[:20],
            a.customer_id[:15] if a.customer_id else "N/A",
            a.title[:40]
        ]
        for a in alerts
    ]
    
    click.echo(tabulate(data, headers=['Severity', 'Type', 'Customer', 'Title'], tablefmt='simple'))


# ============================================================================
# Customer Commands
# ============================================================================

@cli.command()
@click.argument('customer_id')
def score_customer(customer_id):
    """Calculate expansion readiness score for a customer."""
    with get_db() as db:
        scorer = ExpansionScorer(db)
        
        try:
            score = scorer.score_customer(customer_id)
            
            click.echo(f"\nCustomer: {customer_id}")
            click.echo(f"Expansion Score: {score.expansion_score:.1f}/100")
            click.echo(f"Category: {score.expansion_category}")
            click.echo(f"Tenure: {score.tenure_days} days")
            click.echo(f"Usage Trend: {score.usage_trend:+.1%}")
        
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)


# ============================================================================
# Experiment Commands
# ============================================================================

@cli.group()
def experiment():
    """Manage experiments."""
    pass


@experiment.command('create')
@click.option('--name', required=True)
@click.option('--hypothesis', required=True)
@click.option('--change', required=True)
@click.option('--metric', required=True)
def create_experiment(name, hypothesis, change, metric):
    """Create a new experiment."""
    with get_db() as db:
        tracker = ExperimentTracker(db)
        exp = tracker.create_experiment(
            name=name,
            hypothesis=hypothesis,
            change_description=change,
            metric_tracked=metric,
            affected_segment={}
        )
    
    click.echo(f"✓ Experiment created (ID: {exp.id})")


@experiment.command('list')
def list_experiments():
    """List all experiments."""
    with get_db() as db:
        tracker = ExperimentTracker(db)
        active = tracker.get_active_experiments()
    
    if not active:
        click.echo("No active experiments")
        return
    
    data = [
        [e.id, e.name[:30], e.metric_tracked, e.status.value]
        for e in active
    ]
    
    click.echo(tabulate(data, headers=['ID', 'Name', 'Metric', 'Status'], tablefmt='simple'))


@experiment.command('start')
@click.argument('experiment_id', type=int)
def start_experiment(experiment_id):
    """Start an experiment."""
    with get_db() as db:
        tracker = ExperimentTracker(db)
        exp = tracker.start_experiment(experiment_id)
    
    click.echo(f"✓ Experiment started: {exp.name}")
    click.echo(f"  Baseline: {exp.baseline_value}")


@experiment.command('analyze')
@click.argument('experiment_id', type=int)
def analyze_experiment(experiment_id):
    """Analyze experiment results."""
    with get_db() as db:
        tracker = ExperimentTracker(db)
        analysis = tracker.analyze_experiment(experiment_id)
    
    click.echo(f"\nExperiment: {analysis['name']}")
    click.echo(f"Status: {analysis['status']}")
    click.echo(f"Metric: {analysis['metric']}")
    click.echo(f"Baseline: {analysis['baseline_value']:.2f}")
    click.echo(f"Current: {analysis['current_value']:.2f}")
    click.echo(f"Improvement: {analysis['improvement_percent']:+.1f}%")
    click.echo(f"Days Running: {analysis['days_running']}")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
