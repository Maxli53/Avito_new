# Universal Development Standards - Complete Professional Requirements

Professional Developer Expectations
```markdown
A professional developer should:

1. **Implement all standards without complaint** - These are industry practices
2. **Provide realistic timelines** - Comprehensive systems take time
3. **Show incremental progress** - Daily commits with meaningful changes
4. **Handle edge cases** - Real systems have errors and exceptions
5. **Document thoroughly** - Code should be self-explanatory
6. **Think about operations** - How will this run in production?
7. **Consider security** - Validate all inputs and handle authentication
8. **Plan for scale** - Performance and monitoring from day one
9. **Test comprehensively** - Unit, integration, performance, and load tests
10. **Maintain quality** - Code reviews, linting, and continuous validation
```

**These standards ensure enterprise-grade software that's maintainable, secure, performant, and production-ready.**

## Project Foundation - Non-Negotiable

### Project Structure and Environment
```
project-name/
├── pyproject.toml              # Poetry configuration (NEVER requirements.txt)
├── .pre-commit-config.yaml     # Automatic quality control
├── .gitignore                  # Proper ignore patterns
├── .env.example                # Environment variable template
├── Makefile                    # Standardized commands
├── README.md                   # Clear setup instructions
├── CHANGELOG.md                # Version history
├── docker-compose.yml          # Local development environment
├── Dockerfile                  # Container configuration
├── src/
│   ├── __init__.py
│   ├── models/                 # Pydantic data models
│   ├── services/               # Business logic
│   ├── repositories/           # Data access layer
│   ├── api/                    # API endpoints (if applicable)
│   ├── cli/                    # Command line interface
│   └── utils/                  # Utility functions
├── tests/
│   ├── conftest.py             # Test configuration
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   ├── performance/            # Performance tests
│   └── fixtures/               # Test data
├── docs/                       # Documentation
├── scripts/                    # Deployment/maintenance scripts
├── migrations/                 # Database migrations (if applicable)
└── monitoring/                 # Monitoring configuration
```

### Mandatory Dependencies
```toml
[tool.poetry]
name = "project-name"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.10"
pydantic = "^2.0"              # Data validation (MANDATORY)
loguru = "^0.7"                # Structured logging
typer = "^0.9"                 # CLI interface

[tool.poetry.group.dev.dependencies]
pytest = "^7.4"
pytest-cov = "^4.1"
mypy = "^1.5"
black = "^23.0"
ruff = "^0.1"
pre-commit = "^3.4"

# Data Science Projects Add:
pandas = "^2.0"
numpy = "^1.24"
scikit-learn = "^1.3"
jupyter = "^1.0"
matplotlib = "^3.7"
seaborn = "^0.12"

# API Projects Add:
fastapi = "^0.100"
sqlalchemy = "^2.0"
alembic = "^1.11"
redis = "^4.6"

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
disallow_untyped_defs = true
check_untyped_defs = true

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing --fail-under=80 --strict-markers"

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = ["pragma: no cover", "def __repr__", "raise AssertionError"]
```

---

## Data Validation Standards

### Pydantic Models - Mandatory for All Data
```python
# NEVER use plain dictionaries or dataclasses for business data
# ALWAYS use Pydantic models with validation

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

class ProductModel(BaseModel):
    """Example: Proper data validation"""
    sku: str = Field(min_length=1, max_length=50)
    price: Decimal = Field(gt=0, decimal_places=2)
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None
    
    @validator('sku')
    def sku_must_be_alphanumeric(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('SKU must be alphanumeric')
        return v.upper()
    
    @validator('metadata')
    def validate_metadata(cls, v):
        if v and not isinstance(v, dict):
            raise ValueError('Metadata must be dict or None')
        return v
    
    class Config:
        validate_assignment = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
```

### Data Science Model Validation
```python
from pydantic import BaseModel, Field, validator
import pandas as pd
import numpy as np

class DatasetModel(BaseModel):
    """Validate ML datasets"""
    name: str
    shape: tuple = Field(description="(rows, columns)")
    columns: List[str]
    dtypes: dict
    missing_values: dict
    target_column: Optional[str] = None
    
    @validator('shape')
    def validate_shape(cls, v):
        if len(v) != 2 or v[0] <= 0 or v[1] <= 0:
            raise ValueError('Shape must be (positive_rows, positive_cols)')
        return v
    
    @validator('missing_values')
    def validate_missing_values(cls, v):
        for col, missing_count in v.items():
            if missing_count < 0:
                raise ValueError(f'Missing values for {col} cannot be negative')
        return v

class ModelMetrics(BaseModel):
    """Validate ML model performance"""
    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    precision: Optional[float] = Field(None, ge=0.0, le=1.0)
    recall: Optional[float] = Field(None, ge=0.0, le=1.0)
    f1_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    @validator('*', pre=True)
    def convert_numpy_float(cls, v):
        if isinstance(v, np.floating):
            return float(v)
        return v
```

---

## Code Quality Requirements

### Type Safety - Zero Tolerance
```python
# Every function MUST have type hints
def process_data(input_data: List[dict], 
                config: dict,
                threshold: float = 0.8) -> ProcessingResult:
    """
    Process data with full type annotations.
    
    Args:
        input_data: List of data dictionaries
        config: Configuration parameters
        threshold: Confidence threshold
        
    Returns:
        ProcessingResult with validation metrics
        
    Raises:
        ValidationError: If input data invalid
        ProcessingError: If processing fails
    """
    pass

# Type checking must pass strict mode
# mypy src/ --strict --no-error-summary
```

### Error Handling - Comprehensive
```python
from loguru import logger
from typing import Union
import traceback

class ProjectError(Exception):
    """Base exception for all project errors"""
    pass

class ValidationError(ProjectError):
    """Data validation failures"""
    pass

class ProcessingError(ProjectError):
    """Processing pipeline failures"""
    pass

def safe_processing_wrapper(func):
    """Decorator for safe function execution"""
    def wrapper(*args, **kwargs):
        try:
            logger.info(f"Starting {func.__name__}")
            result = func(*args, **kwargs)
            logger.info(f"Completed {func.__name__}")
            return result
        except ValidationError as e:
            logger.error(f"Validation error in {func.__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ProcessingError(f"Processing failed: {e}")
    return wrapper
```

### Logging Standards - Structured
```python
from loguru import logger
import sys

# Configure structured logging
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
)

# Usage in code:
logger.info("Processing started", extra={"sku": "MVTL", "source": "price_list.pdf"})
logger.error("Validation failed", extra={"error_type": "confidence_too_low", "value": 0.3})
```

---

## Testing Requirements

### Minimum Test Coverage - 80%
```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = [
    "--cov=src",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--fail-under=80",
    "--strict-markers"
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests", 
    "slow: Slow running tests",
    "external: Tests requiring external services"
]

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/migrations/*", "*/conftest.py"]

[tool.coverage.report]
precision = 2
show_missing = true
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
```

### Test Structure - Mandatory Organization
```python
# tests/conftest.py - Central test configuration
import pytest
from pathlib import Path
from unittest.mock import Mock
from src.models.core import ProjectConfig

@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture"""
    return ProjectConfig(
        database_url="sqlite:///:memory:",
        debug=True,
        log_level="DEBUG"
    )

@pytest.fixture
def sample_data():
    """Reusable test data"""
    return {
        "valid_input": ["item1", "item2", "item3"],
        "invalid_input": [None, "", "invalid"],
        "expected_output": {"processed": True, "count": 3}
    }

@pytest.fixture
def mock_external_service():
    """Mock external API calls"""
    return Mock()
```

### Test Categories - All Required
```python
# Unit Tests - Test individual functions
class TestDataProcessor:
    def test_valid_input_processing(self, sample_data):
        processor = DataProcessor()
        result = processor.process(sample_data["valid_input"])
        assert result.success is True
        assert result.count == 3
    
    def test_invalid_input_handling(self):
        processor = DataProcessor()
        with pytest.raises(ValidationError):
            processor.process(None)
    
    @pytest.mark.parametrize("input_val,expected", [
        ("VALID", True),
        ("", False),
        (None, False),
    ])
    def test_validation_cases(self, input_val, expected):
        assert DataProcessor.validate(input_val) == expected

# Integration Tests - Test workflows
@pytest.mark.integration
class TestCompleteWorkflow:
    def test_end_to_end_processing(self, test_config):
        # Test complete pipeline from input to output
        pipeline = ProcessingPipeline(test_config)
        result = pipeline.run_complete_workflow()
        
        assert result.success is True
        assert result.processed_count > 0
        assert result.confidence >= 0.8

# Property-Based Tests - Test with random data
from hypothesis import given, strategies as st

class TestWithRandomData:
    @given(st.text(min_size=1, max_size=100))
    def test_string_processing_never_crashes(self, random_string):
        processor = StringProcessor()
        # Should never crash, regardless of input
        result = processor.normalize(random_string)
        assert isinstance(result, str)
```

---

## Data Science Specific Requirements

