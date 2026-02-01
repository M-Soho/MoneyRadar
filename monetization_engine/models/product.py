"""Product and Plan models."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Index, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from monetization_engine.database import Base


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
