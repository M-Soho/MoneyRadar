"""Customer intelligence API routes."""

from flask import Blueprint, jsonify

from monetization_engine.database import get_db
from monetization_engine.analysis import ExpansionScorer

customers_bp = Blueprint('customers', __name__, url_prefix='/api/customers')


@customers_bp.route('/<customer_id>/score', methods=['GET'])
def get_customer_score(customer_id):
    """Get expansion readiness score for a customer."""
    with get_db() as db:
        scorer = ExpansionScorer(db)
        
        try:
            score = scorer.score_customer(customer_id)
            
            return jsonify({
                "customer_id": customer_id,
                "expansion_score": score.expansion_score,
                "expansion_category": score.expansion_category,
                "tenure_days": score.tenure_days,
                "usage_trend": score.usage_trend,
                "calculated_at": score.calculated_at.isoformat()
            }), 200
        
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