### Data Pipeline Validation
```python
from pydantic import BaseModel, Field, validator
import pandas as pd
from pathlib import Path

class DataPipelineConfig(BaseModel):
    """Configuration for data science pipelines"""
    input_path: Path
    output_path: Path
    train_split: float = Field(ge=0.1, le=0.9, default=0.8)
    validation_split: float = Field(ge=0.05, le=0.5, default=0.1)
    test_split: float = Field(ge=0.05, le=0.5, default=0.1)
    random_seed: int = Field(ge=1, default=42)
    
    @validator('validation_split', 'test_split')
    def validate_splits_sum(cls, v, values):
        train = values.get('train_split', 0.8)
        if 'validation_split' in values:
            val = values['validation_split']
            if abs(train + val + v - 1.0) > 0.001:
                raise ValueError('Train/validation/test splits must sum to 1.0')
        return v

class DataQualityReport(BaseModel):
    """Validate data quality metrics"""
    dataset_name: str
    row_count: int = Field(gt=0)
    column_count: int = Field(gt=0)
    missing_percentage: float = Field(ge=0.0, le=100.0)
    duplicate_percentage: float = Field(ge=0.0, le=100.0)
    quality_score: float = Field(ge=0.0, le=1.0)
    
    @validator('quality_score')
    def validate_quality_score(cls, v, values):
        missing_pct = values.get('missing_percentage', 0)
        dup_pct = values.get('duplicate_percentage', 0)
        
        # Quality score should reflect data issues
        expected_max = 1.0 - (missing_pct + dup_pct) / 200
        if v > expected_max + 0.1:  # Small tolerance
            raise ValueError('Quality score too high given data issues')
        return v
```

### Model Performance Validation
```python
class MLModelMetrics(BaseModel):
    """Validate machine learning model performance"""
    model_name: str
    model_type: str  # "classification", "regression", "clustering"
    training_samples: int = Field(gt=0)
    
    # Classification metrics
    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    precision: Optional[float] = Field(None, ge=0.0, le=1.0)
    recall: Optional[float] = Field(None, ge=0.0, le=1.0)
    f1_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Regression metrics
    mse: Optional[float] = Field(None, ge=0.0)
    rmse: Optional[float] = Field(None, ge=0.0)
    mae: Optional[float] = Field(None, ge=0.0)
    r2_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    
    # Training info
    training_time_seconds: float = Field(gt=0)
    cross_validation_scores: Optional[List[float]] = None
    
    @validator('rmse')
    def validate_rmse_vs_mse(cls, v, values):
        mse = values.get('mse')
        if mse is not None and v is not None:
            expected_rmse = mse ** 0.5
            if abs(v - expected_rmse) > 0.001:
                raise ValueError('RMSE must equal sqrt(MSE)')
        return v
    
    @validator('cross_validation_scores')
    def validate_cv_scores(cls, v):
        if v:
            for score in v:
                if not 0.0 <= score <= 1.0:
                    raise ValueError('Cross-validation scores must be between 0 and 1')
        return v
```

---

## Architecture Patterns - Mandatory

### Repository Pattern
```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseRepository(ABC, Generic[T]):
    """Abstract base repository"""
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        pass
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        pass
    
    @abstractmethod
    async def update(self, id: str, updates: dict) -> T:
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass
    
    @abstractmethod
    async def list_all(self, limit: int = 100) -> List[T]:
        pass

class ProductRepository(BaseRepository[ProductModel]):
    """Concrete repository implementation"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def create(self, product: ProductModel) -> ProductModel:
        # Implementation with proper error handling
        try:
            # Database operations
            return saved_product
        except Exception as e:
            logger.error(f"Failed to create product: {e}")
            raise RepositoryError(f"Create failed: {e}")
```

### Service Layer Pattern
```python
class ProcessingService:
    """Business logic layer"""
    
    def __init__(self, 
                 repository: BaseRepository,
                 config: ProjectConfig):
        self.repository = repository
        self.config = config
        
    async def process_data(self, 
                          input_data: List[dict],
                          options: ProcessingOptions) -> ProcessingResult:
        """
        Main business logic with comprehensive validation
        """
        # 1. Validate inputs
        validated_data = [InputModel(**item) for item in input_data]
        
        # 2. Process with error handling
        results = []
        for item in validated_data:
            try:
                processed = await self._process_single_item(item)
                results.append(processed)
            except Exception as e:
                logger.error(f"Processing failed for {item}: {e}")
                if options.fail_fast:
                    raise
                
        # 3. Return validated results
        return ProcessingResult(
            total_processed=len(results),
            success_count=len([r for r in results if r.success]),
            results=results
        )
```

---

## Anti-Deception Validation

### Hardcoded Value Detection
```bash
# Makefile commands to check for hardcoded values
check-hardcoded:
	@echo "Checking for hardcoded values..."
	@grep -r "0\.9[0-9]" src/ --include="*.py" | grep -v test || echo "No hardcoded confidence scores"
	@grep -r "TODO\|FIXME\|HACK" src/ --include="*.py" || echo "No TODO/FIXME found"
	@grep -r "magic_number\|hardcoded" src/ --include="*.py" | grep -v test || echo "No magic numbers"

# Search for suspicious patterns
check-facades:
	@echo "Checking for facade patterns..."
	@find src/ -name "*.js" -o -name "*.ts" | wc -l | xargs -I {} sh -c 'if [ {} -gt 0 ]; then echo "ERROR: JavaScript files found in src/"; exit 1; fi'
	@python -c "import ast; import sys; [print(f'WARNING: {f}') for f in sys.argv[1:] if 'mock' in open(f).read().lower()]" src/**/*.py || echo "No mock usage in production code"
```

### Integration Validation
```python
class IntegrationValidator:
    """Validate all components actually integrate"""
    
    def validate_execution_path(self, main_function):
        """Ensure all classes are actually used"""
        import sys
        from types import TracebackType
        
        called_modules = set()
        
        def trace_calls(frame, event, arg):
            if event == 'call' and 'src/' in frame.f_code.co_filename:
                called_modules.add(frame.f_code.co_filename)
            return trace_calls
        
        sys.settrace(trace_calls)
        main_function()
        sys.settrace(None)
        
        # Verify core modules were called
        required_modules = [
            'src/models/', 'src/services/', 'src/repositories/'
        ]
        
        for required in required_modules:
            found = any(required in module for module in called_modules)
            assert found, f"Module {required} not used in execution path"
```

---

## Performance and Monitoring

### Performance Validation
```python
import time
import psutil
import memory_profiler
from functools import wraps

def performance_monitor(func):
    """Monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Memory before
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Timing
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # Memory after
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        # Log performance metrics
        logger.info(f"Performance: {func.__name__}", extra={
            "execution_time_ms": (end_time - start_time) * 1000,
            "memory_used_mb": memory_after - memory_before,
            "peak_memory_mb": memory_after
        })
        
        return result
    return wrapper

class PerformanceRequirements(BaseModel):
    """Define performance requirements"""
    max_processing_time_seconds: float = Field(gt=0)
    max_memory_usage_mb: float = Field(gt=0)
    min_throughput_items_per_minute: int = Field(gt=0)
    
    def validate_performance(self, metrics: dict) -> bool:
        """Validate performance meets requirements"""
        if metrics['time'] > self.max_processing_time_seconds:
            return False
        if metrics['memory'] > self.max_memory_usage_mb:
            return False
        if metrics['throughput'] < self.min_throughput_items_per_minute:
            return False
        return True
```

---

## Version Control Standards - Mandatory

### Git Workflow Requirements
```bash
# Branch naming convention - MUST follow
feature/PROJ-123-add-user-authentication
bugfix/PROJ-124-fix-login-validation  
hotfix/PROJ-125-security-patch
release/v1.2.0

# Commit message format - MANDATORY
git commit -m "feat: add user authentication with JWT tokens

- Implement JWT token generation
- Add user login validation
- Include password hashing with bcrypt
- Add authentication middleware

Resolves: PROJ-123"

# Conventional commits format required:
# type(scope): description
# 
# body explaining what and why
#
# footer with issue references
```

### Required Git Configuration
```bash
# .gitignore - Must include all these patterns
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment files
.env
.env.local
.env.*.local

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Project specific
logs/
data/raw/
data/processed/
models/saved/
*.db
*.sqlite3
```

### Branch Protection Rules
```bash
# Repository settings - MUST configure
main branch:
  - Require pull request reviews (minimum 1)
  - Require status checks (CI must pass)
  - Require up-to-date branches
  - Include administrators in restrictions
  
develop branch:
  - Require pull request reviews
  - Require status checks
  - Auto-delete head branches after merge
```

---

## Security Standards - Critical

### Environment Variable Management
```python
# settings.py - NEVER hardcode secrets
from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    """Secure configuration management"""
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(5, env="DB_POOL_SIZE")
    
    # API Keys
    claude_api_key: str = Field(..., env="CLAUDE_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(24, env="JWT_EXPIRATION_HOURS")
    
    # Performance
    max_workers: int = Field(4, env="MAX_WORKERS")
    timeout_seconds: int = Field(30, env="TIMEOUT_SECONDS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Usage
settings = Settings()  # Automatically loads from environment
```

