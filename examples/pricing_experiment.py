"""Example: Track a pricing experiment."""

from monetization_engine.database import get_db, init_db
from monetization_engine.experiments import ExperimentTracker


def example_pricing_experiment():
    """Example of running a pricing experiment."""
    print("=== Pricing Experiment Example ===\n")
    
    with get_db() as db:
        tracker = ExperimentTracker(db)
        
        # 1. Create experiment
        print("1. Creating experiment...")
        experiment = tracker.create_experiment(
            name="Pro Plan Price Increase",
            hypothesis="Raising Pro from $49 to $59 will increase ARPU without significant churn",
            change_description="Price: $49 → $59 (20% increase)",
            metric_tracked="arpu",
            affected_segment={"plan_name": "Pro"},
            baseline_value=None  # Will be calculated
        )
        print(f"   ✓ Experiment created (ID: {experiment.id})")
        
        # 2. Start experiment
        print("\n2. Starting experiment...")
        experiment = tracker.start_experiment(experiment.id)
        print(f"   ✓ Experiment started")
        print(f"   Baseline ARPU: ${experiment.baseline_value:.2f}")
        print(f"   Control group: {experiment.control_group_size} customers")
        print(f"   Variant group: {experiment.variant_group_size} customers")
        
        # 3. Analyze during experiment
        print("\n3. Current status...")
        analysis = tracker.analyze_experiment(experiment.id)
        print(f"   Current ARPU: ${analysis['current_value']:.2f}")
        print(f"   Improvement: {analysis['improvement_percent']:+.1f}%")
        print(f"   Days running: {analysis['days_running']}")
        
        # 4. Complete experiment (example - would do this later)
        print("\n4. To complete experiment (when ready):")
        print(f"   moneyradar experiment analyze {experiment.id}")
        print(f"   # Then record results:")
        print(f"   # POST /api/experiments/{experiment.id}/complete")
        print(f"   # {{\"actual_value\": 54.00, \"outcome\": \"Success - ARPU increased 10%\"}}")
    
    print("\n=== Experiment Setup Complete ===")


if __name__ == "__main__":
    init_db()
    example_pricing_experiment()
