"""Analysis-related API routes."""

from flask import Blueprint, jsonify

from monetization_engine.database import get_db
from monetization_engine.analysis import MismatchDetector

analysis_bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')


@analysis_bp.route('/mismatches', methods=['GET'])
def get_mismatches():
    """Get usage vs price mismatches."""
    with get_db() as db:
        detector = MismatchDetector(db)
        results = detector.analyze_all_subscriptions()
        
        return jsonify({
            "upgrade_candidates": results['upgrade_candidates'],
            "overpriced_customers": results['overpriced_customers']
        }), 200


@analysis_bp.route('/feature-pricing', methods=['GET'])
def analyze_feature_pricing():
    """Detect mispriced features across plans."""
    with get_db() as db:
        detector = MismatchDetector(db)
        results = detector.detect_feature_mispricing()
        
        return jsonify({"mispriced_features": results}), 200