### Security Validation Requirements
```python
# security_validators.py - MANDATORY security checks
import secrets
import hashlib
from pydantic import validator

class SecureModel(BaseModel):
    """Base model with security validation"""
    
    @validator('*', pre=True)
    def no_sql_injection_patterns(cls, v):
        if isinstance(v, str):
            suspicious_patterns = [
                'DROP TABLE', 'DELETE FROM', 'UPDATE SET', 
                'UNION SELECT', 'OR 1=1', 'AND 1=1'
            ]
            for pattern in suspicious_patterns:
                if pattern.upper() in v.upper():
                    raise ValueError(f'Suspicious SQL pattern detected: {pattern}')
        return v
    
    @validator('*', pre=True)  
    def no_script_injection(cls, v):
        if isinstance(v, str):
            if any(tag in v.lower() for tag in ['<script', 'javascript:', 'vbscript:']):
                raise ValueError('Script injection pattern detected')
        return v

def generate_secure_token() -> str:
    """Generate cryptographically secure token"""
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> str:
    """Secure password hashing"""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{hashed.hex()}"
```

### Dependency Security - Mandatory
```bash
# Makefile security commands - MUST implement
security-scan:
	poetry run safety check
	poetry run bandit -r src/
	poetry run semgrep --config=auto src/

audit-dependencies:
	poetry audit
	pip-audit

check-secrets:
	@echo "Checking for hardcoded secrets..."
	@grep -r "password\|secret\|token\|key" src/ --include="*.py" | grep -i "=" || echo "✓ No hardcoded secrets found"
```

---

## Database Management Standards

### Migration System - Required
```python
# migrations/env.py - Alembic configuration
from alembic import context
from sqlalchemy import engine_from_config, pool
from src.models.database import Base
from src.config import settings

def run_migrations():
    """Run database migrations with validation"""
    # Migration validation logic
    pass

# Migration template - MUST follow
"""Add user authentication

Revision ID: 001
Revises: None
Create Date: 2025-01-15 10:30:00

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    """Upgrade database schema"""
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

def downgrade():
    """Downgrade database schema"""
    op.drop_table('users')
```

### Database Standards
```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

class DatabaseManager:
    """Professional database management"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False  # Set to True for debugging only
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    @contextmanager
    def get_session(self):
        """Proper session management"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def backup_database(self, backup_path: str):
        """Create database backup"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT pg_dump_version()"))
            # Backup implementation
    
    def validate_schema(self) -> bool:
        """Validate database schema integrity"""
        # Schema validation logic
        pass
```

---

## Environment Management - Critical

### Environment Separation - Mandatory

```yaml
# docker-compose.yml - Development environment
version: '3.8'
services:
  app:
    build: ../../../../AppData/Roaming/JetBrains/PyCharm2025.1/scratches
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/app_dev
      - ENVIRONMENT=development
      - DEBUG=true
    depends_on:
      - db
      - redis
    volumes:
      - .:/app
      - /app/src/__pycache__  # Exclude cache

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: app_dev
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Configuration Management
```python
# config.py - Environment-specific settings
from enum import Enum
from pydantic import BaseSettings, Field

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"  
    PRODUCTION = "production"

class Settings(BaseSettings):
    # Environment
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(5, env="DB_POOL_SIZE")
    database_echo: bool = Field(False, env="DB_ECHO")
    
    # Security  
    secret_key: str = Field(..., env="SECRET_KEY")
    allowed_hosts: list = Field(["localhost"], env="ALLOWED_HOSTS")
    
    # API Rate Limiting
    rate_limit_per_minute: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    @validator('environment')
    def validate_environment(cls, v):
        if v == Environment.PRODUCTION:
            # Additional production validations
            pass
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

---

## API Design Standards - Required for Web Projects

### FastAPI Standards
```python
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import time

# API Models - Pydantic required
class APIResponse(BaseModel):
    """Standard API response format"""
    success: bool
    data: Optional[dict] = None
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error_code: str
    error_message: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# API endpoint standards
@app.post("/products/", response_model=APIResponse)
async def create_product(
    product: ProductCreateModel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse:
    """
    Create new product with validation.
    
    Args:
        product: Product data to create
        db: Database session
        current_user: Authenticated user
        
    Returns:
        APIResponse with created product data
        
    Raises:
        HTTPException: If validation fails or product exists
    """
    try:
        # Validate input
        validated_product = ProductCreateModel(**product.dict())
        
        # Business logic
        created_product = await product_service.create(validated_product, db)
        
        return APIResponse(
            success=True,
            data={"product": created_product.dict()},
            message="Product created successfully"
        )
    
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorResponse(
                error_code="VALIDATION_ERROR",
                error_message=str(e)
            ).dict()
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="INTERNAL_ERROR", 
                error_message="Internal server error"
            ).dict()
        )

# Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Request processed", extra={
        "path": request.url.path,
        "method": request.method,
        "process_time": process_time
    })
    return response
```

---

## Monitoring and Observability - Critical

### Logging Standards - Comprehensive
```python
from loguru import logger
import sys
import json
from datetime import datetime
from contextvars import ContextVar

# Request ID for tracing
request_id: ContextVar[str] = ContextVar('request_id', default='')

# Logger configuration
def setup_logging(environment: str, log_level: str = "INFO"):
    """Configure structured logging"""
    
    # Remove default handler
    logger.remove()
    
    # Console handler with colors for development
    if environment == "development":
        logger.add(
            sys.stdout,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
            level=log_level,
            colorize=True
        )
    
    # JSON handler for production
    else:
        def json_formatter(record):
            return json.dumps({
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "logger": record["name"],
                "function": record["function"],
                "line": record["line"],
                "message": record["message"],
                "request_id": request_id.get(""),
                "extra": record.get("extra", {})
            })
        
        logger.add(
            sys.stdout,
            format=json_formatter,
            level=log_level,
            serialize=True
        )
    
    # File handler with rotation
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="100 MB",
        retention="30 days",
        level="DEBUG",
        compression="gz"
    )

# Usage with context
logger.info(
    "Processing started",
    extra={
        "user_id": "12345",
        "operation": "data_processing",
        "input_size": 1000
    }
)
```

### Performance Monitoring - Required
```python
import time
import psutil
import functools
from typing import Callable, Any

def monitor_performance(
    log_threshold_ms: float = 1000,
    memory_threshold_mb: float = 100
):
    """Monitor function performance and resource usage"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Monitor memory before
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024
            
            # Monitor execution time
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                
                # Calculate metrics
                execution_time = (time.perf_counter() - start_time) * 1000
                memory_after = process.memory_info().rss / 1024 / 1024
                memory_used = memory_after - memory_before
                
                # Log if thresholds exceeded
                if execution_time > log_threshold_ms:
                    logger.warning(f"Slow execution: {func.__name__}", extra={
                        "execution_time_ms": execution_time,
                        "threshold_ms": log_threshold_ms
                    })
                
                if memory_used > memory_threshold_mb:
                    logger.warning(f"High memory usage: {func.__name__}", extra={
                        "memory_used_mb": memory_used,
                        "threshold_mb": memory_threshold_mb
                    })
                
                # Always log performance metrics
                logger.debug(f"Performance: {func.__name__}", extra={
                    "execution_time_ms": execution_time,
                    "memory_used_mb": memory_used,
                    "peak_memory_mb": memory_after
                })
                
                return result
                
            except Exception as e:
                logger.error(f"Function failed: {func.__name__}", extra={
                    "error": str(e),
                    "args": str(args)[:100],  # Truncate for logging
                    "kwargs": str(kwargs)[:100]
                })
                raise
                
        return wrapper
    return decorator

# Usage
@monitor_performance(log_threshold_ms=500, memory_threshold_mb=50)
def expensive_operation(data: List[dict]) -> ProcessingResult:
    # Implementation
    pass
```

---

## Testing Standards - Comprehensive

