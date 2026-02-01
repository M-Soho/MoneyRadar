"""Customer Expansion Scoring System."""

from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session

from monetization_engine.models import Subscription, CustomerScore, UsageRecord


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is UTC-aware."""
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


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
        created_at = _ensure_utc(subscription.created_at)
        tenure_days = (datetime.now(UTC) - created_at).days
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
            customer_score.calculated_at = datetime.now(UTC)
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
        cutoff = datetime.now(UTC) - timedelta(days=days)
        
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


__all__ = ['ExpansionScorer']
