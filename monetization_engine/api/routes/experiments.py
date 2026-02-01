"""Experiment-related API routes."""

from flask import Blueprint, jsonify, request

from monetization_engine.database import get_db
from monetization_engine.experiments import ExperimentTracker

experiments_bp = Blueprint('experiments', __name__, url_prefix='/api/experiments')


@experiments_bp.route('', methods=['GET'])
def list_experiments():
    """List all experiments."""
    with get_db() as db:
        tracker = ExperimentTracker(db)
        active = tracker.get_active_experiments()
        
        return jsonify({
            "experiments": [
                {
                    "id": e.id,
                    "name": e.name,
                    "status": e.status.value,
                    "metric_tracked": e.metric_tracked,
                    "baseline_value": e.baseline_value,
                    "actual_value": e.actual_value
                }
                for e in active
            ]
        }), 200


@experiments_bp.route('', methods=['POST'])
def create_experiment():
    """Create a new experiment."""
    data = request.get_json()
    
    with get_db() as db:
        tracker = ExperimentTracker(db)
        experiment = tracker.create_experiment(
            name=data['name'],
            hypothesis=data['hypothesis'],
            change_description=data['change_description'],
            metric_tracked=data['metric_tracked'],
            affected_segment=data.get('affected_segment', {})
        )
        
        return jsonify({
            "id": experiment.id,
            "name": experiment.name,
            "status": experiment.status.value
        }), 201


@experiments_bp.route('/<int:experiment_id>', methods=['GET'])
def get_experiment(experiment_id):
    """Get experiment details."""
    with get_db() as db:
        tracker = ExperimentTracker(db)
        analysis = tracker.analyze_experiment(experiment_id)
        
        return jsonify(analysis), 200


@experiments_bp.route('/<int:experiment_id>/start', methods=['POST'])
def start_experiment(experiment_id):
    """Start an experiment."""
    with get_db() as db:
        tracker = ExperimentTracker(db)
        experiment = tracker.start_experiment(experiment_id)
        
        return jsonify({
            "id": experiment.id,
            "status": experiment.status.value,
            "baseline_value": experiment.baseline_value
        }), 200


@experiments_bp.route('/<int:experiment_id>/complete', methods=['POST'])
def complete_experiment(experiment_id):
    """Record experiment results."""
    data = request.get_json()
    
    with get_db() as db:
        tracker = ExperimentTracker(db)
        experiment = tracker.record_result(
            experiment_id=experiment_id,
            actual_value=data['actual_value'],
            outcome=data['outcome']
        )
        
        return jsonify({
            "id": experiment.id,
            "status": experiment.status.value,
            "actual_value": experiment.actual_value
        }), 200