### Test Categories - All Required
```python
# Unit Tests - Test individual components
import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st

class TestDataProcessor:
    """Unit tests with comprehensive coverage"""
    
    @pytest.fixture
    def processor(self):
        return DataProcessor(config=test_config)
    
    def test_valid_input_processing(self, processor, sample_data):
        result = processor.process(sample_data["valid"])
        assert result.success is True
        assert result.processed_count == len(sample_data["valid"])
    
    def test_invalid_input_handling(self, processor):
        with pytest.raises(ValidationError, match="Invalid input format"):
            processor.process({"invalid": "data"})
    
    @pytest.mark.parametrize("input_val,expected_result", [
        ("VALID_SKU", True),
        ("", False),
        (None, False),
        ("123", True),
        ("special!@#", False)
    ])
    def test_validation_edge_cases(self, processor, input_val, expected_result):
        result = processor.validate_sku(input_val)
        assert result == expected_result
    
    # Property-based testing with Hypothesis
    @given(st.text(min_size=1, max_size=50))
    def test_string_processing_never_crashes(self, processor, random_string):
        # Should handle any string input without crashing
        try:
            result = processor.normalize_string(random_string)
            assert isinstance(result, str)
        except ValidationError:
            # Validation errors are acceptable
            pass

# Integration Tests - Test workflows
@pytest.mark.integration
class TestCompleteWorkflow:
    """Integration tests for end-to-end workflows"""
    
    @pytest.fixture(scope="class")
    def integration_db(self):
        # Setup integration test database
        engine = create_engine("postgresql://test:test@localhost/test_db")
        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)
    
    def test_complete_data_pipeline(self, integration_db):
        """Test full pipeline with real database"""
        pipeline = DataPipeline(database_url=str(integration_db.url))
        
        # Test with realistic data
        result = pipeline.process_file("tests/fixtures/sample_data.csv")
        
        assert result.success_rate >= 0.95
        assert result.processed_count > 0
        
        # Verify database state
        with pipeline.db.get_session() as session:
            products = session.query(Product).all()
            assert len(products) == result.processed_count

# Performance Tests - Required for critical functions
@pytest.mark.performance
class TestPerformanceRequirements:
    """Validate performance requirements"""
    
    def test_processing_speed_requirement(self):
        """Test 100 items/minute processing speed"""
        processor = DataProcessor()
        test_data = generate_test_data(1000)  # 1000 items
        
        start_time = time.time()
        result = processor.batch_process(test_data)
        duration = time.time() - start_time
        
        items_per_minute = (len(test_data) / duration) * 60
        assert items_per_minute >= 100, f"Only {items_per_minute:.1f} items/min"
    
    def test_memory_usage_limit(self):
        """Test memory usage stays under limit"""
        processor = DataProcessor()
        
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024
        
        # Process large dataset
        large_data = generate_test_data(10000)
        result = processor.batch_process(large_data)
        
        memory_after = process.memory_info().rss / 1024 / 1024
        memory_used = memory_after - memory_before
        
        assert memory_used < 500, f"Used {memory_used:.1f}MB, limit is 500MB"

# Load Tests - For web applications
@pytest.mark.load
class TestLoadRequirements:
    """Test system under load"""
    
    def test_concurrent_requests(self):
        """Test API handles concurrent load"""
        import concurrent.futures
        import requests
        
        def make_request():
            response = requests.get("http://localhost:8000/health")
            return response.status_code
        
        # Test 50 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [future.result() for future in futures]
        
        success_rate = len([r for r in results if r == 200]) / len(results)
        assert success_rate >= 0.95, f"Success rate: {success_rate:.2%}"
```

---

## Code Review Standards - Mandatory

### Code Review Checklist
```markdown
# Code Review Checklist - MUST complete for every PR

## Security Review
- [ ] No hardcoded secrets or API keys
- [ ] Input validation implemented
- [ ] SQL injection prevention
- [ ] XSS prevention (for web apps)
- [ ] Authentication/authorization properly implemented

## Code Quality  
- [ ] Type hints on all functions and classes
- [ ] Pydantic models for all data structures
- [ ] Proper error handling with custom exceptions
- [ ] Logging implemented appropriately
- [ ] No TODO/FIXME/HACK comments

## Architecture
- [ ] Follows repository/service pattern
- [ ] Proper separation of concerns
- [ ] No circular imports
- [ ] Dependency injection used appropriately
- [ ] Performance considerations addressed

## Testing
- [ ] Unit tests for new functionality
- [ ] Integration tests for workflows
- [ ] Test coverage ≥80% maintained
- [ ] Edge cases covered
- [ ] Performance tests for critical paths

## Documentation
- [ ] Docstrings on all public functions/classes
- [ ] README updated if needed
- [ ] API documentation updated (if applicable)
- [ ] CHANGELOG.md updated

## Database
- [ ] Migrations included for schema changes
- [ ] Indexes added for performance
- [ ] Foreign key constraints proper
- [ ] No direct SQL strings (use ORM)
```

### Pull Request Template
```markdown
# Pull Request Template

## Description
Brief description of changes and why they were made.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)  
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Performance improvement
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated  
- [ ] Manual testing completed
- [ ] Performance testing completed (if applicable)

## Checklist
- [ ] Code follows style guidelines (black, ruff, mypy)
- [ ] Self-review completed
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] No hardcoded values added
- [ ] Error handling implemented
- [ ] Logging added appropriately

## Performance Impact
Describe any performance implications of these changes.

## Security Considerations
Describe any security implications of these changes.

## Database Changes
Describe any database schema changes and migrations.
```

---

## CI/CD Pipeline - Production Standard

### GitHub Actions Configuration
```yaml
# .github/workflows/ci.yml - Comprehensive CI pipeline
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: '3.10'
  POETRY_VERSION: '1.5.1'

jobs:
  lint-and-security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: ${{ env.POETRY_VERSION }}
    
    - name: Install dependencies
      run: poetry install
    
    - name: Run linting
      run: |
        poetry run ruff check src/ tests/
        poetry run black --check src/ tests/
        poetry run mypy src/ --strict
    
    - name: Security scan
      run: |
        poetry run safety check
        poetry run bandit -r src/
    
    - name: Check for hardcoded values
      run: |
        make check-hardcoded
        make check-facades

  test:
    runs-on: ubuntu-latest
    needs: lint-and-security
    
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
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        poetry install
    
    - name: Run unit tests
      run: |
        poetry run pytest tests/unit/ -v --cov=src --cov-report=xml
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
      run: |
        poetry run pytest tests/integration/ -v
    
    - name: Run performance tests
      run: |
        poetry run pytest tests/performance/ -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

  deploy-staging:
    runs-on: ubuntu-latest
    needs: [lint-and-security, test]
    if: github.ref == 'refs/heads/develop'
    
    steps:
    - name: Deploy to staging
      run: |
        # Deployment commands
        echo "Deploying to staging environment"
    
  deploy-production:
    runs-on: ubuntu-latest
    needs: [lint-and-security, test]
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to production
      run: |
        # Production deployment commands
        echo "Deploying to production environment"
```

---

## Error Handling and Monitoring - Professional

### Error Tracking Integration
```python
import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

# Error tracking setup
def setup_error_tracking(environment: str, sentry_dsn: Optional[str]):
    """Configure error tracking and monitoring"""
    
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            integrations=[
                SqlalchemyIntegration(),
                FastApiIntegration(auto_enabling=True),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
            ],
            traces_sample_rate=0.1 if environment == "production" else 1.0,
            profiles_sample_rate=0.1 if environment == "production" else 1.0,
        )

# Custom error tracking
class ErrorTracker:
    """Track and categorize application errors"""
    
    def __init__(self):
        self.error_counts = {}
        
    def track_error(self, 
                   error: Exception, 
                   context: dict,
                   severity: str = "error"):
        """Track error with context"""
        
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.utcnow(),
            "severity": severity
        }
        
        # Log to structured logging
        logger.error("Application error", extra=error_info)
        
        # Send to error tracking service
        sentry_sdk.capture_exception(error, extra=context)
        
        # Update local metrics
        error_key = f"{type(error).__name__}:{severity}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

# Usage
error_tracker = ErrorTracker()

try:
    risky_operation()
except ValidationError as e:
    error_tracker.track_error(e, {
        "operation": "data_validation",
        "input_data": data_summary,
        "user_id": current_user.id
    }, severity="warning")
except ProcessingError as e:
    error_tracker.track_error(e, {
        "operation": "data_processing", 
        "batch_size": len(data),
        "stage": "enrichment"
    }, severity="error")
```

---

## Documentation Standards - Required

### Code Documentation - Mandatory
```python
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class DataProcessor:
    """
    Professional data processing with comprehensive validation.
    
    This class handles data processing workflows with built-in validation,
    error recovery, performance monitoring, and audit trails.
    
    The processor supports multiple input formats and provides detailed
    processing reports with quality metrics.
    
    Example:
        Basic usage:
        >>> config = ProcessingConfig(validation_level="strict")
        >>> processor = DataProcessor(config)
        >>> result = processor.process(input_data)
        >>> assert result.success_rate >= 0.95
        
        Advanced usage with custom validation:
        >>> validator = CustomValidator(rules=custom_rules)
        >>> processor = DataProcessor(config, validator=validator)
        >>> result = processor.process_with_validation(data, quality_threshold=0.9)
    
    Attributes:
        config: Processing configuration with validation rules
        validator: Data validation component
        metrics: Performance and quality metrics tracker
        
    Note:
        This processor is designed for high-throughput scenarios and includes
        memory usage optimization for large datasets.
    """
    
    def __init__(self, 
                 config: ProcessingConfig,
                 validator: Optional[DataValidator] = None):
        """
        Initialize processor with configuration and optional validator.
        
        Args:
            config: Processing configuration including validation rules,
                   performance thresholds, and error handling options
            validator: Optional custom validator. If None, uses default
                      validation rules based on config.validation_level
                      
        Raises:
            ConfigurationError: If config validation fails
            ValidatorError: If validator initialization fails
            
        Example:
            >>> config = ProcessingConfig(batch_size=1000, validation_level="strict")
            >>> processor = DataProcessor(config)
        """
        self.config = self._validate_config(config)
        self.validator = validator or DefaultValidator(config.validation_level)
        self.metrics = MetricsTracker()
        self.logger = logger.bind(component="DataProcessor")
    
    def process(self, 
                input_data: List[Dict[str, Any]],
                quality_threshold: float = 0.8,
                fail_fast: bool = False) -> ProcessingResult:
        """
        Process input data with comprehensive validation and monitoring.
        
        This method handles the complete processing workflow including
        validation, transformation, quality assessment, and result compilation.
        
        Args:
            input_data: List of data dictionaries to process. Each dictionary
                       should contain the required fields as defined in the
                       input schema. Empty list is acceptable and returns
                       empty result.
            quality_threshold: Minimum quality score required for successful
                             processing (0.0 to 1.0). Items below this threshold
                             are flagged for manual review.
            fail_fast: If True, stops processing on first error. If False,
                      continues processing and reports all errors in result.
                      
        Returns:
            ProcessingResult containing:
            - success_count: Number of successfully processed items
            - error_count: Number of items that failed processing
            - quality_metrics: Data quality assessment scores
            - processing_time: Total processing duration in seconds
            - warnings: List of non-fatal issues encountered
            - errors: List of processing errors (if fail_fast=False)
            
        Raises:
            ValidationError: If input_data format is invalid
            ProcessingError: If critical processing step fails (fail_fast=True)
            QualityError: If overall quality below threshold
            
        Example:
            Basic processing:
            >>> data = [{"id": 1, "value": "test"}, {"id": 2, "value": "data"}]
            >>> result = processor.process(data)
            >>> print(f"Processed {result.success_count} items")
            
            Strict quality requirements:
            >>> result = processor.process(data, quality_threshold=0.95, fail_fast=True)
            >>> if result.quality_score < 0.95:
            ...     raise QualityError("Quality requirements not met")
        
        Note:
            For large datasets (>10,000 items), consider using batch_process()
            method for better memory efficiency and progress tracking.
        """
        pass
```

