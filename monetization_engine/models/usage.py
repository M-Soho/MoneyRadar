"""Usage tracking models."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from monetization_engine.database import Base


class UsageRecord(Base):
    """Customer usage data for mismatch detection."""
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    
    # Usage metrics
    metric_name = Column(String(100), nullable=False)  # e.g., "api_calls", "storage_gb"
    quantity = Column(Float, nullable=False)
    limit = Column(Float)  # Plan limit for this metric
    
    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    recorded_at = Column(DateTime, server_default=func.now())
    
    subscription = relationship("Subscription", back_populates="usage_records")
    
    __table_args__ = (
        Index("idx_usage_subscription_metric", "subscription_id", "metric_name"),
        Index("idx_usage_period", "period_start", "period_end"),
    )
