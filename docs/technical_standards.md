# Technical Standards & Quality Framework
**Enterprise-Grade Development Standards for Snowmobile Reconciliation System**

## 🚨 Non-Negotiable Development Standards

### Immediate Rejection Criteria
**Project automatically rejected if ANY found:**
- Using `requirements.txt` instead of Poetry
- Using dataclasses instead of Pydantic for business data
- mypy --strict reporting any errors
- Test coverage below 80%
- Hardcoded values outside test files
- TODO/FIXME/HACK comments in production code
- Missing pre-commit hooks or hooks failing
- JavaScript/TypeScript files in src/ directory

### Project Foundation Requirements

#### Poetry Configuration (pyproject.toml)
```toml
[tool.poetry]
name = "snowmobile-reconciliation"
version = "1.0.0"
description = "Snowmobile Product Data Reconciliation System"

[tool.poetry.dependencies]
python = "^3.10"
pydantic = "^2.0"              # Data validation (MANDATORY)
loguru = "^0.7"                # Structured logging
typer = "^0.9"                 # CLI interface
fastapi = "^0.100"             # API framework
sqlalchemy = "^2.0"            # Database ORM
alembic = "^1.11"              # Database migrations
asyncpg = "^0.28"              # PostgreSQL async driver
httpx = "^0.25"                # HTTP client for Claude API

[tool.poetry.group.dev.dependencies]
pytest = "^7.4"
pytest-cov = "^4.1"
pytest-asyncio = "^0.21"
mypy = "^1.5"
black = "^23.0"
ruff = "^0.1"
pre-commit = "^3.4"
hypothesis = "^6.88"           # Property-based testing

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
disallow_untyped_defs = true
check_untyped_defs = true

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = [
    "--cov=src",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--fail-under=80",
    "--strict-markers",
    "--asyncio-mode=auto"
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "performance: Performance tests",
    "system: System tests",
    "slow: Slow running tests"
]

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "def __repr__", 
    "raise AssertionError",
    "raise NotImplementedError"
]
```

## 🏗️ Architecture Patterns - Mandatory

### Pydantic Models - All Data Structures
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum

class ProcessingStage(str, Enum):
    PDF_PROCESSING = "pdf_processing"
    BASE_MODEL_MATCHING = "base_model_matching"
    SPECIFICATION_INHERITANCE = "specification_inheritance"
    VARIANT_SELECTION = "variant_selection"
    SPRING_OPTIONS = "spring_options"
    FINAL_VALIDATION = "final_validation"
    HTML_GENERATION = "html_generation"