### API Documentation - Required for Web Projects
```python
from fastapi import FastAPI
from pydantic import BaseModel, Field

# API documentation configuration
app = FastAPI(
    title="Project API",
    description="Comprehensive API for data processing operations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "products", "description": "Product management operations"},
        {"name": "processing", "description": "Data processing endpoints"},
        {"name": "monitoring", "description": "System health and metrics"}
    ]
)

# Documented API models
class ProductCreateRequest(BaseModel):
    """Request model for creating new products"""
    sku: str = Field(..., description="Product SKU", example="PROD-001")
    name: str = Field(..., description="Product name", example="Widget Pro")
    price: float = Field(..., gt=0, description="Product price in EUR", example=99.99)
    
    class Config:
        schema_extra = {
            "example": {
                "sku": "PROD-001",
                "name": "Professional Widget",
                "price": 299.99
            }
        }

class ProductResponse(BaseModel):
    """Response model for product operations"""
    id: str = Field(..., description="Unique product identifier")
    sku: str = Field(..., description="Product SKU")
    name: str = Field(..., description="Product name") 
    price: float = Field(..., description="Product price in EUR")
    created_at: datetime = Field(..., description="Creation timestamp")
    
# Documented endpoints
@app.post(
    "/products/", 
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new product",
    description="Create a new product with validation and audit trail",
    responses={
        201: {"description": "Product created successfully"},
        400: {"description": "Invalid product data"},
        409: {"description": "Product SKU already exists"},
        500: {"description": "Internal server error"}
    }
)
async def create_product(product: ProductCreateRequest) -> ProductResponse:
    """Create new product with comprehensive validation."""
    pass
```

---

## Data Science Specific Standards

### Jupyter Notebook Standards
```python
# notebook_standards.py - Required for data science projects
import papermill as pm
from pathlib import Path
import nbformat
from nbconvert import HTMLExporter

class NotebookValidator:
    """Validate Jupyter notebooks meet standards"""
    
    def validate_notebook(self, notebook_path: Path) -> bool:
        """Validate notebook structure and content"""
        
        with open(notebook_path) as f:
            notebook = nbformat.read(f, as_version=4)
        
        # Required sections
        required_sections = [
            "# Data Import and Validation",
            "# Exploratory Data Analysis", 
            "# Data Processing",
            "# Results and Validation",
            "# Conclusions"
        ]
        
        notebook_text = '\n'.join([
            cell['source'] for cell in notebook.cells 
            if cell['cell_type'] == 'markdown'
        ])
        
        missing_sections = [
            section for section in required_sections
            if section not in notebook_text
        ]
        
        if missing_sections:
            logger.error(f"Missing required sections: {missing_sections}")
            return False
        
        # Check for proper documentation
        code_cells = [cell for cell in notebook.cells if cell['cell_type'] == 'code']
        documented_cells = sum(1 for cell in code_cells if cell['source'].strip().startswith('#'))
        
        documentation_ratio = documented_cells / len(code_cells) if code_cells else 0
        if documentation_ratio < 0.8:
            logger.error(f"Insufficient documentation: {documentation_ratio:.1%}")
            return False
        
        return True

# Notebook execution validation
def execute_notebook_safely(notebook_path: Path, 
                           parameters: dict = None) -> bool:
    """Execute notebook and validate results"""
    try:
        pm.execute_notebook(
            notebook_path,
            notebook_path.with_suffix('.executed.ipynb'),
            parameters=parameters or {},
            timeout=3600  # 1 hour timeout
        )
        return True
    except Exception as e:
        logger.error(f"Notebook execution failed: {e}")
        return False
```

### Model Training Standards
```python
class ModelTrainingPipeline:
    """Standard ML training pipeline with validation"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.metrics_tracker = MLMetricsTracker()
        
    def train_model(self, 
                   train_data: pd.DataFrame,
                   validation_data: pd.DataFrame,
                   model_type: str) -> TrainingResult:
        """
        Train ML model with comprehensive validation and monitoring.
        
        Args:
            train_data: Training dataset with validated schema
            validation_data: Validation dataset for model evaluation
            model_type: Type of model to train ("classification", "regression")
            
        Returns:
            TrainingResult with model, metrics, and validation reports
        """
        
        # 1. Data validation
        train_schema = self._validate_training_data(train_data)
        val_schema = self._validate_training_data(validation_data)
        
        # 2. Feature engineering with audit trail
        features = self._engineer_features(train_data)
        feature_report = self._generate_feature_report(features)
        
        # 3. Model training with monitoring
        model = self._train_with_monitoring(features, model_type)
        
        # 4. Model validation
        metrics = self._evaluate_model(model, validation_data)
        
        # 5. Performance validation
        if metrics.accuracy < self.config.min_accuracy:
            raise ModelQualityError(f"Accuracy {metrics.accuracy} below threshold {self.config.min_accuracy}")
        
        return TrainingResult(
            model=model,
            metrics=metrics,
            feature_report=feature_report,
            training_config=self.config
        )
    
    def _validate_training_data(self, data: pd.DataFrame) -> DataSchema:
        """Validate training data meets requirements"""
        
        # Check required columns
        required_columns = self.config.required_features + [self.config.target_column]
        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            raise ValidationError(f"Missing required columns: {missing_columns}")
        
        # Check data quality
        missing_percentage = data.isnull().sum().sum() / (len(data) * len(data.columns))
        if missing_percentage > self.config.max_missing_percentage:
            raise ValidationError(f"Too much missing data: {missing_percentage:.1%}")
        
        return DataSchema(
            columns=list(data.columns),
            shape=data.shape,
            dtypes=data.dtypes.to_dict(),
            missing_percentage=missing_percentage
        )
```

---

## Complete Makefile - Universal Commands

