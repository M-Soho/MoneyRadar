"""MoneyRadar - Revenue Intelligence Engine for SaaS.

A decision engine that identifies revenue opportunities and risks.
Not a billing system - answers: "Where should I adjust pricing, packaging, 
or focus to increase revenue without adding work?"
"""

__version__ = "1.0.0"
__author__ = "M-Soho"
__license__ = "MIT"

from monetization_engine.config import get_settings
from monetization_engine.database import get_db, init_db

__all__ = ["__version__", "__author__", "__license__", "get_settings", "get_db", "init_db"]
