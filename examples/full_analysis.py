"""Example usage scripts."""

from datetime import datetime
from monetization_engine.database import get_db, init_db
from monetization_engine.ingestion import StripeIngestion
from monetization_engine.analysis import MismatchDetector
from monetization_engine.analysis.risk_detection import RiskDetector


def example_full_analysis():
    """Run a complete analysis workflow."""
    print("=== MoneyRadar Analysis Example ===\n")
    
    with get_db() as db:
        # 1. Sync from Stripe
        print("1. Syncing from Stripe...")
        ingestion = StripeIngestion(db)
        ingestion.sync_products_and_plans()
        print("   ✓ Products and plans synced\n")
        
        # 2. Calculate MRR
        print("2. Calculating MRR snapshot...")
        snapshot = ingestion.calculate_daily_mrr_snapshot()
        print(f"   Current MRR: ${snapshot.total_mrr:,.2f}")
        print(f"   New MRR: ${snapshot.new_mrr:,.2f}")
        print(f"   Churned MRR: ${snapshot.churned_mrr:,.2f}\n")
        
        # 3. Analyze mismatches
        print("3. Analyzing usage vs price mismatches...")
        detector = MismatchDetector(db)
        results = detector.analyze_all_subscriptions()
        
        print(f"   Upgrade candidates: {len(results['upgrade_candidates'])}")
        for candidate in results['upgrade_candidates'][:3]:
            print(f"   - {candidate['customer_id']}: {candidate['utilization']*100:.1f}% usage")
        
        print(f"\n   Overpriced customers: {len(results['overpriced_customers'])}")
        for customer in results['overpriced_customers'][:3]:
            print(f"   - {customer['customer_id']}: {customer['utilization']*100:.1f}% usage")
        
        # 4. Scan for risks
        print("\n4. Scanning for revenue risks...")
        risk_detector = RiskDetector(db)
        alerts = risk_detector.scan_all_risks()
        
        print(f"   Critical alerts: {len(alerts['critical'])}")
        print(f"   Warning alerts: {len(alerts['warning'])}")
        print(f"   Informational: {len(alerts['informational'])}")
        
        # 5. Show top critical alerts
        if alerts['critical']:
            print("\n   Top Critical Alerts:")
            for alert in alerts['critical'][:3]:
                print(f"   - {alert.title}")
                print(f"     {alert.description}")
    
    print("\n=== Analysis Complete ===")


if __name__ == "__main__":
    # Initialize database if needed
    init_db()
    
    # Run example
    example_full_analysis()
