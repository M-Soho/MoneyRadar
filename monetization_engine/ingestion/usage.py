"""Usage tracking and recording."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from monetization_engine.models import UsageRecord, Subscription, Plan

logger = logging.getLogger(__name__)


class UsageTracker:
    """Track and record customer usage data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_usage(
        self,
        customer_id: str,
        metric_name: str,
        quantity: float,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> UsageRecord:
        """Record usage data for a customer."""
        # Find active subscription for customer
        subscription = self.db.query(Subscription).filter(
            Subscription.customer_id == customer_id,
            Subscription.status == "active"
        ).first()
        
        if not subscription:
            raise ValueError(f"No active subscription found for customer {customer_id}")
        
        # Default to current billing period if not specified
        if not period_start:
            period_start = subscription.current_period_start
        if not period_end:
            period_end = subscription.current_period_end
        
        # Get plan limit for this metric
        plan = subscription.plan
        limit = None
        if plan.limits and metric_name in plan.limits:
            limit = float(plan.limits[metric_name])
        
        # Create usage record
        usage = UsageRecord(
            subscription_id=subscription.id,
            metric_name=metric_name,
            quantity=quantity,
            limit=limit,
            period_start=period_start,
            period_end=period_end
        )
        
        self.db.add(usage)
        self.db.commit()
        
        return usage
    
    def get_usage_summary(
        self,
        subscription_id: int,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict[str, Dict[str, float]]:
        """Get usage summary for a subscription."""
        query = self.db.query(UsageRecord).filter(
            UsageRecord.subscription_id == subscription_id
        )
        
        if period_start:
            query = query.filter(UsageRecord.period_start >= period_start)
        if period_end:
            query = query.filter(UsageRecord.period_end <= period_end)
        
        usage_records = query.all()
        
        summary = {}
        for record in usage_records:
            if record.metric_name not in summary:
                summary[record.metric_name] = {
                    "total": 0.0,
                    "limit": record.limit,
                    "utilization": 0.0
                }
            
            summary[record.metric_name]["total"] += record.quantity
            
            if record.limit:
                summary[record.metric_name]["utilization"] = (
                    summary[record.metric_name]["total"] / record.limit
                )
        
        return summary
    
    def bulk_import_usage(self, usage_data: List[Dict[str, Any]]) -> int:
        """Bulk import usage data from external source."""
        count = 0
        
        for data in usage_data:
            try:
                self.record_usage(
                    customer_id=data["customer_id"],
                    metric_name=data["metric_name"],
                    quantity=data["quantity"],
                    period_start=data.get("period_start"),
                    period_end=data.get("period_end")
                )
                count += 1
            except Exception as e:
                logger.error(f"Error importing usage for {data.get('customer_id')}: {e}")
        
        return count


__all__ = ['UsageTracker']
