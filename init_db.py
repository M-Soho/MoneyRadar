#!/usr/bin/env python
"""Initialize the MoneyRadar database."""
from monetization_engine.database import init_db

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
