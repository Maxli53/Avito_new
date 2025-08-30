# Snowmobile Product Reconciliation - Makefile
# Enforces Universal Development Standards

.DEFAULT_GOAL := help
SHELL := /bin/bash

# Project Configuration
PROJECT_NAME := snowmobile-reconciliation
PYTHON_VERSION := 3.10
MIN_COVERAGE := 80

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# === SETUP ===
install:
	@echo "$(GREEN)Installing project dependencies...$(NC)"
	poetry install --with dev,test
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: install
	@echo "$(GREEN)Installing development tools...$(NC)"
	poetry run pre-commit install
	@echo "$(GREEN)✓ Pre-commit hooks installed$(NC)"

setup: install-dev
	@echo "$(GREEN)Setting up development environment...$(NC)"
	@if ! command -v createdb >/dev/null 2>&1; then \
		echo "$(RED)❌ PostgreSQL not found. Install PostgreSQL first.$(NC)"; \
		exit 1; \
	fi
	@echo "Creating development database..."
	-createdb $(PROJECT_NAME)_dev 2>/dev/null || echo "Database may already exist"
	@echo "Running database migrations..."
	poetry run alembic upgrade head
	@echo "$(GREEN)✓ Development environment ready$(NC)"

# === TESTING ===
test:
	@echo "$(GREEN)Running test suite...$(NC)"
	poetry run pytest tests/ -v --tb=short

test-unit:
	@echo "$(GREEN)Running unit tests...$(NC)"
	poetry run pytest tests/unit/ -v

test-integration:
	@echo "$(GREEN)Running integration tests...$(NC)"
	poetry run pytest tests/integration/ -v --tb=short

test-pipeline:
	@echo "$(GREEN)Running pipeline tests...$(NC)"
	poetry run pytest tests/unit/pipeline/ tests/integration/ -v -m pipeline

test-coverage:
	@echo "$(GREEN)Running tests with coverage analysis...$(NC)"
	poetry run pytest tests/ --cov=src --cov-report=html --cov-report=term --cov-fail-under=$(MIN_COVERAGE)
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

test-fast:
	@echo "$(GREEN)Running fast test subset...$(NC)"
	poetry run pytest tests/unit/ -v --tb=line -x

# === CODE QUALITY ===
lint:
	@echo "$(GREEN)Running code linting...$(NC)"
	poetry run ruff check src/ tests/
	@echo "$(GREEN)✓ Ruff linting passed$(NC)"

format:
	@echo "$(GREEN)Formatting code...$(NC)"
	poetry run black src/ tests/
	poetry run ruff check --fix src/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

type-check:
	@echo "$(GREEN)Running type checking...$(NC)"
	poetry run mypy src/ --strict
	@echo "$(GREEN)✓ Type checking passed$(NC)"

# === SECURITY ===
security-scan:
	@echo "$(GREEN)Running security scans...$(NC)"
	poetry run bandit -r src/ -f json -o security-report.json || poetry run bandit -r src/
	poetry run safety check --json || poetry run safety check
	@echo "$(GREEN)✓ Security scans completed$(NC)"

check-secrets:
	@echo "$(GREEN)Checking for hardcoded secrets...$(NC)"
	@if grep -r "sk-ant-\|AKIA\|password\s*=" src/ --include="*.py" | grep -v test; then \
		echo "$(RED)❌ Hardcoded secrets found$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ No hardcoded secrets$(NC)"

# === ANTI-DECEPTION VALIDATION ===
check-hardcoded:
	@echo "$(GREEN)Checking for hardcoded values...$(NC)"
	@if grep -r "0\.9[0-9]" src/ --include="*.py" | grep -v test; then \
		echo "$(RED)❌ Hardcoded confidence scores found$(NC)"; \
		exit 1; \
	fi
	@if grep -r "TODO\|FIXME\|HACK" src/ --include="*.py"; then \
		echo "$(RED)❌ TODO/FIXME/HACK comments in production code$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ No hardcoded values found$(NC)"

check-facades:
	@echo "$(GREEN)Checking for facade patterns...$(NC)"
	@if find src/ -name "*.js" -o -name "*.ts" | grep -q .; then \
		echo "$(RED)❌ JavaScript files found in src/$(NC)"; \
		exit 1; \
	fi
	@if grep -r "mock\|Mock" src/ --include="*.py" | grep -v test; then \
		echo "$(RED)❌ Mock objects in production code$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ No facade patterns detected$(NC)"

# === PIPELINE SPECIFIC ===
test-base-model-matching:
	@echo "$(GREEN)Testing base model matching stage...$(NC)"
	poetry run pytest tests/unit/pipeline/test_base_model_matching.py -v

