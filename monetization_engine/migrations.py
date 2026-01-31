"""Database migration utilities using Alembic."""

# Initialize alembic if needed
# Run: alembic init alembic

# Migration commands:
# alembic revision --autogenerate -m "Initial migration"
# alembic upgrade head
# alembic downgrade -1

# For now, we use simple SQLAlchemy create_all()
# For production, consider implementing Alembic migrations
