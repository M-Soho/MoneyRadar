"""Revenue Risk Alert System - Early Warning Detection."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from monetization_engine.models import (
    Subscription, Alert, AlertType, AlertSeverity,
    RevenueEvent, RevenueEventType, MRRSnapshot,
    UsageRecord, CustomerScore
)
from monetization_engine.config import get_settings

settings = get_settings()


class RiskDetector:
    """Detect revenue risks and generate alerts."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def scan_all_risks(self) -> Dict[str, List[Alert]]:
        """Run all risk detection checks."""
        alerts = {
            "critical": [],
            "warning": [],
            "informational": []
        }
        
        # Run all detection methods
        alerts_list = []
        alerts_list.extend(self.detect_declining_usage())
        alerts_list.extend(self.detect_payment_issues())
        alerts_list.extend(self.detect_downgrades())
        alerts_list.extend(self.detect_mrr_decline())
        
        # Categorize by severity
        for alert in alerts_list:
            if alert.severity == AlertSeverity.CRITICAL:
                alerts["critical"].append(alert)
            elif alert.severity == AlertSeverity.WARNING:
                alerts["warning"].append(alert)
            else:
                alerts["informational"].append(alert)
        
        return alerts
    
    def detect_declining_usage(self, lookback_days: int = 30) -> List[Alert]:
        """Detect customers with declining usage trends."""
        alerts = []
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get all active subscriptions
        subscriptions = self.db.query(Subscription).filter(
            Subscription.status == "active"
        ).all()
        
        for sub in subscriptions:
            # Get usage trend
            trend = self._calculate_usage_trend(sub.id, lookback_days)
            
            # Negative trend indicates declining usage
            if trend < -0.2:  # 20% decline
                alert = self._create_alert(
                    alert_type=AlertType.DECLINING_USAGE,
                    severity=AlertSeverity.WARNING,
                    subscription_id=sub.id,
                    customer_id=sub.customer_id,
                    title=f"Declining Usage: {sub.customer_id}",
                    description=f"Usage declined {abs(trend)*100:.1f}% over {lookback_days} days",
                    data={"trend": trend, "lookback_days": lookback_days},
                    recommended_action="Reach out to understand usage decline"
                )
                if alert:
                    alerts.append(alert)
        
        return alerts
    
    def detect_payment_issues(self) -> List[Alert]:
        """Detect payment retry patterns and failures."""
        alerts = []
        
        # Look for recent payment failures
        recent_failures = self.db.query(RevenueEvent).filter(
            RevenueEvent.event_type == RevenueEventType.PAYMENT_FAILED,
            RevenueEvent.occurred_at >= datetime.utcnow() - timedelta(days=7)
        ).all()
        
        for event in recent_failures:
            if not event.subscription:
                continue
            
            # Check retry count
            retry_count = event.metadata.get("attempt_count", 1) if event.metadata else 1
            
            severity = AlertSeverity.WARNING if retry_count < 3 else AlertSeverity.CRITICAL
            
            alert = self._create_alert(
                alert_type=AlertType.PAYMENT_RETRY,
                severity=severity,
                subscription_id=event.subscription.id,
                customer_id=event.subscription.customer_id,
                title=f"Payment Issue: {event.subscription.customer_id}",
                description=f"Payment failed (attempt {retry_count})",
                data={"retry_count": retry_count, "amount": event.amount},
                recommended_action="Contact customer about payment method"
            )
            if alert:
                alerts.append(alert)
        
        return alerts
    
    def detect_downgrades(self, lookback_days: int = 30) -> List[Alert]:
        """Detect recent plan downgrades."""
        alerts = []
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        downgrades = self.db.query(RevenueEvent).filter(
            RevenueEvent.event_type == RevenueEventType.SUBSCRIPTION_DOWNGRADED,
            RevenueEvent.occurred_at >= cutoff_date
        ).all()
        
        for event in downgrades:
            if not event.subscription:
                continue
            
            alert = self._create_alert(
                alert_type=AlertType.PLAN_DOWNGRADE,
                severity=AlertSeverity.WARNING,
                subscription_id=event.subscription.id,
                customer_id=event.subscription.customer_id,
                title=f"Recent Downgrade: {event.subscription.customer_id}",
                description=f"Plan downgraded, MRR decreased by ${abs(event.mrr_delta):.2f}",
                data={
                    "mrr_delta": event.mrr_delta,
                    "occurred_at": event.occurred_at.isoformat()
                },
                recommended_action="Follow up to understand reason for downgrade"
            )
            if alert:
                alerts.append(alert)
        
        return alerts
    
    def detect_mrr_decline(self, lookback_days: int = 7) -> List[Alert]:
        """Detect overall MRR decline."""
        alerts = []
        
        # Get recent snapshots
        snapshots = self.db.query(MRRSnapshot).filter(
            MRRSnapshot.date >= datetime.utcnow() - timedelta(days=lookback_days)
        ).order_by(MRRSnapshot.date.desc()).limit(lookback_days).all()
        
        if len(snapshots) < 2:
            return alerts
        
        # Compare latest to earliest
        latest = snapshots[0]
        earliest = snapshots[-1]
        
        if earliest.total_mrr == 0:
            return alerts
        
        decline_percent = ((latest.total_mrr - earliest.total_mrr) / earliest.total_mrr) * 100
        
        if decline_percent < 0:  # Negative growth = decline
            abs_decline = abs(decline_percent)
            
            if abs_decline > settings.mrr_decline_critical_percent:
                severity = AlertSeverity.CRITICAL
            elif abs_decline > settings.mrr_decline_warning_percent:
                severity = AlertSeverity.WARNING
            else:
                return alerts
            
            alert = Alert(
                alert_type=AlertType.MRR_DECLINE,
                severity=severity,
                title=f"MRR Decline Alert",
                description=f"MRR declined {abs_decline:.1f}% over {lookback_days} days",
                data={
                    "decline_percent": decline_percent,
                    "current_mrr": latest.total_mrr,
                    "previous_mrr": earliest.total_mrr,
                    "churned_mrr": latest.churned_mrr,
                    "new_mrr": latest.new_mrr
                },
                recommended_action="Review churn reasons and retention strategy"
            )
            
            self.db.add(alert)
            self.db.commit()
            alerts.append(alert)
        
        return alerts
    
    def _calculate_usage_trend(self, subscription_id: int, days: int) -> float:
        """Calculate usage trend over time period."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get usage records
        usage_records = self.db.query(UsageRecord).filter(
            UsageRecord.subscription_id == subscription_id,
            UsageRecord.recorded_at >= cutoff_date
        ).order_by(UsageRecord.recorded_at).all()
        
        if len(usage_records) < 2:
            return 0.0
        
        # Simple trend: compare first half to second half
        midpoint = len(usage_records) // 2
        first_half = usage_records[:midpoint]
        second_half = usage_records[midpoint:]
        
        avg_first = sum(r.quantity for r in first_half) / len(first_half)
        avg_second = sum(r.quantity for r in second_half) / len(second_half)
        
        if avg_first == 0:
            return 0.0
        
        trend = (avg_second - avg_first) / avg_first
        return trend
    
    def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        subscription_id: Optional[int],
        customer_id: str,
        title: str,
        description: str,
        data: Dict[str, Any],
        recommended_action: str
    ) -> Optional[Alert]:
        """Create an alert if it doesn't already exist."""
        # Check for existing unresolved alert
        existing = self.db.query(Alert).filter(
            Alert.customer_id == customer_id,
            Alert.alert_type == alert_type,
            Alert.is_resolved == False
        ).first()
        
        if existing:
            return None
        
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            subscription_id=subscription_id,
            customer_id=customer_id,
            title=title,
            description=description,
            data=data,
            recommended_action=recommended_action
        )
        
        self.db.add(alert)
        self.db.commit()
        
        return alert


