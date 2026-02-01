"""Database models for monetization engine."""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, JSON, Enum, Index, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from monetization_engine.database import Base


# ============================================================================
# 1. Pricing & Plan Map (Foundational)
# ============================================================================

class Product(Base):
    """Product catalog."""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    stripe_product_id = Column(String(255), unique=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    plans = relationship("Plan", back_populates="product")


class Plan(Base):
    """Pricing plans with versioning."""
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name = Column(String(255), nullable=False)  # e.g., "Pro", "Enterprise"
    version = Column(Integer, default=1)  # Versioning for price changes
    price_monthly = Column(Float, nullable=False)
    price_annual = Column(Float)
    currency = Column(String(3), default="USD")
    
    # Plan limits and features
    limits = Column(JSON)  # {"api_calls": 10000, "users": 5, "storage_gb": 100}
    features = Column(JSON)  # ["advanced_analytics", "priority_support"]
    
    # Versioning
    effective_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    effective_until = Column(DateTime)  # NULL = current version
    
    stripe_price_id = Column(String(255))
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    product = relationship("Product", back_populates="plans")
    subscriptions = relationship("Subscription", back_populates="plan")
    
    __table_args__ = (
        Index("idx_plan_product_version", "product_id", "version"),
        Index("idx_plan_effective_dates", "effective_from", "effective_until"),
    )


# ============================================================================
# 2. Revenue Signal Ingestion
# ============================================================================

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


# ============================================================================
# 3. Usage Tracking
# ============================================================================

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


# ============================================================================
# 4. Revenue Risk Alerts
# ============================================================================

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


# ============================================================================
# 5. Monetization Experiments
# ============================================================================

class ExperimentStatus(enum.Enum):
    """Experiment lifecycle status."""
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELED = "canceled"


class Experiment(Base):
    """Pricing and packaging experiments."""
    __tablename__ = "experiments"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    hypothesis = Column(Text, nullable=False)
    
    # Experiment setup
    affected_segment = Column(JSON)  # {"plan_id": 1, "customer_tags": ["beta"]}
    control_group_size = Column(Integer)
    variant_group_size = Column(Integer)
    
    # What's being tested
    change_description = Column(Text)  # e.g., "Raise Pro from $49 → $59"
    metric_tracked = Column(String(100))  # e.g., "conversion_rate", "arpu", "churn_rate"
    
    # Results
    baseline_value = Column(Float)
    target_value = Column(Float)
    actual_value = Column(Float)
    outcome = Column(Text)  # Summary of results
    
    # Timeline
    status = Column(Enum(ExperimentStatus), default=ExperimentStatus.DRAFT)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_experiment_status", "status"),
    )


# ============================================================================
# 6. Customer Intelligence (Secondary Features)
# ============================================================================

class CustomerScore(Base):
    """Expansion readiness and churn risk scoring."""
    __tablename__ = "customer_scores"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(String(255), nullable=False, unique=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    
    # Expansion readiness (0-100)
    expansion_score = Column(Float, default=0.0)
    expansion_category = Column(String(50))  # "safe_to_upsell", "do_not_touch", "likely_to_churn"
    
    # Factors
    tenure_days = Column(Integer)
    usage_trend = Column(Float)  # Positive = growing, negative = declining
    support_ticket_count = Column(Integer)
    engagement_score = Column(Float)
    
    # Last updated
    calculated_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index("idx_customer_score_customer", "customer_id"),
        Index("idx_customer_score_category", "expansion_category"),
    )
