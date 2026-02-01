"""Subscription and revenue event models."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from monetization_engine.database import Base


class Subscription(Base):
    """Customer subscriptions."""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=False)
    customer_id = Column(String(255), nullable=False)  # Stripe customer ID
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    
    status = Column(String(50))  # active, canceled, past_due, etc.
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    
    mrr = Column(Float, default=0.0)  # Monthly Recurring Revenue
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    canceled_at = Column(DateTime)
    
    plan = relationship("Plan", back_populates="subscriptions")
    events = relationship("RevenueEvent", back_populates="subscription")
    usage_records = relationship("UsageRecord", back_populates="subscription")
    
    __table_args__ = (
        Index("idx_subscription_customer", "customer_id"),
        Index("idx_subscription_status", "status"),
    )


class RevenueEventType(enum.Enum):
    """Types of revenue events."""
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_CANCELED = "subscription_canceled"
    SUBSCRIPTION_UPGRADED = "subscription_upgraded"
    SUBSCRIPTION_DOWNGRADED = "subscription_downgraded"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    MRR_DELTA = "mrr_delta"


class RevenueEvent(Base):
    """Revenue-affecting events from Stripe."""
    __tablename__ = "revenue_events"
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    event_type = Column(Enum(RevenueEventType), nullable=False)
    
    # Event details
    stripe_event_id = Column(String(255), unique=True)
    amount = Column(Float)
    currency = Column(String(3), default="USD")
    mrr_delta = Column(Float)  # Change in MRR
    
    event_metadata = Column(JSON)  # Additional event data (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, server_default=func.now())
    
    subscription = relationship("Subscription", back_populates="events")
    
    __table_args__ = (
        Index("idx_revenue_event_type", "event_type"),
        Index("idx_revenue_event_occurred", "occurred_at"),
    )


class MRRSnapshot(Base):
    """Daily MRR snapshots for tracking."""
    __tablename__ = "mrr_snapshots"
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, unique=True)
    
    total_mrr = Column(Float, nullable=False, default=0.0)
    new_mrr = Column(Float, default=0.0)
    expansion_mrr = Column(Float, default=0.0)
    contraction_mrr = Column(Float, default=0.0)
    churned_mrr = Column(Float, default=0.0)
    
    # Product breakdown
    product_breakdown = Column(JSON)  # {"product_1": 1000, "product_2": 500}
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index("idx_mrr_snapshot_date", "date"),
    )
