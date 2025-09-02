# Makefile for Avito Pipeline Testing Framework
# Production-ready automation for testing, quality checks, and deployment

.PHONY: help install test test-unit test-integration test-e2e test-all
.PHONY: quality-check format lint type-check security coverage clean
.PHONY: build package deploy docs serve-docs
.PHONY: setup-dev setup-ci validate-all pre-commit docker

# Default target
help:
	@echo "🚀 Avito Pipeline Testing Framework - Make Commands"
	@echo "=================================================="
	@echo ""
	@echo "📦 Setup Commands:"
	@echo "  install          Install all dependencies with Poetry"
	@echo "  setup-dev        Setup development environment"  
	@echo "  setup-ci         Setup CI environment"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  test             Run default tests (unit)"
	@echo "  test-unit        Run unit tests with coverage"
	@echo "  test-integration Run integration tests"
	@echo "  test-e2e         Run end-to-end tests"
	@echo "  test-all         Run complete test suite"
	@echo "  test-performance Run performance tests"
	@echo "  test-external    Run external service tests"
	@echo ""
	@echo "🔍 Quality Commands:"
	@echo "  quality-check    Run all quality checks"
	@echo "  format           Format code (Black + isort)"
	@echo "  lint             Run linting (flake8)"
	@echo "  type-check       Run type checking (mypy)"
	@echo "  security         Run security analysis"
	@echo "  validate-all     Run all validation (tests + quality)"
	@echo ""
	@echo "📊 Analysis Commands:"
	@echo "  coverage         Generate coverage reports"
	@echo "  coverage-html    Open coverage HTML report"
	@echo "  benchmark        Run performance benchmarks"
	@echo ""
	@echo "🚀 Build & Deploy Commands:"
	@echo "  build            Build distribution packages"
	@echo "  package          Create release package"
	@echo "  clean            Clean build artifacts"
	@echo ""
	@echo "📚 Documentation Commands:"
	@echo "  docs             Generate documentation"
	@echo "  serve-docs       Serve docs locally"
	@echo ""
	@echo "🐳 Docker Commands:"
	@echo "  docker           Build Docker image"
	@echo "  docker-test      Run tests in Docker"
	@echo ""
	@echo "⚡ Quick Commands:"
	@echo "  dev              Quick development setup"
	@echo "  ci               Full CI pipeline locally"
	@echo "  pre-commit       Run pre-commit hooks"

# Variables
PYTHON := python
POETRY := poetry
PYTEST := $(POETRY) run pytest
COVERAGE := $(POETRY) run coverage
BLACK := $(POETRY) run black
ISORT := $(POETRY) run isort
FLAKE8 := $(POETRY) run flake8
MYPY := $(POETRY) run mypy
BANDIT := $(POETRY) run bandit
SAFETY := $(POETRY) run safety

# Test configurations
UNIT_MARKERS := "unit and not slow"
INTEGRATION_MARKERS := "integration and not external"
E2E_MARKERS := "e2e and not external"
EXTERNAL_MARKERS := "external"
PERFORMANCE_MARKERS := "performance or slow"

# Coverage settings
COVERAGE_THRESHOLD := 90
COVERAGE_DIRS := core pipeline

# ============================================================================
# SETUP COMMANDS
# ============================================================================

install:
	@echo "📦 Installing dependencies..."
	$(POETRY) install --with dev,test
	@echo "✅ Dependencies installed successfully"

setup-dev: install
	@echo "🛠️ Setting up development environment..."
	$(POETRY) run pre-commit install
	@echo "✅ Development environment ready"

setup-ci:
	@echo "🤖 Setting up CI environment..."
	$(POETRY) install --with dev,test --no-root
	@echo "✅ CI environment ready"

# ============================================================================
# TESTING COMMANDS
# ============================================================================

test: test-unit

test-unit:
	@echo "🧪 Running unit tests with coverage..."
	$(PYTEST) tests/ \
		-m $(UNIT_MARKERS) \
		--cov=$(COVERAGE_DIRS) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=$(COVERAGE_THRESHOLD) \
		--junit-xml=junit-unit.xml \
		-v

test-integration:
	@echo "🔗 Running integration tests..."
	$(PYTEST) tests/ \
		-m $(INTEGRATION_MARKERS) \
		--cov=$(COVERAGE_DIRS) \
		--cov-report=xml:coverage-integration.xml \
		--junit-xml=junit-integration.xml \
		--timeout=600 \
		-v

