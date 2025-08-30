# Troubleshooting Guide
**Snowmobile Product Data Reconciliation System**

## 🚨 Common Issues and Solutions

### Environment Setup Issues

#### Poetry Installation Problems
```bash
# Error: Poetry not found or version conflicts
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"
poetry --version  # Verify installation

# Error: Virtual environment issues
poetry env remove python
poetry install
poetry shell
```

#### Database Connection Issues
```bash
# Error: PostgreSQL connection refused
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Error: Database does not exist
createdb snowmobile_dev
createdb snowmobile_test

# Error: Permission denied
sudo -u postgres createuser --superuser $USER
```

#### Pre-commit Hook Failures
```bash
# Error: Pre-commit hooks failing
pre-commit clean
pre-commit install
pre-commit run --all-files

# Error: mypy strict failures
poetry add types-requests types-setuptools
mypy --install-types
```

### Development Issues

#### Type Checking Errors
```python
# ❌ Common mypy errors and fixes

# Error: Missing return type annotation
def process_data(input):  # ❌ No type hints
    return result

def process_data(input: Dict[str, Any]) -> ProcessingResult:  # ✅ Proper typing
    return result

# Error: Untyped function parameters
class ProductMatcher:
    def match(self, entry, catalog):  # ❌ No types
        pass
    
    def match(self, entry: PriceEntry, catalog: List[Product]) -> MatchResult:  # ✅ Typed
        pass

# Error: Any type usage
def parse_specs(data: Any) -> Any:  # ❌ Too generic
    pass

def parse_specs(data: Dict[str, str]) -> ProductSpecification:  # ✅ Specific types
    pass
```

#### Pydantic Model Issues
```python
# ❌ Common Pydantic mistakes

# Error: Using dataclasses instead of Pydantic
@dataclass  # ❌ Wrong approach
class Product:
    sku: str
    price: float

# ✅ Correct Pydantic usage
class Product(BaseModel):
    sku: str = Field(regex=r'^[A-Z0-9]{3,6}$')
    price: Decimal = Field(gt=0, decimal_places=2)

# Error: Missing validation
class PriceEntry(BaseModel):
    price: float  # ❌ No validation

class PriceEntry(BaseModel):
    price: Decimal = Field(gt=0, le=100000, decimal_places=2)  # ✅ Validated
```

#### Test Coverage Issues
```bash
# Error: Coverage below 80%
poetry run pytest --cov=src --cov-report=html
# Review coverage report in htmlcov/index.html
# Add tests for uncovered code

# Error: Tests not finding modules
# Ensure proper __init__.py files in all directories
touch src/__init__.py
touch src/models/__init__.py
touch src/services/__init__.py

# Error: Test fixtures not working
# Check conftest.py setup
# Verify fixture scope and dependencies
```

### Pipeline Processing Issues

#### PDF Parsing Failures
```python
# Common PDF parsing issues and solutions

class PDFParsingTroubleshooter:
    def diagnose_pdf_issues(self, pdf_path: str) -> DiagnosisReport:
        """Diagnose common PDF parsing problems"""
        
        issues = []
        
        # Check file accessibility
        if not os.path.exists(pdf_path):
            issues.append("PDF file not found")
        
        # Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size > 50_000_000:  # 50MB
            issues.append("PDF file too large, consider splitting")
        
        # Check PDF structure
        try:
            doc = fitz.open(pdf_path)
            if doc.page_count == 0:
                issues.append("PDF contains no pages")
        except Exception as e:
            issues.append(f"PDF corruption detected: {e}")
        
        return DiagnosisReport(issues)

# Solutions for common PDF issues:
# 1. Scanned PDFs: Use OCR with Claude error correction
# 2. Password protected: Request unprotected version
# 3. Malformed tables: Try alternative extraction methods
# 4. Non-standard encoding: Convert to UTF-8 before processing
```

#### Claude API Issues
```bash
# Error: API rate limit exceeded (429)
# Solution: Implement exponential backoff
# Check rate limiting configuration in client

# Error: API key invalid (401)
# Verify Claude API key in environment variables
echo $CLAUDE_API_KEY
# Check API key permissions and quotas

# Error: Request timeout
# Increase timeout settings
# Reduce batch size for complex requests
# Implement proper retry logic

# Error: Token limit exceeded
# Reduce prompt size
# Implement prompt truncation
# Use batch processing with smaller batches
```

