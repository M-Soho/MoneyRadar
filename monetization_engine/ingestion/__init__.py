"""Stripe event ingestion and processing."""

import stripe
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from monetization_engine.config import get_settings
from monetization_engine.models import (
    Subscription, RevenueEvent, RevenueEventType, MRRSnapshot,
    Product, Plan
)

settings = get_settings()
stripe.api_key = settings.stripe_api_key


class StripeIngestion:
    """Handle Stripe event ingestion and processing."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def sync_products_and_plans(self) -> None:
        """Sync products and plans from Stripe."""
        # Fetch products from Stripe
        stripe_products = stripe.Product.list(active=True, limit=100)
        
        for stripe_product in stripe_products.data:
            # Create or update product
            product = self.db.query(Product).filter(
                Product.stripe_product_id == stripe_product.id
            ).first()
            
            if not product:
                product = Product(
                    name=stripe_product.name,
                    description=stripe_product.description,
                    stripe_product_id=stripe_product.id
                )
                self.db.add(product)
                self.db.flush()
            
            # Fetch prices for this product
            prices = stripe.Price.list(product=stripe_product.id, active=True, limit=100)
            
            for price in prices.data:
                self._create_or_update_plan(product, price)
        
        self.db.commit()
    
    def _create_or_update_plan(self, product: Product, stripe_price: Any) -> Plan:
        """Create or update a plan from Stripe price."""
        # Check if plan exists
        plan = self.db.query(Plan).filter(
            Plan.stripe_price_id == stripe_price.id
        ).first()
        
        if plan:
            return plan
        
        # Determine plan name from metadata or nickname
        plan_name = stripe_price.nickname or f"Plan {stripe_price.id[:8]}"
        
        # Calculate monthly price
        if stripe_price.recurring.interval == "month":
            price_monthly = stripe_price.unit_amount / 100
            price_annual = None
        elif stripe_price.recurring.interval == "year":
            price_annual = stripe_price.unit_amount / 100
            price_monthly = price_annual / 12
        else:
            price_monthly = stripe_price.unit_amount / 100
            price_annual = None
        
        # Extract limits from metadata
        limits = stripe_price.metadata or {}
        
        plan = Plan(
            product_id=product.id,
            name=plan_name,
            price_monthly=price_monthly,
            price_annual=price_annual,
            currency=stripe_price.currency.upper(),
            limits=limits,
            stripe_price_id=stripe_price.id,
            effective_from=datetime.fromtimestamp(stripe_price.created)
        )
        
        self.db.add(plan)
        self.db.commit()
        return plan
    
    def process_webhook_event(self, event_data: Dict[str, Any]) -> None:
        """Process a Stripe webhook event."""
        event_type = event_data.get("type")
        
        handlers = {
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.payment_succeeded": self._handle_payment_succeeded,
            "invoice.payment_failed": self._handle_payment_failed,
        }
        
        handler = handlers.get(event_type)
        if handler:
            handler(event_data["data"]["object"])
    
    def _handle_subscription_created(self, subscription_data: Dict[str, Any]) -> None:
        """Handle subscription.created event."""
        # Find the plan
        stripe_price_id = subscription_data["items"]["data"][0]["price"]["id"]
        plan = self.db.query(Plan).filter(
            Plan.stripe_price_id == stripe_price_id
        ).first()
        
        if not plan:
            print(f"Warning: Plan not found for price {stripe_price_id}")
            return
        
        # Calculate MRR
        mrr = self._calculate_mrr(subscription_data)
        
        # Create subscription record
        subscription = Subscription(
            stripe_subscription_id=subscription_data["id"],
            customer_id=subscription_data["customer"],
            plan_id=plan.id,
            status=subscription_data["status"],
            current_period_start=datetime.fromtimestamp(subscription_data["current_period_start"]),
            current_period_end=datetime.fromtimestamp(subscription_data["current_period_end"]),
            mrr=mrr
        )
        self.db.add(subscription)
        self.db.flush()
        
        # Create revenue event
        event = RevenueEvent(
            subscription_id=subscription.id,
            event_type=RevenueEventType.SUBSCRIPTION_CREATED,
            stripe_event_id=subscription_data["id"],
            amount=mrr,
            mrr_delta=mrr,
            metadata={"plan_name": plan.name}
        )
        self.db.add(event)
        self.db.commit()
    
    def _handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> None:
        """Handle subscription.updated event."""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_data["id"]
        ).first()
        
        if not subscription:
            # If subscription doesn't exist, treat as creation
            self._handle_subscription_created(subscription_data)
            return
        
        # Calculate new MRR
        new_mrr = self._calculate_mrr(subscription_data)
        old_mrr = subscription.mrr
        mrr_delta = new_mrr - old_mrr
        
        # Determine event type
        if mrr_delta > 0:
            event_type = RevenueEventType.SUBSCRIPTION_UPGRADED
        elif mrr_delta < 0:
            event_type = RevenueEventType.SUBSCRIPTION_DOWNGRADED
        else:
            event_type = RevenueEventType.MRR_DELTA
        
        # Update subscription
        subscription.status = subscription_data["status"]
        subscription.mrr = new_mrr
        subscription.current_period_start = datetime.fromtimestamp(subscription_data["current_period_start"])
        subscription.current_period_end = datetime.fromtimestamp(subscription_data["current_period_end"])
        
        # Create revenue event
        if mrr_delta != 0:
            event = RevenueEvent(
                subscription_id=subscription.id,
                event_type=event_type,
                stripe_event_id=subscription_data["id"],
                mrr_delta=mrr_delta,
                metadata={"old_mrr": old_mrr, "new_mrr": new_mrr}
            )
            self.db.add(event)
        
        self.db.commit()
    
    def _handle_subscription_deleted(self, subscription_data: Dict[str, Any]) -> None:
        """Handle subscription.deleted event."""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_data["id"]
        ).first()
        
        if not subscription:
            return
        
        # Update subscription
        subscription.status = "canceled"
        subscription.canceled_at = datetime.utcnow()
        
        # Create revenue event
        event = RevenueEvent(
            subscription_id=subscription.id,
            event_type=RevenueEventType.SUBSCRIPTION_CANCELED,
            stripe_event_id=subscription_data["id"],
            mrr_delta=-subscription.mrr,
            metadata={"canceled_mrr": subscription.mrr}
        )
        self.db.add(event)
        
        # Set MRR to 0
        subscription.mrr = 0.0
        
        self.db.commit()
    
    def _handle_payment_succeeded(self, invoice_data: Dict[str, Any]) -> None:
        """Handle invoice.payment_succeeded event."""
        subscription_id = invoice_data.get("subscription")
        if not subscription_id:
            return
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            event = RevenueEvent(
                subscription_id=subscription.id,
                event_type=RevenueEventType.PAYMENT_SUCCEEDED,
                stripe_event_id=invoice_data["id"],
                amount=invoice_data["amount_paid"] / 100,
                currency=invoice_data["currency"].upper()
            )
            self.db.add(event)
            self.db.commit()
    
    def _handle_payment_failed(self, invoice_data: Dict[str, Any]) -> None:
        """Handle invoice.payment_failed event."""
        subscription_id = invoice_data.get("subscription")
        if not subscription_id:
            return
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            event = RevenueEvent(
                subscription_id=subscription.id,
                event_type=RevenueEventType.PAYMENT_FAILED,
                stripe_event_id=invoice_data["id"],
                amount=invoice_data["amount_due"] / 100,
                currency=invoice_data["currency"].upper(),
                metadata={"attempt_count": invoice_data.get("attempt_count", 1)}
            )
            self.db.add(event)
            self.db.commit()
    
    def _calculate_mrr(self, subscription_data: Dict[str, Any]) -> float:
        """Calculate MRR from subscription data."""
        items = subscription_data["items"]["data"]
        total_mrr = 0.0
        
        for item in items:
            price = item["price"]
            quantity = item["quantity"]
            unit_amount = price["unit_amount"] / 100  # Convert from cents
            
            if price["recurring"]["interval"] == "month":
                mrr = unit_amount * quantity
            elif price["recurring"]["interval"] == "year":
                mrr = (unit_amount * quantity) / 12
            else:
                mrr = 0.0
            
            total_mrr += mrr
        
        return total_mrr
    
    def calculate_daily_mrr_snapshot(self, date: Optional[datetime] = None) -> MRRSnapshot:
        """Calculate and store daily MRR snapshot."""
        if date is None:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if snapshot already exists
        existing = self.db.query(MRRSnapshot).filter(
            MRRSnapshot.date == date
        ).first()
        
        if existing:
            return existing
        
        # Calculate total MRR
        total_mrr = self.db.query(
            func.sum(Subscription.mrr)
        ).filter(
            Subscription.status == "active"
        ).scalar() or 0.0
        
        # Calculate MRR movements for the day
        start_of_day = date
        end_of_day = date + timedelta(days=1)
        
        events = self.db.query(RevenueEvent).filter(
            RevenueEvent.occurred_at >= start_of_day,
            RevenueEvent.occurred_at < end_of_day
        ).all()
        
        new_mrr = 0.0
        expansion_mrr = 0.0
        contraction_mrr = 0.0
        churned_mrr = 0.0
        
        for event in events:
            if event.event_type == RevenueEventType.SUBSCRIPTION_CREATED:
                new_mrr += event.mrr_delta or 0.0
            elif event.event_type == RevenueEventType.SUBSCRIPTION_UPGRADED:
                expansion_mrr += event.mrr_delta or 0.0
            elif event.event_type == RevenueEventType.SUBSCRIPTION_DOWNGRADED:
                contraction_mrr += abs(event.mrr_delta or 0.0)
            elif event.event_type == RevenueEventType.SUBSCRIPTION_CANCELED:
                churned_mrr += abs(event.mrr_delta or 0.0)
        
        # Create snapshot
        snapshot = MRRSnapshot(
            date=date,
            total_mrr=total_mrr,
            new_mrr=new_mrr,
            expansion_mrr=expansion_mrr,
            contraction_mrr=contraction_mrr,
            churned_mrr=churned_mrr
        )
        
        self.db.add(snapshot)
        self.db.commit()
        
        return snapshot
