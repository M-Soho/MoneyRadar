"""Usage vs Price Mismatch Detection - High Leverage Analysis."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from monetization_engine.models import (
    Subscription, UsageRecord, Plan, Alert, AlertType, AlertSeverity,
    CustomerScore
)
from monetization_engine.config import get_settings

settings = get_settings()


class MismatchDetector:
    """Detect pricing and usage mismatches."""
    
    def __init__(self, db: Session):
        self.db = db
        self.usage_threshold = settings.usage_mismatch_threshold
    
    def analyze_all_subscriptions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze all active subscriptions for mismatches."""
        active_subs = self.db.query(Subscription).filter(
            Subscription.status == "active"
        ).all()
        
        results = {
            "upgrade_candidates": [],
            "overpriced_customers": [],
            "mispriced_features": []
        }
        
        for sub in active_subs:
            mismatch = self._analyze_subscription(sub)
            
            if mismatch["type"] == "underpriced":
                results["upgrade_candidates"].append(mismatch)
            elif mismatch["type"] == "overpriced":
                results["overpriced_customers"].append(mismatch)
        
        return results
    
    def _analyze_subscription(self, subscription: Subscription) -> Dict[str, Any]:
        """Analyze a single subscription for mismatch."""
        # Get usage data for current period
        usage_summary = self._get_usage_summary(subscription)
        
        if not usage_summary:
            return {"type": "no_data", "subscription_id": subscription.id}
        
        # Calculate overall utilization
        total_utilization = self._calculate_utilization(usage_summary)
        
        result = {
            "subscription_id": subscription.id,
            "customer_id": subscription.customer_id,
            "plan_name": subscription.plan.name,
            "mrr": subscription.mrr,
            "utilization": total_utilization,
            "usage_details": usage_summary
        }
        
        # Heavy usage on low-tier plan = UPGRADE CANDIDATE
        if total_utilization > self.usage_threshold:
            result["type"] = "underpriced"
            result["recommendation"] = "Upgrade candidate - high usage"
            result["severity"] = AlertSeverity.WARNING
            
            # Create alert
            self._create_alert(
                subscription=subscription,
                alert_type=AlertType.USAGE_MISMATCH_HIGH,
                severity=AlertSeverity.WARNING,
                title=f"Upgrade Candidate: {subscription.customer_id}",
                description=f"Customer is using {total_utilization*100:.1f}% of plan limits",
                data=usage_summary,
                recommended_action=self._suggest_upgrade(subscription)
            )
        
        # Light usage on high-tier plan = OVERPRICED
        elif total_utilization < (1 - self.usage_threshold):
            result["type"] = "overpriced"
            result["recommendation"] = "Customer may be overpaying"
            result["severity"] = AlertSeverity.INFORMATIONAL
            
            # Create alert
            self._create_alert(
                subscription=subscription,
                alert_type=AlertType.USAGE_MISMATCH_LOW,
                severity=AlertSeverity.INFORMATIONAL,
                title=f"Low Utilization: {subscription.customer_id}",
                description=f"Customer is only using {total_utilization*100:.1f}% of plan limits",
                data=usage_summary,
                recommended_action="Consider offering a more appropriate plan"
            )
        
        else:
            result["type"] = "appropriate"
        
        return result
    
    def _get_usage_summary(self, subscription: Subscription) -> Dict[str, float]:
        """Get usage summary for subscription's current period."""
        usage_records = self.db.query(UsageRecord).filter(
            UsageRecord.subscription_id == subscription.id,
            UsageRecord.period_start >= subscription.current_period_start,
            UsageRecord.period_end <= subscription.current_period_end
        ).all()
        
        if not usage_records:
            return {}
        
        summary = {}
        for record in usage_records:
            if record.limit and record.limit > 0:
                utilization = record.quantity / record.limit
                summary[record.metric_name] = utilization
        
        return summary
    
    def _calculate_utilization(self, usage_summary: Dict[str, float]) -> float:
        """Calculate overall utilization percentage."""
        if not usage_summary:
            return 0.0
        
        # Average utilization across all metrics
        return sum(usage_summary.values()) / len(usage_summary)
    
    def _suggest_upgrade(self, subscription: Subscription) -> str:
        """Suggest an upgrade plan."""
        current_plan = subscription.plan
        
        # Find next tier plan
        higher_plans = self.db.query(Plan).filter(
            Plan.product_id == current_plan.product_id,
            Plan.price_monthly > current_plan.price_monthly,
            Plan.is_active == True
        ).order_by(Plan.price_monthly).all()
        
        if higher_plans:
            next_plan = higher_plans[0]
            mrr_increase = next_plan.price_monthly - current_plan.price_monthly
            return (
                f"Upgrade to {next_plan.name} (${next_plan.price_monthly}/mo) "
                f"for ${mrr_increase:.2f} additional MRR"
            )
        
        return "No higher tier available - consider custom pricing"
    
    def _create_alert(
        self,
        subscription: Subscription,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        description: str,
        data: Dict[str, Any],
        recommended_action: str
    ) -> Alert:
        """Create a mismatch alert."""
        # Check if similar alert already exists
        existing = self.db.query(Alert).filter(
            Alert.subscription_id == subscription.id,
            Alert.alert_type == alert_type,
            Alert.is_resolved == False
        ).first()
        
        if existing:
            return existing
        
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            subscription_id=subscription.id,
            customer_id=subscription.customer_id,
            title=title,
            description=description,
            data=data,
            recommended_action=recommended_action
        )
        
        self.db.add(alert)
        self.db.commit()
        
        return alert
    
    def detect_feature_mispricing(self) -> List[Dict[str, Any]]:
        """Detect features that might be mispriced across plans."""
        # This is more complex - look for patterns across customer base
        results = []
        
        # Get all plans
        plans = self.db.query(Plan).filter(Plan.is_active == True).all()
        
        for plan in plans:
            # Get subscriptions for this plan
            subs = self.db.query(Subscription).filter(
                Subscription.plan_id == plan.id,
                Subscription.status == "active"
            ).all()
            
            if len(subs) < 3:  # Need minimum sample size
                continue
            
            # Analyze usage patterns
            high_usage_count = 0
            low_usage_count = 0
            
            for sub in subs:
                usage_summary = self._get_usage_summary(sub)
                if not usage_summary:
                    continue
                
                utilization = self._calculate_utilization(usage_summary)
                
                if utilization > self.usage_threshold:
                    high_usage_count += 1
                elif utilization < (1 - self.usage_threshold):
                    low_usage_count += 1
            
            # If majority are mismatched, the plan itself might be mispriced
            total_analyzed = high_usage_count + low_usage_count
            if total_analyzed > 0:
                high_ratio = high_usage_count / total_analyzed
                
                if high_ratio > 0.6:
                    results.append({
                        "plan_id": plan.id,
                        "plan_name": plan.name,
                        "issue": "Plan limits may be too restrictive",
                        "affected_customers": high_usage_count,
                        "recommendation": "Consider raising limits or creating higher tier"
                    })
                elif high_ratio < 0.2:
                    results.append({
                        "plan_id": plan.id,
                        "plan_name": plan.name,
                        "issue": "Plan limits may be too generous",
                        "affected_customers": low_usage_count,
                        "recommendation": "Consider lowering limits or reducing price"
                    })
        
        return results