#### Database Performance Issues
```sql
-- Slow query diagnosis
SELECT 
    query,
    mean_exec_time,
    calls,
    total_exec_time
FROM pg_stat_statements 
ORDER BY total_exec_time DESC 
LIMIT 10;

-- Missing index detection
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > 1000;  -- Tables doing too many sequential scans

-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_products_engine_brand 
ON products(engine_model, brand) 
WHERE engine_model IS NOT NULL;
```

### Data Quality Issues

#### Low Confidence Scores
```python
class ConfidenceTroubleshooter:
    """Diagnose and fix low confidence matches"""
    
    def analyze_low_confidence(self, match_result: MatchResult) -> List[str]:
        """Identify reasons for low confidence"""
        issues = []
        
        if match_result.confidence < 0.80:
            # Check data completeness
            if not match_result.price_entry.engine_model:
                issues.append("Missing engine information")
            
            if not match_result.price_entry.track_specifications:
                issues.append("Missing track specifications")
            
            # Check name similarity
            name_similarity = self._calculate_name_similarity(
                match_result.price_entry.product_name,
                match_result.catalog_product.name
            )
            if name_similarity < 0.70:
                issues.append(f"Low name similarity: {name_similarity:.2f}")
        
        return issues
    
    def suggest_improvements(self, issues: List[str]) -> List[str]:
        """Suggest specific fixes for confidence issues"""
        suggestions = []
        
        for issue in issues:
            if "Missing engine" in issue:
                suggestions.append("Review PDF parsing for engine extraction")
            elif "Low name similarity" in issue:
                suggestions.append("Check fuzzy matching parameters")
            elif "Missing track" in issue:
                suggestions.append("Verify track specification parsing")
        
        return suggestions
```

#### Data Inconsistencies
```python
class DataConsistencyChecker:
    """Detect and resolve data inconsistencies"""
    
    def check_specification_consistency(self, product: EnrichedProduct) -> List[str]:
        """Check for specification inconsistencies"""
        issues = []
        
        # Engine/weight correlation
        if product.engine.displacement_cc > 800 and product.weight.dry_weight_kg < 180:
            issues.append("Large engine with unusually low weight")
        
        # Track/category correlation
        if product.category == "Deep Snow" and product.track.length_mm < 3400:
            issues.append("Deep snow sled with short track")
        
        # Price/market correlation
        expected_price_range = self._get_expected_price_range(
            product.market, product.engine.displacement_cc
        )
        if not expected_price_range[0] <= product.price <= expected_price_range[1]:
            issues.append(f"Price outside expected range for {product.market}")
        
        return issues
```

### Performance Troubleshooting

#### Memory Issues
```python
class MemoryProfiler:
    """Monitor and optimize memory usage"""
    
    def profile_memory_usage(self, function_name: str):
        """Decorator to profile memory usage"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                import tracemalloc
                tracemalloc.start()
                
                result = func(*args, **kwargs)
                
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                logger.info(f"{function_name} memory usage: "
                           f"current={current/1024/1024:.1f}MB, "
                           f"peak={peak/1024/1024:.1f}MB")
                
                if peak > 2_000_000_000:  # 2GB limit
                    logger.warning(f"{function_name} exceeded memory limit")
                
                return result
            return wrapper
        return decorator

# Solutions for memory issues:
# 1. Use streaming for large files
# 2. Process in smaller batches
# 3. Clear intermediate data structures
# 4. Use generators instead of lists for large datasets
```

#### Processing Speed Issues
```python
class PerformanceTuner:
    """Optimize processing performance"""
    
    def identify_bottlenecks(self) -> List[str]:
        """Profile code to find performance bottlenecks"""
        
        # Common bottlenecks and solutions:
        bottlenecks = {
            "PDF parsing": "Use parallel processing for multiple PDFs",
            "Database queries": "Add missing indexes, use connection pooling",
            "Claude API calls": "Increase batch size, implement caching",
            "Data validation": "Optimize Pydantic models, cache validation results"
        }
        
        return bottlenecks
    
    def optimize_batch_processing(self, batch_size: int) -> int:
        """Find optimal batch size for processing"""
        # Test different batch sizes and measure performance
        # Return optimal size based on memory and speed constraints
```

## 🔧 Debugging Tools and Techniques