class ProductModel(BaseModel):
    """Core product model with validation"""
    sku: str = Field(min_length=1, max_length=20)
    brand: str = Field(min_length=1, max_length=50)
    model_year: int = Field(ge=2020, le=2030)
    model_family: Optional[str] = Field(None, max_length=100)
    platform: Optional[str] = Field(None, max_length=50)
    
    # Core specifications
    engine_model: Optional[str] = Field(None, max_length=100)
    engine_displacement_cc: Optional[int] = Field(None, gt=0)
    track_length_mm: Optional[int] = Field(None, gt=0)
    track_width_mm: Optional[int] = Field(None, gt=0)
    dry_weight_kg: Optional[int] = Field(None, gt=0)
    
    # Complete specifications
    full_specifications: Dict[str, Any] = Field(default_factory=dict)
    spring_modifications: Dict[str, Any] = Field(default_factory=dict)
    
    # Quality metrics
    confidence_score: Decimal = Field(ge=0.0, le=1.0, decimal_places=2)
    validation_status: str = Field(default="pending")
    auto_accepted: bool = Field(default=False)
    
    # Audit trail
    inheritance_audit_trail: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('sku')
    def sku_must_be_alphanumeric(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('SKU must be alphanumeric')
        return v.upper()
    
    @validator('confidence_score')
    def confidence_must_be_realistic(cls, v):
        # Prevent hardcoded high confidence scores
        if v > 0.99:
            raise ValueError('Confidence score suspiciously high')
        return v

class PipelineStageResult(BaseModel):
    """Result from individual pipeline stage"""
    stage: ProcessingStage
    success: bool
    confidence_score: Decimal = Field(ge=0.0, le=1.0, decimal_places=2)
    processing_time_ms: int = Field(gt=0)
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    
    @validator('confidence_score')
    def validate_confidence_realism(cls, v, values):
        # Realistic confidence validation
        if values.get('success') and v < 0.1:
            raise ValueError('Successful stage cannot have extremely low confidence')
        return v

class ClaudeAPIRequest(BaseModel):
    """Claude API request tracking"""
    request_id: str
    prompt_tokens: int = Field(gt=0)
    completion_tokens: int = Field(gt=0)
    cost_usd: Decimal = Field(ge=0.0, decimal_places=4)
    processing_time_ms: int = Field(gt=0)
    confidence_achieved: Decimal = Field(ge=0.0, le=1.0)
    
    @validator('cost_usd')
    def validate_realistic_cost(cls, v, values):
        # Detect unrealistic cost values
        tokens = values.get('prompt_tokens', 0) + values.get('completion_tokens', 0)
        if tokens > 1000 and v < 0.01:
            raise ValueError('Cost too low for token count')
        return v
```

### Repository Pattern - Data Access Layer
```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

T = TypeVar('T', bound=BaseModel)

class BaseRepository(ABC, Generic[T]):
    """Abstract base repository with comprehensive error handling"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logger.bind(component=self.__class__.__name__)
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity with validation"""
        pass
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID with proper error handling"""
        pass
    
    @abstractmethod
    async def update(self, id: str, updates: Dict[str, Any]) -> T:
        """Update entity with validation"""
        pass
    
    @abstractmethod
    async def list_with_filters(self, filters: Dict[str, Any]) -> List[T]:
        """List entities with complex filtering"""
        pass

class ProductRepository(BaseRepository[ProductModel]):
    """Product repository with performance optimization"""
    
    async def create(self, product: ProductModel) -> ProductModel:
        """Create product with comprehensive validation"""
        try:
            # Validate business rules
            await self._validate_business_rules(product)
            
            # Create database record
            db_product = await self._create_db_record(product)
            
            # Log success
            self.logger.info(
                "Product created",
                extra={
                    "sku": product.sku,
                    "brand": product.brand,
                    "confidence": float(product.confidence_score)
                }
            )
            
            return product
            
        except Exception as e:
            self.logger.error(
                "Product creation failed",
                extra={
                    "sku": product.sku,
                    "error": str(e)
                }
            )
            raise RepositoryError(f"Failed to create product {product.sku}: {e}")
    
    async def get_high_confidence_products(self, 
                                         threshold: Decimal = Decimal('0.95')) -> List[ProductModel]:
        """Get products suitable for HTML generation"""
        
        query = """
        SELECT * FROM products 
        WHERE confidence_score >= %s 
          AND validation_status = 'passed'
          AND auto_accepted = TRUE
          AND deleted_at IS NULL
        ORDER BY confidence_score DESC, created_at DESC
        """
        
        return await self._execute_query_to_models(query, [threshold])
```

### Service Layer - Business Logic
```python
class InheritancePipelineService:
    """Core business logic with comprehensive validation"""
    
    def __init__(self, 
                 product_repo: ProductRepository,
                 claude_service: ClaudeEnrichmentService,
                 config: PipelineConfig):
        self.product_repo = product_repo
        self.claude_service = claude_service
        self.config = config
        self.logger = logger.bind(component="InheritancePipeline")
    
    async def process_model_code(self, 
                               model_code: str,
                               price_entry_data: Dict[str, Any]) -> ProcessingResult:
        """Process single model code through complete pipeline"""
        
        processing_start = datetime.utcnow()
        stage_results = []
        
        try:
            # Stage 1: Base Model Matching
            stage_1 = await self._execute_stage_1(model_code, price_entry_data)
            stage_results.append(stage_1)
            
            if not stage_1.success:
                return ProcessingResult(
                    success=False, 
                    error="Stage 1 failed",
                    stage_results=stage_results
                )
            
            # Stage 2: Specification Inheritance
            stage_2 = await self._execute_stage_2(stage_1.data)
            stage_results.append(stage_2)
            
            # Continue through all stages...
            # [Stages 3-6 implementation]
            
            # Calculate final confidence
            final_confidence = self._calculate_final_confidence(stage_results)
            
            # Create product
            product = await self._create_final_product(stage_results, final_confidence)
            
            return ProcessingResult(
                success=True,
                product=product,
                stage_results=stage_results,
                processing_time=datetime.utcnow() - processing_start
            )
            
        except Exception as e:
            self.logger.error(
                "Pipeline processing failed",
                extra={
                    "model_code": model_code,
                    "error": str(e),
                    "completed_stages": len(stage_results)
                }
            )
            raise ProcessingError(f"Pipeline failed at stage {len(stage_results) + 1}: {e}")
```

## 🧪 Reality-First Testing Methodology

### 5-Tier Testing Architecture

#### Tier 1: Unit Tests (30% effort) - Real Data Components
```python
class TestPDFExtraction:
    """Unit tests using real PDF samples"""
    
    @pytest.fixture(scope="class")
    def real_pdf_samples(self):
        """Real production PDF samples for testing"""
        return {
            "lynx_2026": Path("tests/fixtures/pdfs/lynx_2026_sample.pdf"),
            "skidoo_2025": Path("tests/fixtures/pdfs/skidoo_2025_sample.pdf"),
            "poor_quality": Path("tests/fixtures/pdfs/scanned_poor_quality.pdf")
        }
    
    async def test_extract_ltta_from_real_lynx_pdf(self, real_pdf_samples):
        """Test LTTA extraction from actual Lynx PDF"""
        pdf_path = real_pdf_samples["lynx_2026"]
        
        extractor = PDFExtractor()
        result = await extractor.extract_model_data(pdf_path, "LTTA")
        
        # Test against known real values
        assert result.model_code == "LTTA"
        assert result.brand == "Lynx"
        assert result.model_family == "Rave RE"
        assert result.engine == "600R E-TEC"
        assert result.price_eur == 18750.00
        assert result.confidence >= 0.95
    
    @pytest.mark.parametrize("model_code,expected_brand,expected_engine", [
        ("LTTA", "Lynx", "600R E-TEC"),
        ("MVTL", "Lynx", "850 E-TEC"),
        ("AYTS", "Ski-Doo", "900 ACE Turbo R"),
    ])
    async def test_real_model_codes(self, model_code, expected_brand, expected_engine):
        """Test multiple real model codes with known results"""
        extractor = PDFExtractor()
        result = await extractor.extract_model_data(
            get_pdf_for_brand(expected_brand), model_code
        )
        
        assert result.brand == expected_brand
        assert expected_engine in result.engine
        assert result.confidence >= 0.85
```

#### Tier 2: Integration Tests (35% effort) - Complete Workflows
```python
class TestCompleteInheritancePipeline:
    """Integration tests with real production flows"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ltta_complete_pipeline_real_data(self):
        """Test LTTA through complete 6-stage pipeline"""
        
        # Use real production configuration
        pipeline = InheritancePipeline(
            config=ProductionPipelineConfig(),
            enable_claude_api=True,
            enable_database=True
        )
        
        # Process real LTTA entry
        result = await pipeline.process_model_code(
            "LTTA", 
            real_lynx_price_entry_data
        )
        
        # Validate against known specifications
        assert result.success is True
        assert result.product.brand == "Lynx"
        assert result.product.model_family == "Rave RE" 
        assert result.product.engine_model == "600R E-TEC"
        assert result.product.confidence_score >= Decimal('0.95')
        
        # Validate complete specification inheritance
        assert len(result.product.full_specifications) >= 50
        assert "suspension" in result.product.full_specifications
        assert "track" in result.product.full_specifications
        
        # Validate audit trail completeness
        assert len(result.stage_results) == 6
        assert all(stage.success for stage in result.stage_results)
```

#### Tier 3: System Tests (20% effort) - Production Simulation
```python
class TestProductionSystemBehavior:
    """System tests simulating real production loads"""
    
    @pytest.mark.system
    @pytest.mark.expensive
    async def test_complete_price_list_processing(self):
        """Process complete real price list"""
        
        # Use actual production price list
        price_list_pdf = "tests/fixtures/pdfs/lynx_2026_complete.pdf"
        
        system = ProductionSystem(
            claude_api_key=os.getenv("CLAUDE_API_KEY_TEST"),
            database_url=os.getenv("TEST_DATABASE_URL")
        )
        
        # Process entire price list
        start_time = time.time()
        results = await system.process_complete_price_list(price_list_pdf)
        processing_time = time.time() - start_time
        
        # Production requirements
        assert len(results.processed_products) >= 50
        assert results.success_rate >= 0.95
        assert results.average_confidence >= 0.90
        assert processing_time <= 1800  # Complete in under 30 minutes
        
        # Cost validation
        assert results.total_api_cost <= 25.00
        
        # Quality validation
        manual_review_count = results.manual_review_required_count
        assert manual_review_count <= len(results.processed_products) * 0.05
```

#### Tier 4: Performance Tests (10% effort) - Load Validation
```python
class TestPerformanceRequirements:
    """Validate performance under production loads"""
    
    @pytest.mark.performance
    async def test_concurrent_processing_load(self):
        """Test concurrent processing with real load patterns"""
        
        model_codes = ["LTTA", "MVTL", "LUTC", "AYTS", "UJTB"]
        
        async def process_model_code(code):
            pipeline = InheritancePipeline(ProductionConfig())
            start_time = time.time()
            result = await pipeline.process_model_code(code, get_test_data(code))
            return result, time.time() - start_time
        
        # Execute concurrent processing
        tasks = [process_model_code(code) for code in model_codes]
        results = await asyncio.gather(*tasks)
        
        processing_times = [time for _, time in results]
        successful_results = [result for result, _ in results if result.success]
        
        # Performance requirements
        assert max(processing_times) <= 30  # No single request > 30s
        assert sum(processing_times) / len(processing_times) <= 15  # Avg < 15s
        assert len(successful_results) >= len(model_codes) * 0.95  # 95% success
```

#### Tier 5: Acceptance Tests (5% effort) - Business Value
```python
class TestBusinessValueDelivery:
    """Validate actual business value with stakeholder scenarios"""
    
    @pytest.mark.acceptance
    async def test_cost_reduction_validation(self):
        """Validate actual cost reduction vs manual processing"""
        
        # Process representative sample
        model_codes = await get_random_real_model_codes(count=100)
        
        automated_start = time.time()
        system = ProductionSystem()
        results = await system.batch_process(model_codes)
        automated_time = time.time() - automated_start
        
        # Business value validation
        manual_time_estimate = len(model_codes) * 30 * 60  # 30 min per product
        time_savings = manual_time_estimate - automated_time
        
        assert time_savings >= manual_time_estimate * 0.95  # 95%+ time savings
        assert results.accuracy >= 0.99  # 99%+ accuracy
        
        # Cost validation
        manual_cost_estimate = len(model_codes) * 50  # $50 per product
        automated_cost = results.total_processing_cost
        cost_savings = manual_cost_estimate - automated_cost
        
        assert cost_savings >= manual_cost_estimate * 0.98  # 98%+ cost savings
```

## 🛡️ Anti-Deception Validation Framework

### Hardcoded Value Detection
```python
class TestAntiDeception:
    """Prevent facades and hardcoded implementations"""
    
    def test_no_hardcoded_confidence_scores(self):
        """Detect hardcoded confidence values"""
        source_files = glob.glob("src/**/*.py", recursive=True)
        
        for file_path in source_files:
            with open(file_path) as f:
                content = f.read()
            
            # Look for suspicious confidence patterns
            suspicious_patterns = [
                r'confidence.*=.*0\.9[0-9]',  # High confidence scores
                r'0\.95',  # Exact confidence values
                r'confidence.*1\.0',  # Perfect confidence
            ]
            
            for pattern in suspicious_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches and 'test' not in file_path:
                    raise AssertionError(f"Hardcoded confidence in {file_path}: {matches}")
    
    def test_no_mock_paradise(self):
        """Ensure production code doesn't rely on mocks"""
        production_files = glob.glob("src/**/*.py", recursive=True)
        
        for file_path in production_files:
            with open(file_path) as f:
                content = f.read()
            
            mock_indicators = ['Mock(', '@patch', 'MagicMock']
            for indicator in mock_indicators:
                if indicator in content:
                    raise AssertionError(f"Mock usage in production code: {file_path}")
    
    def test_execution_path_integration(self):
        """Verify all components actually integrate"""
        import sys
        from types import TracebackType
        
        called_modules = set()
        
        def trace_calls(frame, event, arg):
            if event == 'call' and 'src/' in frame.f_code.co_filename:
                called_modules.add(frame.f_code.co_filename)
            return trace_calls
        
        # Execute main workflow with tracing
        sys.settrace(trace_calls)
        run_sample_pipeline()
        sys.settrace(None)
        
        # Verify core modules were used
        required_modules = [
            'src/models/', 'src/services/', 'src/repositories/', 
            'src/pipeline/stages/'
        ]
        
        for required in required_modules:
            found = any(required in module for module in called_modules)
            assert found, f"Module {required} not used in execution"
```

## 🔧 Complete Makefile - Universal Commands

```makefile
.PHONY: install test lint format clean security performance validate-all

# === SETUP ===
install:
	poetry install
	pre-commit install

setup:
	createdb snowmobile_dev || echo "Database may exist"
	poetry run alembic upgrade head
	@echo "✅ Project setup complete"

# === TESTING ===
test:
	poetry run pytest tests/ -v

test-unit:
	poetry run pytest tests/unit/ -v -m "not integration"

test-integration:
	poetry run pytest tests/integration/ -v -m integration

test-performance:
	poetry run pytest tests/performance/ -v -m performance

test-system:
	poetry run pytest tests/system/ -v -m system

test-coverage:
	poetry run pytest --cov=src --cov-report=html --cov-report=term-missing --fail-under=80

# === CODE QUALITY ===
lint:
	poetry run ruff check src/ tests/
	poetry run mypy src/ --strict --no-error-summary

format:
	poetry run black src/ tests/
	poetry run ruff check --fix src/ tests/

type-check:
	poetry run mypy src/ --strict

# === SECURITY ===
security-scan:
	poetry run safety check --json
	poetry run bandit -r src/ -f json

check-secrets:
	@echo "Checking for hardcoded secrets..."
	@grep -r "password\|secret\|token\|key.*=" src/ --include="*.py" || echo "✅ No hardcoded secrets"

# === ANTI-DECEPTION ===
check-hardcoded:
	@echo "Checking for hardcoded values..."
	@grep -r "0\.9[0-9]" src/ --include="*.py" | grep -v test || echo "✅ No hardcoded confidence scores"
	@grep -r "TODO\|FIXME\|HACK" src/ --include="*.py" || echo "✅ No TODO/FIXME found"

check-facades:
	@find src/ -name "*.js" -o -name "*.ts" | wc -l | xargs -I {} sh -c 'if [ {} -gt 0 ]; then echo "❌ JavaScript found in src/"; exit 1; else echo "✅ No JavaScript in src/"; fi'

check-mocks:
	@python -c "import glob; files = glob.glob('src/**/*.py', recursive=True); mocks = [f for f in files if 'mock' in open(f).read().lower()]; print('❌ Mocks in production:' if mocks else '✅ No mocks in production', mocks)"

# === PERFORMANCE ===
benchmark:
	poetry run python scripts/benchmark_pipeline.py

profile:
	poetry run python -m cProfile -o profile.stats src/main.py
	poetry run python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

# === DATABASE ===
db-migrate:
	poetry run alembic upgrade head

db-rollback:
	poetry run alembic downgrade -1

db-reset:
	dropdb snowmobile_dev || echo "Database may not exist"
	createdb snowmobile_dev
	poetry run alembic upgrade head

# === VALIDATION ===
validate-all: lint type-check security-scan check-hardcoded check-facades check-mocks test-coverage
	@echo "✅ All validation checks passed"

validate-pipeline:
	poetry run python scripts/validate_pipeline_integration.py

# === MONITORING ===
health-check:
	curl -f http://localhost:8000/health || echo "Service not responding"

metrics:
	poetry run python scripts/show_pipeline_metrics.py

# === CLEANUP ===
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov/ .mypy_cache/

# === HELP ===
help:
	@echo "Available commands:"
	@echo "  Setup:      install, setup"
	@echo "  Testing:    test, test-unit, test-integration, test-coverage"
	@echo "  Quality:    lint, format, type-check, security-scan"
	@echo "  Anti-Fraud: check-hardcoded, check-facades, check-mocks"
	@echo "  Database:   db-migrate, db-rollback, db-reset"
	@echo "  Validation: validate-all, validate-pipeline"
	@echo "  Monitor:    health-check, metrics, benchmark"
```

## 📊 Quality Metrics Framework

### Confidence Scoring Algorithm
```python
class ConfidenceCalculator:
    """Professional confidence scoring with realistic boundaries"""
    
    def calculate_stage_confidence(self, 
                                 stage_type: ProcessingStage,
                                 input_data: Dict[str, Any],
                                 processing_result: Dict[str, Any]) -> Decimal:
        """Calculate realistic confidence scores by stage"""
        
        if stage_type == ProcessingStage.BASE_MODEL_MATCHING:
            if processing_result.get('method') == 'exact_lookup':
                return Decimal('0.98')  # High confidence for exact matches
            elif processing_result.get('method') == 'claude_semantic':
                # Claude confidence with realistic bounds
                claude_confidence = processing_result.get('claude_confidence', 0.85)
                return Decimal(str(min(claude_confidence, 0.92)))
            else:
                return Decimal('0.70')  # Fallback methods
        
        elif stage_type == ProcessingStage.SPECIFICATION_INHERITANCE:
            # Inheritance is highly reliable for matched base models
            base_confidence = input_data.get('base_model_confidence', 0.85)
            completeness = processing_result.get('completeness_score', 0.90)
            return Decimal(str(min(base_confidence * completeness, 0.97)))
        
        elif stage_type == ProcessingStage.SPRING_OPTIONS:
            known_options = processing_result.get('known_options_count', 0)
            researched_options = processing_result.get('researched_options_count', 0)
            
            if known_options > 0 and researched_options == 0:
                return Decimal('0.93')  # High confidence for known options
            elif researched_options > 0:
                # Claude research confidence with penalty
                claude_conf = processing_result.get('claude_confidence', 0.85)
                return Decimal(str(max(claude_conf - 0.05, 0.75)))
            else:
                return Decimal('0.95')  # No spring options to process
        
        # Add other stage calculations...
        return Decimal('0.85')  # Default realistic confidence
```

### Performance Monitoring
```python
from prometheus_client import Counter, Histogram, Gauge
import time
import psutil

# Pipeline metrics
PIPELINE_REQUESTS = Counter('pipeline_requests_total', 'Total pipeline requests', ['stage', 'status'])
PIPELINE_DURATION = Histogram('pipeline_duration_seconds', 'Pipeline processing time', ['stage'])
CONFIDENCE_SCORES = Histogram('confidence_score_distribution', 'Confidence score distribution')
CLAUDE_API_COSTS = Counter('claude_api_cost_total', 'Total Claude API costs')

def monitor_pipeline_stage(stage: ProcessingStage):
    """Monitor pipeline stage performance"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Record success metrics
                PIPELINE_REQUESTS.labels(stage=stage.value, status='success').inc()
                PIPELINE_DURATION.labels(stage=stage.value).observe(time.time() - start_time)
                
                if hasattr(result, 'confidence_score'):
                    CONFIDENCE_SCORES.observe(float(result.confidence_score))
                
                return result
                
            except Exception as e:
                PIPELINE_REQUESTS.labels(stage=stage.value, status='error').inc()
                logger.error(f"Stage {stage.value} failed", error=str(e))
                raise
                
        return wrapper
    return decorator
```

## 🔐 Security & Input Validation

### Comprehensive Input Validation
```python
class SecurityValidator:
    """Professional security validation for all inputs"""
    
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
        r"(\b(UNION|OR|AND)\s+(SELECT|ALL)\b)",
        r"(;|\|\||&&)",
    ]
    
    @classmethod
    def validate_model_code(cls, model_code: str) -> str:
        """Validate model code input"""
        if not model_code or len(model_code) > 50:
            raise ValueError("Invalid model code length")
        
        # Check for injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, model_code, re.IGNORECASE):
                raise ValueError("Potential SQL injection detected")
        
        return model_code.upper().strip()

class SecureInputModel(BaseModel):
    """Base model with security validation"""
    
    @validator('*', pre=True)
    def validate_security(cls, v):
        if isinstance(v, str):
            return SecurityValidator.validate_against_injection(v)
        return v
```

## 📋 Development Workflow Standards

### Git Workflow Requirements
```bash
# Branch naming - MANDATORY
feature/SNOW-123-add-stage-4-spring-options
bugfix/SNOW-124-fix-confidence-calculation
hotfix/SNOW-125-claude-api-timeout

# Commit format - REQUIRED
git commit -m "feat(pipeline): add spring options registry lookup

- Implement known spring options database lookup
- Add Claude research fallback for unknown options
- Include audit trail for option application
- Add performance metrics for stage 4

Resolves: SNOW-123
Performance: Stage 4 processing time reduced by 40%"
```

### Code Review Checklist
```markdown
## Security Review
- [ ] No hardcoded secrets, API keys, or configuration
- [ ] Input validation implemented for all external data
- [ ] SQL injection prevention validated

## Code Quality
- [ ] Type hints on ALL functions and classes
- [ ] Pydantic models for ALL data structures
- [ ] Comprehensive error handling with audit trails
- [ ] Structured logging with performance context

## Architecture
- [ ] Repository/service pattern followed
- [ ] No circular imports or tight coupling
- [ ] Performance considerations for large PDFs
- [ ] Memory usage optimized

## Testing
- [ ] Unit tests for new functionality with real data
- [ ] Integration tests for pipeline workflows
- [ ] Performance tests for critical paths
- [ ] Anti-deception validation passing

## Pipeline Integration
- [ ] New stage integrates with existing pipeline
- [ ] Audit trail properly maintained
- [ ] Confidence scoring realistic and validated
- [ ] Error recovery mechanisms implemented
```

## 🚀 Deployment & Production Standards

### CI/CD Pipeline Configuration
```yaml
# .github/workflows/ci.yml
name: Enterprise CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  quality-gates:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Install dependencies
      run: poetry install
    
    - name: Run quality checks
      run: |
        poetry run ruff check src/ tests/
        poetry run black --check src/ tests/
        poetry run mypy src/ --strict
    
    - name: Anti-deception validation
      run: |
        make check-hardcoded
        make check-facades
        make check-mocks
    
    - name: Security scan
      run: |
        poetry run safety check
        poetry run bandit -r src/

  test-suite:
    needs: quality-gates
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - name: Run comprehensive test suite
      run: |
        poetry run pytest tests/unit/ -v --cov=src
        poetry run pytest tests/integration/ -v
        poetry run pytest tests/performance/ -v

    - name: Validate coverage threshold
      run: |
        poetry run coverage report --fail-under=80
```

## 📈 Success Criteria & KPIs

### Technical Excellence
- **Type Safety**: mypy --strict passes with zero errors
- **Test Coverage**: Maintained at 80%+ across all components
- **Real Data Testing**: All tests use production PDF samples
- **Performance**: 100+ products/minute processing throughput
- **Quality**: 95%+ confidence scores for auto-accepted products

### Business Impact
- **Accuracy**: 99%+ correct product specifications vs. manual
- **Cost Efficiency**: <$3.00 per product including all processing
- **Time Reduction**: 95%+ reduction in manual processing time
- **Scalability**: Support for unlimited price lists and catalogs
- **Quality**: Customer-ready HTML documentation automatically generated

### Operational Excellence
- **Error Recovery**: <1% unrecoverable processing failures
- **Monitoring**: Complete observability and performance tracking
- **Learning**: Parser configurations improve automatically
- **Audit**: Complete traceability from PDF input to HTML output
- **Security**: No vulnerabilities or hardcoded credentials

This technical standards framework ensures enterprise-grade development practices while maintaining the flexibility needed for complex snowmobile product data reconciliation workflows.