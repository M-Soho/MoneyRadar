# MoneyRadar Code Modularization

This document describes the modular architecture of the MoneyRadar codebase.

## Module Structure

### Core Modules

```
monetization_engine/
├── models/              # Data models (6 modules)
│   ├── product.py       # Product and Plan models
│   ├── subscription.py  # Subscription, RevenueEvent, MRRSnapshot
│   ├── usage.py         # UsageRecord model
│   ├── alert.py         # Alert, AlertType, AlertSeverity
│   ├── experiment.py    # Experiment, ExperimentStatus
│   └── customer_score.py # CustomerScore model
│
├── analysis/            # Pricing intelligence (3 modules)
│   ├── mismatch_detector.py  # Usage vs price analysis
│   ├── risk_detector.py      # Revenue risk detection
│   └── expansion_scorer.py   # Customer expansion readiness
│
├── api/                 # REST API (7 route modules)
│   ├── app.py           # Flask app & blueprint registration
│   └── routes/
│       ├── revenue.py   # MRR and revenue endpoints
│       ├── analysis.py  # Mismatch detection endpoints
│       ├── alerts.py    # Alert management endpoints
│       ├── customers.py # Customer scoring endpoints
│       ├── experiments.py # Experiment tracking endpoints
│       ├── webhooks.py  # Stripe webhook handler
│       └── admin.py     # Admin operations
│
├── ingestion/           # Data ingestion
│   ├── __init__.py      # Stripe webhook processing
│   └── usage.py         # Usage tracking
│
├── experiments/         # Experiment tracking
│   └── __init__.py      # ExperimentTracker & ExperimentReporter
│
├── config.py            # Configuration management
├── database.py          # Database session management
├── logging_config.py    # Logging configuration
└── cli.py               # Command-line interface
```

## Design Principles

### 1. Separation of Concerns
Each module has a single, well-defined responsibility:
- **Models**: Pure data definitions
- **Analysis**: Business logic for intelligence
- **API Routes**: HTTP request handling
- **Ingestion**: External data integration

### 2. Dependency Injection
All classes accept a database session (`db: Session`) for easier testing and flexibility.

### 3. Clear Boundaries
- Models contain no business logic
- Analysis modules don't know about HTTP
- Routes are thin wrappers around business logic

### 4. Import Aggregation
Each package exports its public API through `__init__.py`:
```python
from monetization_engine.models import Subscription, Plan
from monetization_engine.analysis import MismatchDetector, RiskDetector
```

## Module Responsibilities

### Models Package
**Purpose**: Define database schema and ORM models

**Modules**:
- `product.py`: Products and pricing plans
- `subscription.py`: Customer subscriptions and revenue events
- `usage.py`: Usage tracking records
- `alert.py`: Revenue risk alerts
- `experiment.py`: Pricing experiments
- `customer_score.py`: Customer expansion scores

**No dependencies**: Models are pure SQLAlchemy definitions

### Analysis Package
**Purpose**: Revenue intelligence and risk detection

**Modules**:
- `mismatch_detector.py`: Detects when customers are on wrong pricing tier
- `risk_detector.py`: Identifies churn risks and revenue threats
- `expansion_scorer.py`: Scores customers for upsell readiness

**Dependencies**: Models only

### API Package
**Purpose**: HTTP interface for all operations

**Architecture**: Flask blueprints for each domain
- Each route module is independent
- Registered in `app.py`
- Clean URL structure (`/api/<domain>/<operation>`)

**Modules**:
- `revenue.py`: MRR insights (`/api/revenue/*`)
- `analysis.py`: Mismatch detection (`/api/analysis/*`)
- `alerts.py`: Alert management (`/api/alerts/*`)
- `customers.py`: Customer intelligence (`/api/customers/*`)
- `experiments.py`: Experiment tracking (`/api/experiments/*`)
- `webhooks.py`: Stripe integration (`/webhooks/*`)
- `admin.py`: Admin operations (`/api/admin/*`)

### Ingestion Package
**Purpose**: External data integration

**Modules**:
- `__init__.py`: Stripe webhook event processing
- `usage.py`: Usage event recording

## Benefits of This Architecture

### ✅ Maintainability
- Small, focused files (50-250 lines each)
- Easy to locate functionality
- Clear ownership of features

### ✅ Testability
- Each module can be tested independently
- Mock dependencies easily
- Clear interfaces

### ✅ Scalability
- New features go in obvious places
- Can split large modules further as needed
- Parallel development possible

### ✅ Onboarding
- New developers can understand one module at a time
- Clear navigation structure
- Self-documenting organization

## Migration Notes

The following large files were broken down:
- `models/__init__.py` (323 lines) → 6 focused modules
- `api/app.py` (394 lines) → 1 app + 7 route modules
- `analysis/risk_detection.py` (384 lines) → 2 focused modules
- `analysis/__init__.py` (231 lines) → Extracted mismatch_detector.py

All original files backed up with `.bak` extension.
All tests passing (9/9) ✓

## Usage Examples

### Import Models
```python
from monetization_engine.models import Product, Plan, Subscription
```

### Import Analysis Tools
```python
from monetization_engine.analysis import MismatchDetector, RiskDetector
```

### Run API Server
```python
from monetization_engine.api.app import app
app.run()
```

### Use CLI
```bash
moneyradar init-db
moneyradar sync
moneyradar analyze
```