class ExpansionScorer:
    """Score customers for expansion readiness (Secondary Feature)."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def score_customer(self, customer_id: str) -> CustomerScore:
        """Calculate expansion readiness score for a customer."""
        # Get subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.customer_id == customer_id,
            Subscription.status == "active"
        ).first()
        
        if not subscription:
            raise ValueError(f"No active subscription for customer {customer_id}")
        
        # Calculate factors
        tenure_days = (datetime.utcnow() - subscription.created_at).days
        usage_trend = self._get_usage_trend(subscription.id)
        
        # Simple scoring algorithm
        score = 0.0
        
        # Tenure factor (0-30 points)
        if tenure_days > 365:
            score += 30
        elif tenure_days > 180:
            score += 20
        elif tenure_days > 90:
            score += 10
        
        # Usage trend factor (0-40 points)
        if usage_trend > 0.5:  # Strong growth
            score += 40
        elif usage_trend > 0.2:  # Moderate growth
            score += 25
        elif usage_trend > 0:  # Slight growth
            score += 10
        
        # Engagement factor (0-30 points) - based on usage level
        avg_usage = self._get_average_usage(subscription.id)
        score += min(30, avg_usage * 30)
        
        # Categorize
        if score >= 70:
            category = "safe_to_upsell"
        elif score >= 40:
            category = "neutral"
        else:
            category = "do_not_touch"
        
        # Check for churn risk
        if usage_trend < -0.2:
            category = "likely_to_churn"
            score = max(0, score - 30)
        
        # Update or create score
        customer_score = self.db.query(CustomerScore).filter(
            CustomerScore.customer_id == customer_id
        ).first()
        
        if customer_score:
            customer_score.expansion_score = score
            customer_score.expansion_category = category
            customer_score.tenure_days = tenure_days
            customer_score.usage_trend = usage_trend
            customer_score.calculated_at = datetime.utcnow()
        else:
            customer_score = CustomerScore(
                customer_id=customer_id,
                subscription_id=subscription.id,
                expansion_score=score,
                expansion_category=category,
                tenure_days=tenure_days,
                usage_trend=usage_trend
            )
            self.db.add(customer_score)
        
        self.db.commit()
        return customer_score
    
    def _get_usage_trend(self, subscription_id: int, days: int = 30) -> float:
        """Get usage trend for subscription."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        records = self.db.query(UsageRecord).filter(
            UsageRecord.subscription_id == subscription_id,
            UsageRecord.recorded_at >= cutoff
        ).order_by(UsageRecord.recorded_at).all()
        
        if len(records) < 2:
            return 0.0
        
        midpoint = len(records) // 2
        first_half_avg = sum(r.quantity for r in records[:midpoint]) / midpoint
        second_half_avg = sum(r.quantity for r in records[midpoint:]) / (len(records) - midpoint)
        
        if first_half_avg == 0:
            return 0.0
        
        return (second_half_avg - first_half_avg) / first_half_avg
    
    def _get_average_usage(self, subscription_id: int) -> float:
        """Get average usage ratio (usage / limit)."""
        records = self.db.query(UsageRecord).filter(
            UsageRecord.subscription_id == subscription_id,
            UsageRecord.limit.isnot(None),
            UsageRecord.limit > 0
        ).all()
        
        if not records:
            return 0.0
        
        ratios = [r.quantity / r.limit for r in records if r.limit > 0]
        return sum(ratios) / len(ratios) if ratios else 0.0
