# Changelog

All notable changes to MoneyRadar will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Modern React-based web UI with interactive dashboard
- Revenue analytics visualization with charts and trends
- Alert management interface with one-click resolution
- Usage mismatch detection UI for upgrade/downgrade opportunities
- Customer expansion scoring interface
- Pricing experiment tracking dashboard
- CORS support in Flask API for frontend integration
- Development startup scripts (Linux/Mac/Windows)
- Enhanced Makefile with UI commands
- Comprehensive UI documentation and quick start guide
- API client with typed methods for all endpoints
- Responsive design with dark mode support
- Chart visualizations using Recharts
- Comprehensive code review and improvement roadmap
- Modern Python tooling configuration
- Development workflow automation

## [1.0.0] - 2026-02-01

### Added
- Initial release of MoneyRadar
- Revenue signal ingestion from Stripe
- Usage vs price mismatch detection
- Revenue risk alert system
- Monetization experiment tracking
- Expansion readiness scoring
- Complete CLI interface
- RESTful API with Flask
- Comprehensive test suite (9 tests, 47% coverage)
- Modular architecture with separated concerns:
  - 6 model modules (product, subscription, usage, alert, experiment, customer_score)
  - 7 API route blueprints (revenue, analysis, alerts, customers, experiments, webhooks, admin)
  - 3 analysis modules (mismatch_detector, risk_detector, expansion_scorer)

### Fixed
- SQLAlchemy reserved keyword conflict (`metadata` → `event_metadata`)
- Import/export issues across modules
- Python 3.9 type hint compatibility

### Documentation
- Complete README with examples
- API reference documentation
- Deployment guide (DEPLOYMENT.md)
- Usage guide (USAGE.md)
- Architecture documentation (ARCHITECTURE.md)

[Unreleased]: https://github.com/M-Soho/MoneyRadar/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/M-Soho/MoneyRadar/releases/tag/v1.0.0
