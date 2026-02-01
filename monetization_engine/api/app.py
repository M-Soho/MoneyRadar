"""Flask API for MoneyRadar.

This module provides the main Flask application and registers
all route blueprints for the MoneyRadar API.
"""

from flask import Flask, jsonify

from monetization_engine.config import get_settings
from monetization_engine.database import init_db
from monetization_engine.api.routes import (
    revenue_bp,
    analysis_bp,
    alerts_bp,
    customers_bp,
    experiments_bp,
    webhooks_bp,
    admin_bp,
)

settings = get_settings()
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.secret_key

# Register blueprints
app.register_blueprint(revenue_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(customers_bp)
app.register_blueprint(experiments_bp)
app.register_blueprint(webhooks_bp)
app.register_blueprint(admin_bp)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "MoneyRadar"}), 200


if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=settings.flask_env == 'development'
    )
