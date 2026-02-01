"""Revenue-related API routes."""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta, UTC

from monetization_engine.database import get_db
from monetization_engine.ingestion import StripeIngestion
from monetization_engine.models import MRRSnapshot, Subscription
from sqlalchemy import func

revenue_bp = Blueprint('revenue', __name__, url_prefix='/api/revenue')


@revenue_bp.route('/mrr', methods=['GET'])
def get_mrr():
    """Get current MRR and recent trends."""
    with get_db() as db:
        # Current MRR
        current_mrr = db.query(
            func.sum(Subscription.mrr)
        ).filter(Subscription.status == "active").scalar() or 0.0
        
        # Latest snapshot
        latest_snapshot = db.query(MRRSnapshot).order_by(
            MRRSnapshot.date.desc()
        ).first()
        
        return jsonify({
            "current_mrr": current_mrr,
            "latest_snapshot": {
                "date": latest_snapshot.date.isoformat() if latest_snapshot else None,
                "total_mrr": latest_snapshot.total_mrr if latest_snapshot else 0,
                "new_mrr": latest_snapshot.new_mrr if latest_snapshot else 0,
                "expansion_mrr": latest_snapshot.expansion_mrr if latest_snapshot else 0,
                "contraction_mrr": latest_snapshot.contraction_mrr if latest_snapshot else 0,
                "churned_mrr": latest_snapshot.churned_mrr if latest_snapshot else 0
            }
        }), 200


@revenue_bp.route('/snapshots', methods=['GET'])
def get_mrr_snapshots():
    """Get historical MRR snapshots."""
    days = request.args.get('days', 30, type=int)
    
    with get_db() as db:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        snapshots = db.query(MRRSnapshot).filter(
            MRRSnapshot.date >= cutoff
        ).order_by(MRRSnapshot.date).all()
        
        return jsonify({
            "snapshots": [
                {
                    "date": s.date.isoformat(),
                    "total_mrr": s.total_mrr,
                    "new_mrr": s.new_mrr,
                    "expansion_mrr": s.expansion_mrr,
                    "contraction_mrr": s.contraction_mrr,
                    "churned_mrr": s.churned_mrr,
                    "product_breakdown": s.product_breakdown
                }
                for s in snapshots
            ]
        }), 200
