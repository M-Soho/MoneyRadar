"""Monetization Experiments Tracker - Prevent Pricing Amnesia."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from monetization_engine.models import (
    Experiment, ExperimentStatus, Subscription, Plan, RevenueEvent
)


class ExperimentTracker:
    """Track and analyze pricing/packaging experiments."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_experiment(
        self,
        name: str,
        hypothesis: str,
        change_description: str,
        metric_tracked: str,
        affected_segment: Dict[str, Any],
        baseline_value: Optional[float] = None
    ) -> Experiment:
        """Create a new experiment."""
        experiment = Experiment(
            name=name,
            hypothesis=hypothesis,
            change_description=change_description,
            metric_tracked=metric_tracked,
            affected_segment=affected_segment,
            baseline_value=baseline_value,
            status=ExperimentStatus.DRAFT
        )
        
        self.db.add(experiment)
        self.db.commit()
        
        return experiment
    
    def start_experiment(self, experiment_id: int) -> Experiment:
        """Start running an experiment."""
        experiment = self.db.query(Experiment).get(experiment_id)
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if experiment.status != ExperimentStatus.DRAFT:
            raise ValueError(f"Experiment must be in DRAFT status to start")
        
        # Calculate baseline if not set
        if not experiment.baseline_value:
            experiment.baseline_value = self._calculate_metric(
                experiment.metric_tracked,
                experiment.affected_segment
            )
        
        # Count affected customers
        control_size, variant_size = self._count_affected_customers(
            experiment.affected_segment
        )
        
        experiment.control_group_size = control_size
        experiment.variant_group_size = variant_size
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.utcnow()
        
        self.db.commit()
        
        return experiment
    
    def record_result(
        self,
        experiment_id: int,
        actual_value: float,
        outcome: str
    ) -> Experiment:
        """Record experiment results."""
        experiment = self.db.query(Experiment).get(experiment_id)
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment.actual_value = actual_value
        experiment.outcome = outcome
        experiment.status = ExperimentStatus.COMPLETED
        experiment.ended_at = datetime.utcnow()
        
        self.db.commit()
        
        return experiment
    
    def get_active_experiments(self) -> List[Experiment]:
        """Get all running experiments."""
        return self.db.query(Experiment).filter(
            Experiment.status == ExperimentStatus.RUNNING
        ).all()
    
    def get_experiment_history(
        self,
        metric: Optional[str] = None,
        limit: int = 50
    ) -> List[Experiment]:
        """Get historical experiments for learning."""
        query = self.db.query(Experiment).filter(
            Experiment.status == ExperimentStatus.COMPLETED
        )
        
        if metric:
            query = query.filter(Experiment.metric_tracked == metric)
        
        return query.order_by(Experiment.ended_at.desc()).limit(limit).all()
    
    def analyze_experiment(self, experiment_id: int) -> Dict[str, Any]:
        """Analyze experiment performance."""
        experiment = self.db.query(Experiment).get(experiment_id)
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if experiment.status != ExperimentStatus.RUNNING and experiment.status != ExperimentStatus.COMPLETED:
            return {"status": "not_ready", "message": "Experiment not yet started"}
        
        # Calculate current metric value
        current_value = self._calculate_metric(
            experiment.metric_tracked,
            experiment.affected_segment
        )
        
        # Calculate improvement
        baseline = experiment.baseline_value or 0
        improvement = 0
        improvement_percent = 0
        
        if baseline > 0:
            improvement = current_value - baseline
            improvement_percent = (improvement / baseline) * 100
        
        # Determine success
        target_met = False
        if experiment.target_value:
            if experiment.target_value > baseline:
                target_met = current_value >= experiment.target_value
            else:
                target_met = current_value <= experiment.target_value
        
        return {
            "experiment_id": experiment.id,
            "name": experiment.name,
            "status": experiment.status.value,
            "metric": experiment.metric_tracked,
            "baseline_value": baseline,
            "current_value": current_value,
            "target_value": experiment.target_value,
            "improvement": improvement,
            "improvement_percent": improvement_percent,
            "target_met": target_met,
            "days_running": (datetime.utcnow() - experiment.started_at).days if experiment.started_at else 0
        }
    
    def _calculate_metric(
        self,
        metric: str,
        segment: Dict[str, Any]
    ) -> float:
        """Calculate current value of a metric for a segment."""
        # Get subscriptions in segment
        query = self.db.query(Subscription).filter(
            Subscription.status == "active"
        )
        
        # Apply segment filters
        if "plan_id" in segment:
            query = query.filter(Subscription.plan_id == segment["plan_id"])
        
        subscriptions = query.all()
        
        if not subscriptions:
            return 0.0
        
        # Calculate metric
        if metric == "arpu":
            total_mrr = sum(s.mrr for s in subscriptions)
            return total_mrr / len(subscriptions)
        
        elif metric == "conversion_rate":
            # This would need trial data - simplified for now
            return 0.0
        
        elif metric == "churn_rate":
            # Calculate churn rate over last 30 days
            total_subs = len(subscriptions)
            churned = self.db.query(Subscription).filter(
                Subscription.status == "canceled",
                Subscription.canceled_at >= datetime.utcnow() - timedelta(days=30)
            ).count()
            
            if total_subs == 0:
                return 0.0
            
            return (churned / total_subs) * 100
        
        elif metric == "mrr":
            total_mrr = sum(s.mrr for s in subscriptions)
            return total_mrr
        
        else:
            # Unknown metric
            return 0.0
    
    def _count_affected_customers(self, segment: Dict[str, Any]) -> tuple:
        """Count customers in control and variant groups."""
        query = self.db.query(Subscription).filter(
            Subscription.status == "active"
        )
        
        if "plan_id" in segment:
            query = query.filter(Subscription.plan_id == segment["plan_id"])
        
        total = query.count()
        
        # Simple 50/50 split for now
        control = total // 2
        variant = total - control
        
        return (control, variant)