test-inheritance-pipeline:
	@echo "$(GREEN)Testing complete inheritance pipeline...$(NC)"
	poetry run pytest tests/integration/test_inheritance_pipeline.py -v

test-claude-integration:
	@echo "$(GREEN)Testing Claude API integration...$(NC)"
	poetry run pytest tests/unit/services/test_claude_enrichment.py -v

validate-models:
	@echo "$(GREEN)Validating Pydantic models...$(NC)"
	poetry run python -c "from src.models.domain import *; print('All models imported successfully')"
	@echo "$(GREEN)✓ Pydantic models valid$(NC)"

# === DATABASE ===
db-migrate:
	@echo "$(GREEN)Running database migrations...$(NC)"
	poetry run alembic upgrade head
	@echo "$(GREEN)✓ Database migrated$(NC)"

db-rollback:
	@echo "$(GREEN)Rolling back last migration...$(NC)"
	poetry run alembic downgrade -1

db-reset:
	@echo "$(YELLOW)Resetting development database...$(NC)"
	-dropdb $(PROJECT_NAME)_dev 2>/dev/null
	createdb $(PROJECT_NAME)_dev
	poetry run alembic upgrade head
	@echo "$(GREEN)✓ Database reset$(NC)"

db-backup:
	@echo "$(GREEN)Creating database backup...$(NC)"
	@mkdir -p backups
	pg_dump $(PROJECT_NAME)_dev > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Database backed up$(NC)"

# === PERFORMANCE ===
benchmark:
	@echo "$(GREEN)Running performance benchmarks...$(NC)"
	poetry run python scripts/benchmark_pipeline.py
	@echo "$(GREEN)✓ Benchmarks completed$(NC)"

profile-pipeline:
	@echo "$(GREEN)Profiling pipeline performance...$(NC)"
	poetry run python -m cProfile -o profile.stats scripts/run_sample_pipeline.py
	poetry run python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

memory-profile:
	@echo "$(GREEN)Memory profiling pipeline...$(NC)"
	poetry run mprof run scripts/run_sample_pipeline.py
	poetry run mprof plot --output memory-profile.png

# === COMPREHENSIVE VALIDATION ===
validate-all: check-hardcoded check-facades check-secrets lint type-check test-coverage security-scan
	@echo "$(GREEN)🎉 ALL VALIDATION CHECKS PASSED! 🎉$(NC)"
	@echo "$(GREEN)✓ Code quality: Excellent$(NC)"
	@echo "$(GREEN)✓ Type safety: 100% mypy --strict$(NC)"
	@echo "$(GREEN)✓ Test coverage: ≥$(MIN_COVERAGE)%$(NC)"
	@echo "$(GREEN)✓ Security: No vulnerabilities$(NC)"
	@echo "$(GREEN)✓ Anti-deception: No hardcoded values$(NC)"

pre-commit-all:
	@echo "$(GREEN)Running all pre-commit hooks...$(NC)"
	poetry run pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

# === DOCUMENTATION ===
docs-generate:
	@echo "$(GREEN)Generating documentation...$(NC)"
	poetry run sphinx-build -b html docs/ docs/_build/html
	@echo "$(GREEN)✓ Documentation generated$(NC)"

docs-serve:
	@echo "$(GREEN)Serving documentation at http://localhost:8080$(NC)"
	poetry run python -m http.server 8080 --directory docs/_build/html

# === DEPLOYMENT ===
build:
	@echo "$(GREEN)Building application...$(NC)"
	docker build -t $(PROJECT_NAME):latest .
	@echo "$(GREEN)✓ Application built$(NC)"

deploy-staging: validate-all build
	@echo "$(GREEN)Deploying to staging...$(NC)"
	docker-compose -f docker-compose.staging.yml up -d
	@echo "$(GREEN)✓ Deployed to staging$(NC)"

deploy-prod: validate-all build
	@echo "$(YELLOW)Production deployment requires manual approval$(NC)"
	@read -p "Deploy to production? (yes/no): " confirm && [ "$confirm" = "yes" ]
	docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✓ Deployed to production$(NC)"

# === MONITORING ===
health-check:
	@echo "$(GREEN)Performing health check...$(NC)"
	@curl -f http://localhost:8000/health || echo "$(RED)Service not responding$(NC)"

logs:
	@echo "$(GREEN)Showing application logs...$(NC)"
	tail -f logs/app_$(shell date +%Y-%m-%d).log