```makefile
# Complete Makefile for all professional projects
.PHONY: install test lint format clean security performance docs deploy

# === SETUP ===
install:
	poetry install
	pre-commit install
	
install-dev:
	poetry install --with dev,test
	pre-commit install

setup-db:
	createdb $(PROJECT_NAME)_dev || echo "Database may already exist"
	poetry run alembic upgrade head

# === TESTING ===
test:
	poetry run pytest tests/ -v

test-unit:
	poetry run pytest tests/unit/ -v -m "not integration and not performance"

test-integration:
	poetry run pytest tests/integration/ -v -m integration

test-performance:
	poetry run pytest tests/performance/ -v -m performance --durations=10

test-load:
	poetry run pytest tests/load/ -v -m load

test-coverage:
	poetry run pytest --cov=src --cov-report=html --cov-report=term-missing --fail-under=80

test-watch:
	poetry run ptw tests/ src/ --ignore=.git

# === CODE QUALITY ===
lint:
	poetry run ruff check src/ tests/
	poetry run mypy src/ --strict --no-error-summary

format:
	poetry run black src/ tests/
	poetry run ruff check --fix src/ tests/

type-check:
	poetry run mypy src/ --strict

complexity-check:
	poetry run radon cc src/ -a -nc
	poetry run radon mi src/ -nc

# === SECURITY ===
security-scan:
	poetry run safety check --json
	poetry run bandit -r src/ -f json
	poetry run semgrep --config=auto src/

check-secrets:
	@echo "Checking for hardcoded secrets..."
	@grep -r "password\|secret\|token\|key.*=" src/ --include="*.py" || echo "✓ No hardcoded secrets"

audit-dependencies:
	poetry audit
	pip-audit

# === ANTI-DECEPTION ===
check-hardcoded:
	@echo "Checking for hardcoded values..."
	@grep -r "0\.9[0-9]" src/ --include="*.py" | grep -v test || echo "✓ No hardcoded confidence scores"
	@grep -r "TODO\|FIXME\|HACK" src/ --include="*.py" || echo "✓ No TODO/FIXME found"

check-facades:
	@find src/ -name "*.js" -o -name "*.ts" | wc -l | xargs -I {} sh -c 'if [ {} -gt 0 ]; then echo "❌ JavaScript found in src/"; exit 1; else echo "✓ No JavaScript in src/"; fi'
	@python -c "import ast; import sys; [print(f'WARNING: Mock in production: {f}') for f in sys.argv[1:] if 'mock' in open(f).read().lower()]" src/**/*.py 2>/dev/null || echo "✓ No mocks in production"

# === PERFORMANCE ===
profile:
	poetry run python -m cProfile -o profile.stats src/main.py
	poetry run python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

memory-profile:
	poetry run mprof run src/main.py
	poetry run mprof plot

benchmark:
	poetry run python scripts/benchmark.py

# === DOCUMENTATION ===
docs-generate:
	poetry run sphinx-build -b html docs/ docs/_build/html

docs-serve:
	poetry run python -m http.server 8080 --directory docs/_build/html

docs-check:
	poetry run sphinx-build -b linkcheck docs/ docs/_build/linkcheck

# === DATABASE ===
db-migrate:
	poetry run alembic upgrade head

db-rollback:
	poetry run alembic downgrade -1

db-reset:
	dropdb $(PROJECT_NAME)_dev || echo "Database may not exist"
	createdb $(PROJECT_NAME)_dev
	poetry run alembic upgrade head

db-backup:
	pg_dump $(PROJECT_NAME)_dev > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql

# === DEPLOYMENT ===
build:
	docker build -t $(PROJECT_NAME):latest .

deploy-staging:
	docker-compose -f docker-compose.staging.yml up -d

deploy-prod:
	@echo "Production deployment requires manual approval"
	@read -p "Deploy to production? (yes/no): " confirm && [ "$confirm" = "yes" ]
	docker-compose -f docker-compose.prod.yml up -d

# === VALIDATION ===
validate-all: lint type-check security-scan test-coverage check-hardcoded check-facades
	@echo "✓ All validation checks passed"

pre-commit-all:
	pre-commit run --all-files

# === MONITORING ===
health-check:
	curl -f http://localhost:8000/health || echo "Service not responding"

logs:
	tail -f logs/app_$(shell date +%Y-%m-%d).log

metrics:
	poetry run python scripts/show_metrics.py

# === CLEANUP ===
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov/ .mypy_cache/
	rm -rf dist/ build/ *.egg-info/

clean-all: clean
	docker system prune -f
	docker volume prune -f

# === INFORMATION ===
info:
	@echo "=== Project Information ==="
	@echo "Poetry: $(shell poetry --version)"
	@echo "Python: $(shell python --version)"
	@echo "Environment: $(shell poetry env info --path)"
	@echo "Dependencies:"
	@poetry show --tree | head -10

env-info:
	@echo "=== Environment Variables ==="
	@env | grep -E "(DATABASE|API|SECRET)" | sort

help:
	@echo "Available commands:"
	@echo "  Setup:       install, install-dev, setup-db"
	@echo "  Testing:     test, test-unit, test-integration, test-coverage"
	@echo "  Quality:     lint, format, type-check, security-scan"
	@echo "  Database:    db-migrate, db-rollback, db-reset, db-backup"
	@echo "  Deploy:      build, deploy-staging, deploy-prod"
	@echo "  Validation:  validate-all, check-hardcoded, check-facades"
	@echo "  Monitoring:  health-check, logs, metrics"
	@echo "  Cleanup:     clean, clean-all"
	@echo "  Info:        info, env-info, help"
```

---

## Pre-commit Configuration - Universal

```yaml
# .pre-commit-config.yaml - Mandatory for all projects
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict
      - id: check-docstring-first
      - id: check-case-conflict

  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3.10

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        args: [--strict]
        additional_dependencies: [pydantic, pandas, numpy]

  - repo: local
    hooks:
      - id: check-hardcoded-values
        name: Check for hardcoded values
        entry: bash -c 'grep -r "0\.9[0-9]" src/ --include="*.py" | grep -v test && exit 1 || exit 0'
        language: system
        pass_filenames: false

      - id: pytest-fast
        name: Fast test suite
        entry: poetry run pytest tests/unit/ --fail-fast
        language: system
        pass_filenames: false
```

---

## Documentation Requirements

### Code Documentation - Mandatory
```python
class DataProcessor:
    """
    Process and validate data with comprehensive error handling.
    
    This class handles data processing workflows with built-in validation,
    error recovery, and performance monitoring.
    
    Example:
        >>> processor = DataProcessor(config)
        >>> result = processor.process(data)
        >>> assert result.success is True
    """
    
    def __init__(self, config: ProcessingConfig):
        """
        Initialize processor with configuration.
        
        Args:
            config: Processing configuration with validation rules
            
        Raises:
            ValidationError: If config is invalid
        """
        self.config = config
        self.logger = logger.bind(component="DataProcessor")
    
    def process(self, 
                input_data: List[dict],
                validation_level: str = "strict") -> ProcessingResult:
        """
        Process input data with configurable validation.
        
        Args:
            input_data: List of data dictionaries to process
            validation_level: "strict", "normal", or "permissive"
            
        Returns:
            ProcessingResult with success metrics and processed data
            
        Raises:
            ValidationError: If input data fails validation
            ProcessingError: If processing pipeline fails
            
        Example:
            >>> result = processor.process([{"id": 1, "value": "test"}])
            >>> assert result.processed_count == 1
        """
        pass
```

### README Template - Required
```markdown
# Project Name

## Overview
Brief description of what this project does and why it exists.

## Setup
```bash
# Clone and setup
git clone [repo]
cd project-name
poetry install
pre-commit install
```

## Usage
```bash
# Basic usage
python -m src.cli --help

# Run main workflow
python -m src.cli process --input data.csv --output results.json
```

## Development
```bash
# Run all checks
make check-all

# Run tests
make test-coverage

# Format code  
make format
```

## Architecture
Brief explanation of key components and data flow.

## Performance
Current performance metrics and requirements.
```

---

## Project Validation Checklist

### Pre-Development (Setup Phase)
- [ ] Poetry pyproject.toml configured correctly
- [ ] Pre-commit hooks installed and passing
- [ ] Makefile commands all functional
- [ ] mypy --strict passes on empty project
- [ ] Basic test structure created
- [ ] Documentation template completed

### During Development (Weekly Checks)
- [ ] All tests passing with ≥80% coverage
- [ ] mypy --strict shows zero errors
- [ ] No hardcoded values in production code
- [ ] Git commits daily with meaningful messages
- [ ] Pre-commit hooks passing on all commits
- [ ] Performance requirements being met

### Pre-Delivery (Final Validation)
- [ ] Complete test suite passing
- [ ] All Makefile commands working
- [ ] Documentation complete and accurate
- [ ] Performance benchmarks met
- [ ] Anti-deception validation passing
- [ ] Code review checklist completed

---

## Immediate Rejection Criteria

**Automatic project rejection if ANY found:**
- Using requirements.txt instead of Poetry
- Using dataclasses instead of Pydantic for business data
- mypy --strict errors anywhere in codebase
- Test coverage below 80%
- Hardcoded values outside test files
- JavaScript/TypeScript files in src/ directory
- TODO/FIXME/HACK comments in production code
- Missing pre-commit hooks or hooks failing
- Makefile commands not working
- Suspiciously perfect results without realistic errors

---

---

## Infrastructure and Deployment Standards

### Docker Configuration - Required
```dockerfile
# Dockerfile - Multi-stage build for efficiency
FROM python:3.10-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.5.1

# Copy dependency files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Production stage
FROM python:3.10-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
WORKDIR /app
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "src.main"]
```

### Environment-Specific Configuration
```yaml
# docker-compose.production.yml
version: '3.8'

services:
  app:
    image: project-name:latest
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - SENTRY_DSN=${SENTRY_DSN}
    depends_on:
      - db
    networks:
      - app-network
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    networks:
      - app-network

  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
```

---

## Monitoring and Alerting - Production Ready

### Application Monitoring
```python
# monitoring/metrics.py - Custom metrics collection
import time
import psutil
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from functools import wraps
from contextlib import contextmanager

# Prometheus metrics
REQUEST_COUNT = Counter('app_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('app_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('app_active_connections', 'Active database connections')
MEMORY_USAGE = Gauge('app_memory_usage_bytes', 'Memory usage in bytes')
ERROR_COUNT = Counter('app_errors_total', 'Total errors', ['error_type'])

class MetricsCollector:
    """Collect and expose application metrics"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
    
    @contextmanager
    def time_operation(self, operation_name: str):
        """Time operation and record metrics"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            REQUEST_DURATION.labels(operation=operation_name).observe(duration)
    
    def record_error(self, error_type: str):
        """Record error occurrence"""
        ERROR_COUNT.labels(error_type=error_type).inc()
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        process = psutil.Process()
        MEMORY_USAGE.set(process.memory_info().rss)

# Usage decorator
def monitor_endpoint(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status='pending'
        ).inc()
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path, 
                status='success'
            ).inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status='error'
            ).inc()
            metrics.record_error(type(e).__name__)
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    return wrapper
```

