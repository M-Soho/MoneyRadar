"""Experiment tracking models."""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Enum, Index, Text
from sqlalchemy.sql import func
import enum

from monetization_engine.database import Base


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