test-e2e:
	@echo "🚀 Running end-to-end tests..."
	$(PYTEST) tests/e2e/ \
		-m $(E2E_MARKERS) \
		--cov=$(COVERAGE_DIRS) \
		--cov-report=xml:coverage-e2e.xml \
		--junit-xml=junit-e2e.xml \
		--timeout=1200 \
		--maxfail=3 \
		-v

test-external:
	@echo "🌐 Running external service tests..."
	@echo "⚠️ Warning: These tests require external service credentials"
	$(PYTEST) tests/ \
		-m $(EXTERNAL_MARKERS) \
		--junit-xml=junit-external.xml \
		--timeout=1800 \
		--maxfail=2 \
		-v

test-performance:
	@echo "⚡ Running performance tests..."
	$(PYTEST) tests/ \
		-m $(PERFORMANCE_MARKERS) \
		--benchmark-json=benchmark-results.json \
		--junit-xml=junit-performance.xml \
		--timeout=1800 \
		-v

test-all:
	@echo "🎯 Running complete test suite..."
	$(PYTEST) tests/ \
		--cov=$(COVERAGE_DIRS) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov-all \
		--cov-report=xml:coverage-all.xml \
		--cov-fail-under=$(COVERAGE_THRESHOLD) \
		--junit-xml=junit-all.xml \
		--timeout=300 \
		--maxfail=15 \
		-v

test-parallel:
	@echo "🚀 Running tests in parallel..."
	$(PYTEST) tests/ \
		-n auto \
		-m $(UNIT_MARKERS) \
		--cov=$(COVERAGE_DIRS) \
		--cov-report=xml:coverage-parallel.xml \
		--junit-xml=junit-parallel.xml \
		-v

# ============================================================================
# QUALITY COMMANDS
# ============================================================================

quality-check:
	@echo "🔍 Running comprehensive quality checks..."
	$(PYTHON) scripts/quality_check.py --all --quality-gate

format:
	@echo "🎨 Formatting code..."
	$(BLACK) .
	$(ISORT) .
	@echo "✅ Code formatted successfully"

format-check:
	@echo "🎨 Checking code formatting..."
	$(BLACK) --check --diff .
	$(ISORT) --check-only --diff .

lint:
	@echo "🔍 Running linter..."
	$(FLAKE8) . --statistics

type-check:
	@echo "🔍 Running type checker..."
	$(MYPY) . --ignore-missing-imports

security:
	@echo "🛡️ Running security analysis..."
	$(BANDIT) -r . -f json -o bandit-report.json || true
	$(SAFETY) check --json --output safety-report.json || true
	@echo "📄 Security reports saved: bandit-report.json, safety-report.json"

validate-all: format-check lint type-check security test-all
	@echo "✅ All validation checks completed successfully!"

# ============================================================================
# COVERAGE COMMANDS
# ============================================================================

coverage:
	@echo "📊 Generating coverage reports..."
	$(COVERAGE) erase
	$(COVERAGE) run -m pytest tests/ -m $(UNIT_MARKERS)
	$(COVERAGE) report --show-missing
	$(COVERAGE) html -d htmlcov
	$(COVERAGE) xml -o coverage.xml
	@echo "✅ Coverage reports generated"

coverage-html: coverage
	@echo "🌐 Opening coverage HTML report..."
	@if command -v xdg-open > /dev/null; then \
		xdg-open htmlcov/index.html; \
	elif command -v open > /dev/null; then \
		open htmlcov/index.html; \
	elif command -v start > /dev/null; then \
		start htmlcov/index.html; \
	else \
		echo "📁 Coverage report available at: htmlcov/index.html"; \
	fi

benchmark:
	@echo "⚡ Running performance benchmarks..."
	$(PYTEST) tests/ \
		-m $(PERFORMANCE_MARKERS) \
		--benchmark-json=benchmark-detailed.json \
		--benchmark-sort=mean \
		--benchmark-verbose

# ============================================================================
# BUILD COMMANDS
# ============================================================================

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .tox/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "coverage*.xml" -delete
	find . -type f -name "junit*.xml" -delete
	find . -type f -name "*-report.json" -delete
	@echo "✅ Cleaned successfully"

build: clean
	@echo "📦 Building distribution packages..."
	$(POETRY) build
	@echo "✅ Build completed"

package: build
	@echo "📦 Creating release package..."
	@echo "Distribution files:"
	@ls -la dist/
	@echo "✅ Package ready for deployment"

