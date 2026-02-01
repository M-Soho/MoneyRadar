"""Configuration management for MoneyRadar."""

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    # Database
    database_url: str = Field(
        default="sqlite:///./moneyradar.db",
        description="Database connection string"
    )
    
    # Stripe
    stripe_api_key: str = Field(
        ...,
        description="Stripe secret API key"
    )
    stripe_webhook_secret: Optional[str] = Field(
        default=None,
        description="Stripe webhook signing secret"
    )
    
    # Flask
    flask_env: str = Field(default="development")
    secret_key: str = Field(default="dev-secret-change-me")
    
    # Alert Thresholds
    mrr_decline_warning_percent: float = Field(
        default=5.0,
        description="MRR decline % to trigger warning"
    )
    mrr_decline_critical_percent: float = Field(
        default=15.0,
        description="MRR decline % to trigger critical alert"
    )
    usage_mismatch_threshold: float = Field(
        default=0.7,
        description="Usage ratio threshold for mismatch detection"
    )
    support_ticket_spike_threshold: int = Field(
        default=3,
        description="Multiple of avg tickets to trigger alert"
    )
    
    # OPSP Integration (optional)
    opsp_api_url: Optional[str] = Field(default=None)
    opsp_api_key: Optional[str] = Field(default=None)


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
