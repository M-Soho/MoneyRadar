"""Alert-related API routes."""

from flask import Blueprint, jsonify, request

from monetization_engine.database import get_db
from monetization_engine.analysis import RiskDetector
from monetization_engine.models import Alert

alerts_bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')


@alerts_bp.route('', methods=['GET'])
def list_alerts():
    """List all alerts."""
    status = request.args.get('status', 'active')
    
    with get_db() as db:
        query = db.query(Alert)
        
        if status == 'active':
            query = query.filter(Alert.is_resolved == False)
        elif status == 'resolved':
            query = query.filter(Alert.is_resolved == True)
        
        alerts = query.order_by(Alert.created_at.desc()).limit(100).all()
        
        return jsonify({
            "alerts": [
                {
                    "id": a.id,
                    "type": a.alert_type.value,
                    "severity": a.severity.value,
                    "customer_id": a.customer_id,
                    "title": a.title,
                    "description": a.description,
                    "recommended_action": a.recommended_action,
                    "created_at": a.created_at.isoformat(),
                    "is_resolved": a.is_resolved
                }
                for a in alerts
            ]
        }), 200


@alerts_bp.route('/scan', methods=['POST'])
def scan_risks():
    """Run risk scan and create new alerts."""
    with get_db() as db:
        detector = RiskDetector(db)
        results = detector.scan_all_risks()
        
        return jsonify({
            "critical": len(results['critical']),
            "warning": len(results['warning']),
            "informational": len(results['informational'])
        }), 200


@alerts_bp.route('/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """Resolve an alert."""
    with get_db() as db:
        alert = db.query(Alert).get(alert_id)
        
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        
        from datetime import datetime
        alert.is_resolved = True
        alert.resolved_at = datetime.now(UTC)
        
        return jsonify({"message": "Alert resolved"}), 200