# ============================================================================
# DOCUMENTATION COMMANDS
# ============================================================================

docs:
	@echo "📚 Generating documentation..."
	@if [ -d "docs/" ]; then \
		cd docs && make html; \
		echo "✅ Documentation generated"; \
	else \
		echo "❌ Documentation directory not found"; \
	fi

serve-docs: docs
	@echo "🌐 Serving documentation locally..."
	@if [ -d "docs/_build/html" ]; then \
		cd docs/_build/html && $(PYTHON) -m http.server 8080; \
	else \
		echo "❌ Documentation build not found. Run 'make docs' first."; \
	fi

# ============================================================================
# DOCKER COMMANDS
# ============================================================================

docker:
	@echo "🐳 Building Docker image..."
	docker build -t avito-pipeline-tests .
	@echo "✅ Docker image built successfully"

docker-test:
	@echo "🐳 Running tests in Docker..."
	docker run --rm -v $(PWD):/app avito-pipeline-tests make test-all

# ============================================================================
# UTILITY COMMANDS
# ============================================================================

pre-commit:
	@echo "🔧 Running pre-commit hooks..."
	$(POETRY) run pre-commit run --all-files

dev: setup-dev format test-unit
	@echo "🚀 Development environment ready!"

ci: setup-ci validate-all
	@echo "🤖 CI pipeline completed successfully!"

# Advanced test runner
test-runner:
	@echo "🚀 Running advanced test runner..."
	$(PYTHON) scripts/test_runner.py --level full --quality-gate --report

test-quick:
	@echo "⚡ Running quick tests..."
	$(PYTEST) tests/unit/ \
		-m "unit and not slow" \
		--tb=short \
		-q \
		--maxfail=5

test-watch:
	@echo "👁️ Running tests in watch mode..."
	$(PYTEST) tests/unit/ \
		-m "unit and not slow" \
		-f \
		--tb=short

# Database utilities
db-reset:
	@echo "🗄️ Resetting test database..."
	rm -f *.db test*.db
	@echo "✅ Test databases reset"

# Reporting
report-all: test-all coverage benchmark security
	@echo "📊 Generating comprehensive report..."
	@echo "Reports generated:"
	@echo "  - Test results: junit-all.xml"
	@echo "  - Coverage: htmlcov-all/index.html"
	@echo "  - Benchmarks: benchmark-results.json"
	@echo "  - Security: bandit-report.json, safety-report.json"

# Version management
version-patch:
	@echo "📈 Bumping patch version..."
	$(POETRY) version patch
	@echo "New version: $$($(POETRY) version --short)"

version-minor:
	@echo "📈 Bumping minor version..."
	$(POETRY) version minor
	@echo "New version: $$($(POETRY) version --short)"

version-major:
	@echo "📈 Bumping major version..."
	$(POETRY) version major
	@echo "New version: $$($(POETRY) version --short)"

# Environment info
info:
	@echo "ℹ️ Environment Information"
	@echo "========================="
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Poetry: $$($(POETRY) --version)"
	@echo "Project: $$($(POETRY) version)"
	@echo "Dependencies:"
	@$(POETRY) show --tree | head -10

# Health check
health-check:
	@echo "🏥 System Health Check"
	@echo "===================="
	@echo "✅ Python available: $$($(PYTHON) --version)"
	@echo "✅ Poetry available: $$($(POETRY) --version)"
	@echo "✅ Dependencies: $$($(POETRY) check && echo 'OK' || echo 'ISSUES')"
	@echo "✅ Tests: $$(make test-quick > /dev/null 2>&1 && echo 'PASSING' || echo 'FAILING')"
	@echo "✅ Linting: $$($(FLAKE8) . --count --quiet && echo 'CLEAN' || echo 'ISSUES')"

# Show test statistics
test-stats:
	@echo "📊 Test Statistics"
	@echo "=================="
	@echo "Unit tests: $$(find tests/unit -name '*.py' -exec grep -l 'def test_' {} \; | wc -l) files"
	@echo "Integration tests: $$(find tests/integration -name '*.py' -exec grep -l 'def test_' {} \; | wc -l) files"
	@echo "E2E tests: $$(find tests/e2e -name '*.py' -exec grep -l 'def test_' {} \; | wc -l) files"
	@echo "Total test functions: $$(find tests -name '*.py' -exec grep -c 'def test_' {} \; | paste -sd+ - | bc)"