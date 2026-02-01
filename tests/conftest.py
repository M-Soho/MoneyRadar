"""Test fixtures and configuration."""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment variables before importing modules
os.environ.setdefault("STRIPE_API_KEY", "sk_test_fake_key_for_testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from monetization_engine.database import Base


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