class SupportTicketAnalyzer:
    """Analyze support ticket patterns for mismatch signals."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def correlate_tickets_with_plans(
        self,
        ticket_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Correlate support tickets with plans.
        
        Args:
            ticket_data: List of tickets with customer_id and ticket_type
        """
        plan_tickets = {}
        
        for ticket in ticket_data:
            customer_id = ticket.get("customer_id")
            
            # Find subscription
            sub = self.db.query(Subscription).filter(
                Subscription.customer_id == customer_id,
                Subscription.status == "active"
            ).first()
            
            if not sub:
                continue
            
            plan_name = sub.plan.name
            
            if plan_name not in plan_tickets:
                plan_tickets[plan_name] = {
                    "total_customers": 0,
                    "total_tickets": 0,
                    "tickets_per_customer": 0.0
                }
            
            plan_tickets[plan_name]["total_tickets"] += 1
        
        # Calculate tickets per customer for each plan
        for plan_name in plan_tickets:
            customer_count = self.db.query(Subscription).join(Plan).filter(
                Plan.name == plan_name,
                Subscription.status == "active"
            ).count()
            
            plan_tickets[plan_name]["total_customers"] = customer_count
            if customer_count > 0:
                plan_tickets[plan_name]["tickets_per_customer"] = (
                    plan_tickets[plan_name]["total_tickets"] / customer_count
                )
        
        return plan_tickets
