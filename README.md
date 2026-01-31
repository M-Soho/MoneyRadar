# MoneyRadar - Internal Monetization Engine

**Not a billing system. A decision engine.**

MoneyRadar answers one question repeatedly and reliably:  
**"Where should I adjust pricing, packaging, or focus to increase revenue without adding work?"**

## Purpose

This is a revenue intelligence tool designed for solo operators and small teams. It identifies where money is leaking or hiding in your SaaS business by analyzing:

- **Usage vs Price Mismatches** - Who should upgrade? Who's overpaying?
- **Revenue Risk Signals** - Early warnings before customers churn
- **Pricing Experiments** - Track what works, prevent "pricing amnesia"
- **Expansion Opportunities** - Know who's safe to upsell

## Features

### ✅ Core Capabilities (v1)

1. **Revenue Signal Ingestion**
   - Stripe webhook integration
   - Daily/weekly MRR tracking
   - Revenue event aggregation (not invoicing)

2. **Pricing & Plan Map**
   - Canonical source of truth for products/plans/pricing
   - Versioned pricing with effective dates
   - Critical for buyer diligence later

3. **Usage vs Price Mismatch Detection** 🎯
   - Identifies upgrade candidates (heavy usage, low tier)
   - Flags overpriced customers (light usage, high tier)
   - Detects mispriced features across plans

4. **Revenue Risk Alerts**
   - Declining usage detection
   - Payment retry warnings
   - Downgrade tracking
   - MRR decline alerts

5. **Monetization Experiments Tracker**
   - Track pricing hypotheses
   - Measure outcomes (conversion, ARPU, churn)
   - Build evidence over time

### 🔄 Secondary Features (Post v1)

6. **Revenue Attribution** - Simple channel/product attribution
7. **Expansion Readiness Scoring** - Customer scores for upsell safety
8. **Portfolio-Level Health** - Cross-product revenue insights

### ❌ Explicitly Out of Scope

- Invoicing UI
- Tax handling
- Refund workflows
- Coupons & promos
- Customer-facing dashboards
- Complex forecasting

## Quick Start

### Installation

```bash
# Clone repository
cd /workspaces/MoneyRadar

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Required:
# - STRIPE_API_KEY
# - DATABASE_URL (default: SQLite)
```

### Initialize Database

```bash
# Using CLI
moneyradar init

# Or using Python
python -c "from monetization_engine.database import init_db; init_db()"
```

### Sync from Stripe

```bash
# Sync products and plans
moneyradar sync-stripe

# Calculate current MRR snapshot
moneyradar calculate-mrr
```

## Usage

### Command Line Interface

```bash
# Analyze mismatches
moneyradar analyze-mismatches

# Scan for revenue risks
moneyradar scan-risks

# List active alerts
moneyradar list-alerts

# Score a customer for expansion
moneyradar score-customer cus_ABC123

# Manage experiments
moneyradar experiment create --name "Price test" --hypothesis "Increase conversion" --change "Raise Pro $49→$59" --metric arpu
moneyradar experiment list
moneyradar experiment start <id>
moneyradar experiment analyze <id>
```

### API Server

```bash
# Start Flask API
python monetization_engine/api/app.py

# Or using Flask CLI
export FLASK_APP=monetization_engine.api.app
flask run
```

#### API Endpoints

**Revenue Insights**
- `GET /api/revenue/mrr` - Current MRR
- `GET /api/revenue/snapshots?days=30` - Historical MRR

**Analysis**
- `GET /api/analysis/mismatches` - Usage vs price mismatches
- `GET /api/analysis/feature-pricing` - Mispriced features

**Alerts**
- `GET /api/alerts` - List alerts
- `POST /api/alerts/scan` - Run risk scan
- `POST /api/alerts/<id>/resolve` - Resolve alert

**Customer Intelligence**
- `GET /api/customers/<id>/score` - Expansion readiness

**Experiments**
- `GET /api/experiments` - List experiments
- `POST /api/experiments` - Create experiment
- `GET /api/experiments/<id>` - Get details
- `POST /api/experiments/<id>/start` - Start experiment
- `POST /api/experiments/<id>/complete` - Record results

**Webhooks**
- `POST /webhooks/stripe` - Stripe webhook handler

**Admin**
- `POST /api/admin/sync-stripe` - Trigger Stripe sync
- `POST /api/admin/calculate-mrr-snapshot` - Calculate MRR

## Architecture

```
monetization_engine/
├── models/           # Database models (SQLAlchemy)
├── ingestion/        # Stripe event processing & usage tracking
├── analysis/         # Mismatch detection, risk analysis
├── experiments/      # A/B test tracking
├── api/              # Flask REST API
├── config.py         # Configuration management
├── database.py       # Database setup
└── cli.py            # Command-line interface
```

## Integration

### Stripe Webhooks

Configure in Stripe Dashboard:
- URL: `https://your-domain.com/webhooks/stripe`
- Events: `customer.subscription.*`, `invoice.payment_*`

### OPSP Integration (Optional)

Set environment variables:
```bash
OPSP_API_URL=http://localhost:8000/api
OPSP_API_KEY=your-key
```

Alerts can be forwarded to OPSP for visibility in your main dashboard.

## Database Schema

- **Products & Plans** - Versioned pricing catalog
- **Subscriptions** - Customer subscription state
- **Revenue Events** - Stripe event log with MRR deltas
- **MRR Snapshots** - Daily aggregated metrics
- **Usage Records** - Customer usage tracking
- **Alerts** - Risk warnings and opportunities
- **Experiments** - Pricing test tracking
- **Customer Scores** - Expansion readiness

## Development

```bash
# Run tests
pytest

# Format code
black monetization_engine/

# Type checking
mypy monetization_engine/

# Linting
flake8 monetization_engine/
```

## Production Deployment

### Scheduled Jobs

Set up cron jobs or task scheduler:

```bash
# Daily MRR snapshot (run at midnight)
0 0 * * * cd /app && moneyradar calculate-mrr

# Sync Stripe (hourly)
0 * * * * cd /app && moneyradar sync-stripe

# Risk scan (every 6 hours)
0 */6 * * * cd /app && moneyradar scan-risks
```

### Database

For production, use PostgreSQL:

```bash
DATABASE_URL=postgresql://user:password@host:5432/moneyradar
```

### API Deployment

Use Gunicorn for production:

```bash
pip install gunicorn
gunicorn monetization_engine.api.app:app -w 4 -b 0.0.0.0:5000
```

## Key Decisions

1. **Not a Billing System** - Uses Stripe as source of truth
2. **Aggregation Only** - No invoice generation or payment processing
3. **Simple Attribution** - No complex multi-touch models
4. **Evidence-Based** - Experiments build pricing knowledge over time
5. **Solo-Optimized** - Minimal maintenance, maximum insight

## License

MIT License - See LICENSE file

## Support

This is an internal tool. For issues or questions, open a GitHub issue.