### Health Check Standards
```python
# health.py - Comprehensive health checks
from pydantic import BaseModel
from typing import Dict, List
import asyncio
import aioredis
import asyncpg

class HealthStatus(BaseModel):
    """Health check response model"""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    version: str
    uptime_seconds: float
    checks: Dict[str, dict]

class HealthChecker:
    """Comprehensive application health monitoring"""
    
    def __init__(self, config: Settings):
        self.config = config
        self.start_time = time.time()
    
    async def check_health(self) -> HealthStatus:
        """Perform comprehensive health check"""
        
        checks = {}
        overall_status = "healthy"
        
        # Database health
        db_health = await self._check_database()
        checks["database"] = db_health
        if db_health["status"] != "healthy":
            overall_status = "degraded"
        
        # Redis health (if used)
        if self.config.redis_url:
            redis_health = await self._check_redis()
            checks["redis"] = redis_health
            if redis_health["status"] != "healthy":
                overall_status = "degraded"
        
        # External API health
        api_health = await self._check_external_apis()
        checks["external_apis"] = api_health
        if api_health["status"] != "healthy":
            overall_status = "degraded"
        
        # System resources
        system_health = self._check_system_resources()
        checks["system"] = system_health
        if system_health["status"] != "healthy":
            overall_status = "unhealthy"
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=self.config.app_version,
            uptime_seconds=time.time() - self.start_time,
            checks=checks
        )
    
    async def _check_database(self) -> dict:
        """Check database connectivity and performance"""
        try:
            conn = await asyncpg.connect(self.config.database_url)
            
            # Test query performance
            start_time = time.time()
            await conn.fetchval("SELECT 1")
            query_time = (time.time() - start_time) * 1000
            
            await conn.close()
            
            status = "healthy" if query_time < 100 else "degraded"
            
            return {
                "status": status,
                "response_time_ms": query_time,
                "message": "Database connection successful"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Database connection failed"
            }
    
    def _check_system_resources(self) -> dict:
        """Check system resource usage"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu = psutil.cpu_percent(interval=1)
        
        # Determine status based on thresholds
        if memory.percent > 90 or disk.percent > 90 or cpu > 90:
            status = "unhealthy"
        elif memory.percent > 80 or disk.percent > 80 or cpu > 80:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "cpu_percent": cpu,
            "message": f"System resources: {status}"
        }
```

---

## Performance and Load Testing - Critical

### Load Testing Standards
```python
# tests/load/test_load_requirements.py
import asyncio
import aiohttp
import time
from statistics import mean, median
import pytest

class LoadTestRunner:
    """Professional load testing framework"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = []
    
    async def run_load_test(self,
                           endpoint: str,
                           concurrent_users: int,
                           duration_seconds: int,
                           ramp_up_seconds: int = 30) -> dict:
        """
        Run comprehensive load test
        
        Args:
            endpoint: API endpoint to test
            concurrent_users: Number of simultaneous users
            duration_seconds: Test duration
            ramp_up_seconds: Gradual user ramp-up time
        
        Returns:
            Load test results with performance metrics
        """
        
        # Gradual ramp-up
        tasks = []
        ramp_up_delay = ramp_up_seconds / concurrent_users
        
        async with aiohttp.ClientSession() as session:
            for i in range(concurrent_users):
                task = asyncio.create_task(
                    self._user_simulation(session, endpoint, duration_seconds)
                )
                tasks.append(task)
                
                # Gradual ramp-up
                await asyncio.sleep(ramp_up_delay)
            
            # Wait for all users to complete
            await asyncio.gather(*tasks)
        
        return self._analyze_results()
    
    async def _user_simulation(self, 
                              session: aiohttp.ClientSession,
                              endpoint: str,
                              duration: int):
        """Simulate single user behavior"""
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            start_request = time.time()
            
            try:
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    await response.text()
                    
                    self.results.append({
                        "timestamp": start_request,
                        "response_time": time.time() - start_request,
                        "status_code": response.status,
                        "success": response.status < 400
                    })
                    
            except Exception as e:
                self.results.append({
                    "timestamp": start_request,
                    "response_time": time.time() - start_request,
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                })
            
            # Realistic user behavior - wait between requests
            await asyncio.sleep(1)
    
    def _analyze_results(self) -> dict:
        """Analyze load test results"""
        
        response_times = [r["response_time"] for r in self.results]
        success_count = len([r for r in self.results if r["success"]])
        
        return {
            "total_requests": len(self.results),
            "successful_requests": success_count,
            "success_rate": success_count / len(self.results),
            "average_response_time": mean(response_times),
            "median_response_time": median(response_times),
            "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
            "max_response_time": max(response_times),
            "requests_per_second": len(self.results) / max(response_times)
        }

# Load test requirements
@pytest.mark.load
class TestLoadRequirements:
    """Validate system performance under load"""
    
    @pytest.mark.asyncio
    async def test_api_load_capacity(self):
        """Test API handles required load"""
        
        runner = LoadTestRunner("http://localhost:8000")
        
        # Test requirements: 100 concurrent users for 5 minutes
        results = await runner.run_load_test(
            endpoint="/api/products/",
            concurrent_users=100,
            duration_seconds=300,
            ramp_up_seconds=60
        )
        
        # Performance requirements
        assert results["success_rate"] >= 0.99, f"Success rate: {results['success_rate']:.2%}"
        assert results["average_response_time"] <= 1.0, f"Avg response: {results['average_response_time']:.2f}s"
        assert results["p95_response_time"] <= 2.0, f"P95 response: {results['p95_response_time']:.2f}s"
        assert results["requests_per_second"] >= 50, f"RPS: {results['requests_per_second']:.1f}"
```

### Caching Strategy - Performance Critical
```python
# caching/redis_cache.py - Professional caching layer
import json
import asyncio
from typing import Optional, Any, Callable
import aioredis
from functools import wraps

class CacheManager:
    """Professional Redis caching with validation"""
    
    def __init__(self, redis_url: str, default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.redis: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """Establish Redis connection with validation"""
        self.redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={}
        )
        
        # Validate connection
        await self.redis.ping()
        logger.info("Redis connection established")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value with validation"""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in cache key: {key}")
            await self.redis.delete(key)  # Clean up corrupted data
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value with validation"""
        try:
            serialized = json.dumps(value, default=str)
            ttl = ttl or self.default_ttl
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

def cached(ttl: int = 3600, key_prefix: str = ""):
    """Caching decorator with validation"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try cache first
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result
            
            # Execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Usage
@cached(ttl=1800, key_prefix="product_data")
async def get_product_specifications(sku: str) -> dict:
    # Expensive operation that benefits from caching
    pass
```

---

## MLOps Standards - Data Science Projects

### Model Versioning and Tracking
```python
# mlops/model_tracking.py - Professional ML model management
import mlflow
import mlflow.sklearn
import joblib
from pathlib import Path
from typing import Dict, Any
import hashlib

class ModelTracker:
    """Professional ML model tracking and versioning"""
    
    def __init__(self, tracking_uri: str, experiment_name: str):
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        self.experiment_name = experiment_name
    
    def track_training_run(self,
                          model,
                          metrics: Dict[str, float],
                          parameters: Dict[str, Any],
                          dataset_info: Dict[str, Any],
                          model_artifacts: Dict[str, Path]) -> str:
        """
        Track complete ML training run with artifacts
        
        Returns:
            run_id: MLflow run identifier for model retrieval
        """
        
        with mlflow.start_run() as run:
            # Log parameters
            mlflow.log_params(parameters)
            
            # Log metrics
            mlflow.log_metrics(metrics)
            
            # Log dataset information
            mlflow.log_params({
                f"dataset_{k}": v for k, v in dataset_info.items()
            })
            
            # Log model
            mlflow.sklearn.log_model(
                model,
                "model",
                registered_model_name=f"{self.experiment_name}_model"
            )
            
            # Log additional artifacts
            for artifact_name, artifact_path in model_artifacts.items():
                mlflow.log_artifact(str(artifact_path), artifact_name)
            
            # Generate model signature
            model_signature = self._generate_model_signature(model)
            mlflow.log_param("model_signature", model_signature)
            
            logger.info(f"Model tracked: {run.info.run_id}")
            return run.info.run_id
    
    def load_model_by_version(self, version: str):
        """Load specific model version"""
        model_uri = f"models:/{self.experiment_name}_model/{version}"
        return mlflow.sklearn.load_model(model_uri)
    
    def promote_model_to_production(self, run_id: str) -> bool:
        """Promote model to production with validation"""
        try:
            # Load model for validation
            model_uri = f"runs:/{run_id}/model"
            model = mlflow.sklearn.load_model(model_uri)
            
            # Validate model performance
            if self._validate_model_quality(model):
                # Promote to production
                mlflow.register_model(model_uri, f"{self.experiment_name}_production")
                logger.info(f"Model {run_id} promoted to production")
                return True
            else:
                logger.warning(f"Model {run_id} failed quality validation")
                return False
                
        except Exception as e:
            logger.error(f"Model promotion failed: {e}")
            return False

# Model validation pipeline
class ModelValidator:
    """Validate ML models before deployment"""
    
    def __init__(self, quality_thresholds: Dict[str, float]):
        self.thresholds = quality_thresholds
    
    def validate_model(self, 
                      model,
                      test_data: pd.DataFrame,
                      target_column: str) -> ModelValidationResult:
        """Comprehensive model validation"""
        
        # Performance validation
        predictions = model.predict(test_data.drop(target_column, axis=1))
        actual = test_data[target_column]
        
        metrics = self._calculate_metrics(predictions, actual)
        
        # Quality gates
        validation_results = {}
        for metric_name, threshold in self.thresholds.items():
            current_value = metrics.get(metric_name, 0)
            validation_results[metric_name] = {
                "value": current_value,
                "threshold": threshold,
                "passed": current_value >= threshold
            }
        
        # Data drift detection
        drift_score = self._detect_data_drift(test_data)
        validation_results["data_drift"] = {
            "score": drift_score,
            "threshold": 0.1,
            "passed": drift_score < 0.1
        }
        
        overall_passed = all(result["passed"] for result in validation_results.values())
        
        return ModelValidationResult(
            model_id=self._generate_model_id(model),
            validation_passed=overall_passed,
            metrics=metrics,
            validation_details=validation_results,
            timestamp=datetime.utcnow()
        )
```

