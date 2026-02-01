"""Webhook handlers."""

from flask import Blueprint, request, jsonify
import stripe

from monetization_engine.config import get_settings
from monetization_engine.database import get_db
from monetization_engine.ingestion import StripeIngestion

settings = get_settings()
webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhooks')


@webhooks_bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        if settings.stripe_webhook_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        else:
            event = request.get_json()
        
        # Process event
        with get_db() as db:
            ingestion = StripeIngestion(db)
            ingestion.process_webhook_event(event)
        
        return jsonify({"status": "success"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400
