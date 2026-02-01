"""Configuration management for MoneyRadar."""

import secrets
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, field_validator
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
    secret_key: Optional[str] = Field(
        default=None,
        description="Flask secret key - REQUIRED for production, use openssl rand -base64 32"
    )
    
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
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: Optional[str], info) -> str:
        """Validate and generate secret key if needed."""
        flask_env = info.data.get('flask_env', 'development')
        
        # Auto-generate for development if missing
        if not v and flask_env == 'development':
            generated = secrets.token_urlsafe(32)
            print(f"⚠️  WARNING: Auto-generated SECRET_KEY for development")
            print(f"⚠️  Add to .env: SECRET_KEY={generated}")
            return generated
        
        # Require in production
        if not v and flask_env == 'production':
            raise ValueError(
                "SECRET_KEY is required in production. Generate with:\n"
                "  openssl rand -base64 32"
            )
        
        # Reject weak keys
        if v and v in ['dev-secret-change-me', 'changeme', 'secret', 'dev']:
            raise ValueError(
                "Weak SECRET_KEY detected. Generate a strong key:\n"
                "  openssl rand -base64 32"
            )
        
        # Require minimum length
        if v and len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        
        return v or secrets.token_urlsafe(32)


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