### A/B Testing Framework
```python
# ab_testing/experiment_framework.py - A/B testing for ML models
from enum import Enum
import random
from typing import Optional

class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ABExperiment(BaseModel):
    """A/B testing experiment configuration"""
    
    experiment_id: str
    name: str
    description: str
    status: ExperimentStatus
    traffic_split: float = Field(ge=0.0, le=1.0)  # Percentage to new model
    
    control_model_version: str
    treatment_model_version: str
    
    success_metrics: List[str]
    minimum_sample_size: int = Field(gt=0)
    
    start_date: datetime
    end_date: Optional[datetime] = None
    
class ExperimentManager:
    """Manage A/B testing experiments"""
    
    def __init__(self):
        self.active_experiments = {}
    
    def should_use_treatment(self, 
                           experiment_id: str,
                           user_id: str) -> bool:
        """Determine if user should see treatment version"""
        
        experiment = self.active_experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return False
        
        # Consistent assignment based on user_id
        random.seed(hash(f"{experiment_id}:{user_id}"))
        return random.random() < experiment.traffic_split
    
    def record_experiment_result(self,
                               experiment_id: str,
                               user_id: str,
                               model_version: str,
                               metrics: Dict[str, float]):
        """Record experiment results for analysis"""
        
        result = ExperimentResult(
            experiment_id=experiment_id,
            user_id=user_id,
            model_version=model_version,
            metrics=metrics,
            timestamp=datetime.utcnow()
        )
        
        # Store results for statistical analysis
        self._store_result(result)
```

---

## Database Design Standards - Critical

### Schema Design Requirements
```python
# database/schema_standards.py - Professional database design
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class BaseModel:
    """Base model with audit fields - ALL tables must inherit"""
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))  # Audit trail
    updated_by = Column(String(100))  # Audit trail
    
    # Soft delete support
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(100), nullable=True)

class Product(Base, BaseModel):
    """Example: Professional table design"""
    __tablename__ = "products"
    
    # Business keys
    sku = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    
    # Flexible specifications storage
    specifications = Column(JSONB, nullable=False, default=dict)
    
    # Performance optimization
    search_vector = Column(Text)  # Full-text search
    
    # Required indexes
    __table_args__ = (
        Index('idx_products_sku_name', 'sku', 'name'),
        Index('idx_products_created_at', 'created_at'),
        Index('idx_products_search_vector', 'search_vector', postgresql_using='gin'),
        Index('idx_products_specs_gin', 'specifications', postgresql_using='gin'),
    )

# Migration validation
class MigrationValidator:
    """Validate database migrations before deployment"""
    
    def validate_migration(self, migration_sql: str) -> bool:
        """Validate migration safety"""
        
        dangerous_operations = [
            'DROP TABLE',
            'DROP COLUMN', 
            'ALTER COLUMN DROP',
            'TRUNCATE',
            'DELETE FROM'
        ]
        
        for operation in dangerous_operations:
            if operation in migration_sql.upper():
                logger.error(f"Dangerous operation detected: {operation}")
                return False
        
        return True
    
    def estimate_migration_time(self, 
                               migration_sql: str,
                               table_name: str) -> int:
        """Estimate migration execution time"""
        
        # Check table size
        row_count = self._get_table_row_count(table_name)
        
        # Estimate based on operation type
        if 'CREATE INDEX' in migration_sql.upper():
            # Index creation: ~1000 rows per second
            return max(60, row_count // 1000)
        elif 'ALTER TABLE' in migration_sql.upper():
            # Table alteration: ~500 rows per second  
            return max(120, row_count // 500)
        else:
            return 30  # Default estimate
```

---

## Security and Compliance - Critical

### Input Validation Framework
```python
# security/validation.py - Comprehensive input validation
import re
from typing import Any, List, Dict
from pydantic import BaseModel, validator, Field

class SecurityValidator:
    """Professional security validation"""
    
    # Security patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC)\b)",
        r"(\b(UNION|OR|AND)\s+(SELECT|ALL)\b)",
        r"(;|\|\||&&)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+\b)"
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>"
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\.\/",
        r"\.\.\\",
        r"~\/",
        r"\/etc\/",
        r"\/proc\/"
    ]
    
    @classmethod
    def validate_against_injection(cls, value: str) -> str:
        """Validate string against injection attacks"""
        
        if not isinstance(value, str):
            return value
        
        # Check SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potential SQL injection detected")
        
        # Check XSS
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potential XSS attack detected")
        
        # Check path traversal
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value):
                raise ValueError(f"Potential path traversal detected")
        
        return value

class SecureInputModel(BaseModel):
    """Base model with security validation"""
    
    @validator('*', pre=True)
    def validate_security(cls, v):
        if isinstance(v, str):
            return SecurityValidator.validate_against_injection(v)
        return v
    
    class Config:
        # Additional security configurations
        anystr_strip_whitespace = True
        validate_assignment = True
        use_enum_values = True

# Rate limiting
class RateLimiter:
    """Professional rate limiting implementation"""
    
    def __init__(self, redis_client, default_limit: int = 100):
        self.redis = redis_client
        self.default_limit = default_limit
    
    async def is_allowed(self, 
                        identifier: str,
                        limit: Optional[int] = None,
                        window_seconds: int = 60) -> bool:
        """Check if request is within rate limit"""
        
        limit = limit or self.default_limit
        key = f"rate_limit:{identifier}:{window_seconds}"
        
        # Sliding window counter
        now = time.time()
        window_start = now - window_seconds
        
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)  # Remove old entries
        pipe.zcard(key)  # Count current entries
        pipe.zadd(key, {str(now): now})  # Add current request
        pipe.expire(key, window_seconds)  # Set expiration
        
        results = await pipe.execute()
        current_count = results[1]
        
        return current_count < limit
```

---

## Final Requirements Summary

### Immediate Rejection Criteria - Comprehensive List
```bash
# Development Environment
❌ Using requirements.txt instead of pyproject.toml
❌ Missing pre-commit hooks or hooks failing
❌ mypy --strict reporting any errors
❌ Test coverage below 80%
❌ Missing or broken Makefile commands

# Code Quality  
❌ Using dataclasses instead of Pydantic for business data
❌ Missing type hints on any public function
❌ TODO/FIXME/HACK comments in production code
❌ Hardcoded secrets or configuration values
❌ No error handling or generic try/except blocks

# Architecture
❌ Direct database queries instead of repository pattern
❌ Missing service layer for business logic
❌ Circular imports or missing __init__.py files
❌ No dependency injection or tightly coupled code
❌ JavaScript/TypeScript files in src/ directory

# Security
❌ No input validation or sanitization
❌ Hardcoded API keys or secrets
❌ Missing authentication/authorization
❌ No rate limiting (for web APIs)
❌ Vulnerable to SQL injection or XSS

# Testing
❌ Missing unit tests for core functionality
❌ No integration tests for workflows
❌ Missing performance tests for critical paths
❌ No load testing for web applications
❌ Tests that don't actually test functionality

# Data Science Specific
❌ No data validation or schema enforcement
❌ Missing model performance validation
❌ No experiment tracking or model versioning
❌ Hardcoded model parameters or features
❌ No data drift detection

# Operations
❌ No logging or poor logging practices
❌ Missing health checks and monitoring
❌ No database migration system
❌ Missing backup and recovery procedures
❌ No deployment automation
```