### Logging Configuration
```python
# Proper logging setup for debugging
import logging
from loguru import logger

# Configure loguru for development
logger.add("logs/debug_{time:YYYY-MM-DD}.log", 
          level="DEBUG", 
          rotation="1 day",
          retention="30 days")

# Configure for production
logger.add("logs/production_{time:YYYY-MM-DD}.log",
          level="INFO",
          rotation="1 day", 
          retention="90 days")

# Usage in code
logger.info("Processing price list", pdf_path=pdf_path, market=market)
logger.debug("Raw extraction result", data=raw_data)
logger.error("Failed to parse product", sku=sku, error=str(e))
```

### Debug Mode Configuration
```python
class DebugConfiguration:
    """Enhanced debugging capabilities"""
    
    def __init__(self):
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
    def enable_debug_features(self):
        if self.debug_mode:
            # Enable verbose logging
            logging.getLogger().setLevel(logging.DEBUG)
            
            # Save intermediate results
            self.save_intermediate_files = True
            
            # Disable Claude API calls (use mocks)
            self.mock_claude_api = True
            
            # Enable performance profiling
            self.enable_profiling = True
```

### Common SQL Debugging
```sql
-- Check for orphaned records
SELECT COUNT(*) FROM sku_mappings sm
LEFT JOIN products p ON sm.catalog_sku = p.sku
WHERE p.sku IS NULL;

-- Find low confidence matches requiring review
SELECT 
    price_sku,
    catalog_sku,
    confidence_score,
    matching_method
FROM sku_mappings
WHERE confidence_score < 0.95
ORDER BY confidence_score;

-- Check processing performance
SELECT 
    DATE(created_at) as processing_date,
    COUNT(*) as products_processed,
    AVG(confidence_score) as avg_confidence,
    COUNT(*) FILTER (WHERE requires_review) as review_needed
FROM sku_mappings
GROUP BY DATE(created_at)
ORDER BY processing_date DESC;
```

## 📞 Support and Escalation

### Self-Service Debugging
1. **Check logs first**: Review application logs for error details
2. **Run diagnostics**: Use built-in diagnostic tools
3. **Validate environment**: Ensure all dependencies are correct
4. **Test with samples**: Use known-good test data

### When to Escalate
- **Security vulnerabilities**: Immediate escalation required
- **Data corruption**: Stop processing and escalate
- **Performance degradation**: >50% slowdown
- **API quota exhaustion**: Cost impact requires approval

### Information to Include
- **Error messages**: Complete stack traces
- **Environment details**: Python version, Poetry lock file
- **Data samples**: Anonymized sample data causing issues
- **Performance metrics**: Timing and memory usage data
- **Steps to reproduce**: Detailed reproduction steps

### Emergency Procedures
```bash
# Stop all processing
poetry run python -m src.cli stop-all-processing

# Create emergency backup
poetry run python scripts/emergency_backup.py

# Check system health
poetry run python -m src.cli health-check --detailed

# Rollback to last known good state
poetry run python scripts/rollback_to_backup.py --backup-id <id>
```

## 🛠️ Diagnostic Tools

### System Health Check
```python
class SystemHealthChecker:
    """Comprehensive system health validation"""
    
    def run_health_check(self) -> HealthReport:
        """Run complete system health check"""
        
        checks = [
            self._check_database_connectivity(),
            self._check_claude_api_availability(),
            self._check_disk_space(),
            self._check_memory_usage(),
            self._check_processing_queue_status()
        ]
        
        return HealthReport(checks)
    
    def _check_database_connectivity(self) -> HealthCheck:
        """Verify database is accessible and responsive"""
        
    def _check_claude_api_availability(self) -> HealthCheck:
        """Test Claude API connectivity and quotas"""
        
    def _check_processing_queue_status(self) -> HealthCheck:
        """Check for stuck or failed processing jobs"""
```

### Performance Profiler
```python
class PerformanceProfiler:
    """Profile application performance"""
    
    def profile_pipeline_stage(self, stage_name: str):
        """Profile individual pipeline stages"""
        
    def generate_performance_report(self) -> PerformanceReport:
        """Generate detailed performance analysis"""
        
    def identify_optimization_opportunities(self) -> List[str]:
        """Suggest performance optimizations"""
```

---

**Emergency Contact**: If critical issues cannot be resolved using this guide, document the issue thoroughly and escalate immediately. Include all diagnostic information and steps already attempted.