"""Administrative API routes."""

from flask import Blueprint, jsonify

from monetization_engine.database import get_db
from monetization_engine.ingestion import StripeIngestion

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/sync-stripe', methods=['POST'])
def sync_stripe():
    """Trigger Stripe sync."""
    with get_db() as db:
        ingestion = StripeIngestion(db)
        ingestion.sync_products_and_plans()
    
    return jsonify({"message": "Sync completed"}), 200


@admin_bp.route('/calculate-mrr-snapshot', methods=['POST'])
def calculate_mrr_snapshot():
    """Calculate MRR snapshot."""
    with get_db() as db:
        ingestion = StripeIngestion(db)
        snapshot = ingestion.calculate_daily_mrr_snapshot()
    
    return jsonify({
        "date": snapshot.date.isoformat(),
        "total_mrr": snapshot.total_mrr
    }), 200
