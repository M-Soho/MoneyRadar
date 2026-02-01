"""API route blueprints."""

from monetization_engine.api.routes.revenue import revenue_bp
from monetization_engine.api.routes.analysis import analysis_bp
from monetization_engine.api.routes.alerts import alerts_bp
from monetization_engine.api.routes.customers import customers_bp
from monetization_engine.api.routes.experiments import experiments_bp
from monetization_engine.api.routes.webhooks import webhooks_bp
from monetization_engine.api.routes.admin import admin_bp

__all__ = [
    'revenue_bp',
    'analysis_bp',
    'alerts_bp',
    'customers_bp',
    'experiments_bp',
    'webhooks_bp',
    'admin_bp',
]
