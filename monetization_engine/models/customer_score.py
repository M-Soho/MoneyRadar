"""Customer intelligence and scoring models."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from monetization_engine.database import Base


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
