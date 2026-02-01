.PHONY: help install install-dev test lint format clean run-api run-cli docker-build docker-run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev]"

test: ## Run tests with coverage
	pytest tests/ -v --cov=monetization_engine --cov-report=term-missing

test-fast: ## Run tests without coverage
	pytest tests/ -v

lint: ## Run linters (ruff, mypy, black --check)
	ruff check monetization_engine/ tests/
	mypy monetization_engine/
	black --check monetization_engine/ tests/

format: ## Format code with black and ruff
	black monetization_engine/ tests/
	ruff check --fix monetization_engine/ tests/

clean: ## Remove build artifacts and cache
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	rm -rf .pytest_cache .coverage htmlcov/
	rm -f moneyradar.db

init-db: ## Initialize database
	moneyradar init

sync: ## Sync data from Stripe
	moneyradar sync-stripe
	moneyradar calculate-mrr

analyze: ## Run analysis
	moneyradar analyze-mismatches
	moneyradar scan-risks

run-api: ## Start Flask API server
	FLASK_APP=monetization_engine.api.app flask run

run-api-prod: ## Start production API server with Gunicorn
	gunicorn monetization_engine.api.app:app -w 4 -b 0.0.0.0:5000

docker-build: ## Build Docker image
	docker build -t moneyradar:latest .

docker-run: ## Run Docker container
	docker-compose up -d

docker-stop: ## Stop Docker container
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

setup: install-dev init-db ## Complete setup for new developers
	@echo "✅ MoneyRadar setup complete!"
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Run 'make sync' to pull Stripe data"
	@echo "  3. Run 'make test' to verify installation"

coverage: ## Generate HTML coverage report
	pytest tests/ --cov=monetization_engine --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

security: ## Run security checks
	pip install safety bandit
	safety check
	bandit -r monetization_engine/ -ll

pre-commit: lint test ## Run pre-commit checks (lint + test)
	@echo "✅ All pre-commit checks passed!"

release: clean test lint ## Prepare for release
	@echo "Creating release..."
	python -m build
	@echo "✅ Release ready in dist/"
