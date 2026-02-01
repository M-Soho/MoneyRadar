"""Alert and notification models."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Enum, Index, Text
from sqlalchemy.sql import func
import enum

from monetization_engine.database import Base


class AlertSeverity(enum.Enum):
    """Alert severity levels."""
    INFORMATIONAL = "informational"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(enum.Enum):
    """Types of alerts."""
    DECLINING_USAGE = "declining_usage"
    SUPPORT_TICKET_SPIKE = "support_ticket_spike"
    PAYMENT_RETRY = "payment_retry"
    PLAN_DOWNGRADE = "plan_downgrade"
    USAGE_MISMATCH_HIGH = "usage_mismatch_high"  # Heavy usage, low tier
    USAGE_MISMATCH_LOW = "usage_mismatch_low"  # Light usage, high tier
    MRR_DECLINE = "mrr_decline"
    CHURN_RISK = "churn_risk"


class Alert(Base):
    """Revenue risk alerts."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    
    # Target
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    customer_id = Column(String(255))
    
    # Alert details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    data = Column(JSON)  # Additional context
    
    # Recommendations
    recommended_action = Column(Text)
    
    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index("idx_alert_type_severity", "alert_type", "severity"),
        Index("idx_alert_customer", "customer_id"),
        Index("idx_alert_resolved", "is_resolved"),
    )