class ExperimentReporter:
    """Generate reports and insights from experiments."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_summary_report(self, experiment_id: int) -> Dict[str, Any]:
        """Generate a summary report for an experiment."""
        experiment = self.db.query(Experiment).get(experiment_id)
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        report = {
            "experiment_id": experiment.id,
            "name": experiment.name,
            "hypothesis": experiment.hypothesis,
            "status": experiment.status.value,
            "metric_tracked": experiment.metric_tracked,
            "baseline_value": experiment.baseline_value,
            "actual_value": experiment.actual_value,
            "target_value": experiment.target_value,
            "outcome": experiment.outcome,
            "started_at": experiment.started_at.isoformat() if experiment.started_at else None,
            "ended_at": experiment.ended_at.isoformat() if experiment.ended_at else None,
        }
        
        # Calculate success metrics
        if experiment.baseline_value and experiment.actual_value:
            improvement = experiment.actual_value - experiment.baseline_value
            improvement_percent = (improvement / experiment.baseline_value) * 100
            report["improvement"] = improvement
            report["improvement_percent"] = improvement_percent
            
            if experiment.target_value:
                report["target_met"] = experiment.actual_value >= experiment.target_value
        
        return report
    
    def get_learnings(self, metric: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get key learnings from past experiments."""
        query = self.db.query(Experiment).filter(
            Experiment.status == ExperimentStatus.COMPLETED
        )
        
        if metric:
            query = query.filter(Experiment.metric_tracked == metric)
        
        experiments = query.order_by(Experiment.ended_at.desc()).limit(20).all()
        
        learnings = []
        for exp in experiments:
            if exp.baseline_value and exp.actual_value:
                improvement = ((exp.actual_value - exp.baseline_value) / exp.baseline_value) * 100
                
                learnings.append({
                    "name": exp.name,
                    "change": exp.change_description,
                    "metric": exp.metric_tracked,
                    "improvement_percent": improvement,
                    "outcome": exp.outcome,
                    "ended_at": exp.ended_at.isoformat() if exp.ended_at else None
                })
        
        return learnings


__all__ = ['ExperimentTracker', 'ExperimentReporter']