# === CLEANUP ===
clean:
	@echo "$(GREEN)Cleaning up temporary files...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov/ .mypy_cache/
	rm -rf dist/ build/ *.egg-info/
	rm -f profile.stats security-report.json memory-profile.png
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

clean-all: clean
	@echo "$(GREEN)Deep cleanup...$(NC)"
	docker system prune -f
	docker volume prune -f
	@echo "$(GREEN)✓ Deep cleanup completed$(NC)"

# === DEVELOPER TOOLS ===
shell:
	@echo "$(GREEN)Starting development shell...$(NC)"
	poetry shell

install-claude:
	@echo "$(GREEN)Installing Claude CLI (optional)...$(NC)"
	pip install anthropic

setup-vscode:
	@echo "$(GREEN)Setting up VS Code workspace...$(NC)"
	@mkdir -p .vscode
	@echo '{"python.defaultInterpreterPath": "./venv/bin/python", "python.linting.mypyEnabled": true, "python.formatting.provider": "black"}' > .vscode/settings.json
	@echo "$(GREEN)✓ VS Code configured$(NC)"

# === INFORMATION ===
info:
	@echo "$(GREEN)=== Project Information ===$(NC)"
	@echo "Project: $(PROJECT_NAME)"
	@echo "Poetry: $(shell poetry --version 2>/dev/null || echo 'Not installed')"
	@echo "Python: $(shell python --version 2>/dev/null || echo 'Not found')"
	@echo "Environment: $(shell poetry env info --path 2>/dev/null || echo 'No environment')"
	@echo ""
	@echo "Dependencies:"
	@poetry show --tree 2>/dev/null | head -10 || echo "Run 'make install' first"

env-info:
	@echo "$(GREEN)=== Environment Variables ===$(NC)"
	@env | grep -E "(DATABASE|CLAUDE|API|SECRET)" | sort || echo "No relevant environment variables found"

status:
	@echo "$(GREEN)=== Project Status ===$(NC)"
	@echo "Git status:"
	@git status --porcelain || echo "Not a git repository"
	@echo ""
	@echo "Last commit:"
	@git log -1 --oneline 2>/dev/null || echo "No commits yet"

# === HELP ===
help:
	@echo "$(GREEN)Available commands:$(NC)"
	@echo ""
	@echo "$(YELLOW)Setup:$(NC)"
	@echo "  install          Install project dependencies"
	@echo "  install-dev      Install with development tools"
	@echo "  setup           Complete development environment setup"
	@echo ""
	@echo "$(YELLOW)Testing:$(NC)"
	@echo "  test            Run complete test suite"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests"
	@echo "  test-coverage   Run tests with coverage (≥$(MIN_COVERAGE)%)"
	@echo "  test-pipeline   Run pipeline-specific tests"
	@echo ""
	@echo "$(YELLOW)Code Quality:$(NC)"
	@echo "  lint            Check code with ruff"
	@echo "  format          Format code with black + ruff"
	@echo "  type-check      Run mypy --strict type checking"
	@echo "  security-scan   Run security analysis"
	@echo ""
	@echo "$(YELLOW)Validation:$(NC)"
	@echo "  validate-all    Run ALL validation checks (required)"
	@echo "  check-hardcoded Check for hardcoded values"
	@echo "  check-facades   Check for facade patterns"
	@echo "  check-secrets   Check for hardcoded secrets"
	@echo ""
	@echo "$(YELLOW)Database:$(NC)"
	@echo "  db-migrate      Run database migrations"
	@echo "  db-rollback     Rollback last migration"
	@echo "  db-reset        Reset development database"
	@echo ""
	@echo "$(YELLOW)Performance:$(NC)"
	@echo "  benchmark       Run performance benchmarks"
	@echo "  profile-pipeline Profile pipeline performance"
	@echo ""
	@echo "$(YELLOW)Deployment:$(NC)"
	@echo "  build           Build Docker image"
	@echo "  deploy-staging  Deploy to staging (after validation)"
	@echo "  deploy-prod     Deploy to production (with approval)"
	@echo ""
	@echo "$(YELLOW)Information:$(NC)"
	@echo "  info            Show project information"
	@echo "  status          Show project status"
	@echo "  help            Show this help message"

# === SERVE COMMAND ===
serve:
	@echo "$(GREEN)Starting development server...$(NC)"
	poetry run python src/main.py

# Prevent make from interpreting targets as files
.PHONY: install install-dev setup test test-unit test-integration test-coverage test-fast lint format type-check security-scan check-secrets check-hardcoded check-facades validate-all pre-commit-all docs-generate docs-serve build deploy-staging deploy-prod health-check logs clean clean-all shell info env-info status help serve