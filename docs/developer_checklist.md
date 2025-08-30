# New Developer Competency Checklist
**Snowmobile Product Data Reconciliation System**

## 🎯 Immediate Expectations

The previous developer was terminated for failing to meet professional standards. This checklist ensures the new developer understands and can demonstrate competency in our established requirements.

## 📋 Day 1: Setup Validation

### Environment Setup (Must Complete 100%)
- [ ] **Poetry Configuration**: `pyproject.toml` configured correctly (NO requirements.txt)
- [ ] **Pre-commit Hooks**: Installed and passing all checks
- [ ] **Type Checking**: `mypy --strict` passes with zero errors
- [ ] **Code Quality**: `black`, `ruff`, `safety` all configured and passing
- [ ] **Testing Framework**: pytest with coverage ≥80% setup
- [ ] **Database**: PostgreSQL 15+ running with proper schema
- [ ] **Claude API**: Valid API key configured and tested
- [ ] **Git Workflow**: Proper branch naming and commit message format

### Competency Demonstration
```bash
# Must execute successfully:
make check-all          # All quality checks pass
make test-coverage      # 80%+ coverage achieved
make type-check         # Zero mypy errors
make security-scan      # No vulnerabilities
make db-migrate        # Database operations work
```

**Automatic Disqualification**: Any failure in setup validation indicates inability to follow basic professional standards.

## 🧪 Day 2-3: Technical Understanding

### Code Review Assessment
- [ ] **Pydantic Models**: Understands why we use Pydantic vs. dataclasses
- [ ] **Type Hints**: Can explain typing system and add hints correctly
- [ ] **Repository Pattern**: Understands separation of data access and business logic
- [ ] **Error Handling**: Can implement proper exception handling
- [ ] **Testing Strategy**: Writes meaningful tests, not just coverage fillers

### Practical Test: MVTL Case Study
Implement a test function that demonstrates understanding:

```python
def test_mvtl_complete_processing(self):
    """
    Process MVTL variant through complete pipeline
    Must demonstrate understanding of:
    - Data parsing and validation
    - Product matching logic
    - Claude API integration
    - Database operations
    - Error handling
    """
    
    # Input: Raw Finnish price list entry
    raw_entry = "MVTL|Backcountry|X-RS|850 E-TEC|137in/3500mm|Electric|10.25 in. Color Touchscreen|Scandi Blue|21 950,00 €"
    
    # Expected output: Complete product with specifications
    expected_output = {
        "sku": "MVTL",
        "confidence_score": 0.98,  # Must be ≥0.95
        "specifications": {
            "engine": {"model": "850 E-TEC", "displacement_cc": 849, "hp": 165},
            "track": {"length_mm": 3500, "width_mm": 381},
            "weight": {"dry_weight_kg": 203}
        }
    }
    
    # Implementation must follow all established patterns
```

### Technical Interview Questions
1. **Why PostgreSQL JSONB?** (Must understand flexible schema benefits)
2. **Confidence Scoring**: How do you determine 0.95 threshold?
3. **Claude API Optimization**: How do you minimize API costs?
4. **Error Recovery**: What happens when parsing fails?
5. **Performance**: How do you handle 1000+ product catalogs?

## 🎯 Week 1: Production Readiness

### Feature Implementation Test
**Assignment**: Implement a complete feature following all standards

#### Requirements
- [ ] **Feature**: Add support for new market (Denmark - DK)
- [ ] **Database**: Create migration for new market support
- [ ] **Parsing**: Handle Danish currency and language
- [ ] **Testing**: Comprehensive test suite with 80%+ coverage
- [ ] **Documentation**: Update all relevant documentation
- [ ] **Performance**: No degradation in processing speed

#### Validation Criteria
```python
# All of these must pass:
assert migration_is_reversible()
assert all_tests_pass_with_coverage_80_plus()
assert mypy_strict_zero_errors()
assert no_hardcoded_values()
assert proper_error_handling()
assert performance_benchmarks_met()
assert documentation_updated()
```

### Code Quality Assessment

#### Required Patterns (Must Demonstrate)
```python
# 1. Proper Pydantic model usage
class DanishPriceEntry(BaseModel):
    raw_sku: str = Field(regex=r'^[A-Z0-9]{3,6}$')
    price_dkk: Decimal = Field(gt=0)
    market: Literal["DK"] = "DK"

# 2. Repository pattern implementation
class DanishPriceRepository:
    async def save_price_entry(self, entry: DanishPriceEntry) -> None:
        # Database operations with proper error handling

# 3. Service layer with dependency injection
class DanishMarketService:
    def __init__(self, repository: DanishPriceRepository):
        self.repository = repository
    
    async def process_danish_prices(self, pdf_path: str) -> ProcessingResult:
        # Business logic with comprehensive error handling
```

#### Anti-Patterns (Immediate Rejection)
```python
# ❌ NEVER do this:
class Product:  # Using regular class instead of Pydantic
    def __init__(self, sku, price):
        self.sku = sku  # No type hints
        self.price = price

# ❌ Hardcoded values
CONFIDENCE_THRESHOLD = 0.95  # Should be configurable

# ❌ Poor error handling
try:
    result = api_call()
except:  # Generic exception handling
    pass

# ❌ Direct database access in business logic
def process_product(sku):
    cursor.execute("SELECT * FROM products WHERE sku = %s", (sku,))
```

## 🚨 Red Flags (Immediate Termination)

### Technical Red Flags
- [ ] Suggests using `requirements.txt` instead of Poetry
- [ ] Implements dataclasses when Pydantic is required
- [ ] Submits code with mypy errors
- [ ] Achieves <80% test coverage
- [ ] Includes hardcoded values in production code
- [ ] Uses TODO/FIXME comments in production code
- [ ] Bypasses pre-commit hooks
- [ ] Commits broken code to main branch

### Behavioral Red Flags
- [ ] Complains about Universal Development Standards
- [ ] Suggests "shortcuts" or "faster approaches"
- [ ] Doesn't read documentation thoroughly
- [ ] Asks questions answered in provided documentation
- [ ] Shows resistance to established patterns
- [ ] Delivers incomplete implementations
- [ ] Doesn't follow Git workflow conventions

## ✅ Success Indicators

### Technical Competency
- [ ] **First Implementation**: Follows all patterns correctly
- [ ] **Test Quality**: Tests are meaningful, not just coverage fillers
- [ ] **Code Reviews**: Provides constructive feedback on patterns
- [ ] **Performance**: Meets or exceeds established benchmarks
- [ ] **Documentation**: Updates are accurate and helpful

### Professional Behavior
- [ ] **Proactive Communication**: Regular progress updates
- [ ] **Problem Solving**: Researches before asking questions
- [ ] **Quality Focus**: Prioritizes correctness over speed
- [ ] **Continuous Improvement**: Suggests optimizations within established patterns
- [ ] **Team Collaboration**: Follows established code review process

## 🎓 Learning Path

### Week 1: Foundation
1. **Environment Mastery**: Complete setup without assistance
2. **Pattern Understanding**: Demonstrate repository/service patterns
3. **Testing Proficiency**: Write comprehensive test suites
4. **Quality Tools**: Master all code quality tools

### Week 2: Domain Expertise
1. **Pipeline Flow**: Understand complete data processing pipeline
2. **Claude Integration**: Optimize API usage and prompt engineering
3. **Database Operations**: Master PostgreSQL JSONB operations
4. **Performance Optimization**: Identify and resolve bottlenecks

### Week 3: Production Readiness
1. **Feature Delivery**: Complete features following all standards
2. **Error Handling**: Implement robust error recovery
3. **Monitoring**: Add comprehensive logging and metrics
4. **Documentation**: Maintain accurate project documentation

## 📊 Performance Benchmarks

### Code Quality Metrics
- **Cyclomatic Complexity**: <10 per function
- **Test Coverage**: ≥80% (target 90%+)
- **Type Coverage**: 100% (mypy --strict must pass)
- **Security Score**: Zero vulnerabilities in security scan

### Processing Benchmarks
- **MVTL Test Case**: <5 seconds end-to-end processing
- **Batch Processing**: 100 products in <60 seconds
- **Database Queries**: <100ms for typical operations
- **API Response**: <2 seconds for enrichment requests

## 📞 Final Validation

### Week 1 Deliverable
**Assignment**: Implement Danish market support with complete feature set

#### Must Include
1. **Database Migration**: Add DK market support
2. **Parser Enhancement**: Handle Danish price format
3. **Test Suite**: Comprehensive testing for new market
4. **Documentation**: Update all relevant docs
5. **Performance**: No regression in existing functionality

#### Success Criteria
```bash
# All must pass:
make validate-all        # 100% success
poetry run pytest -v     # All tests pass
make benchmark          # Performance maintained
make security-scan      # Zero vulnerabilities
git log --oneline -10   # Clean commit history
```

### Ongoing Evaluation
- **Daily**: Code commits with meaningful progress
- **Weekly**: Feature delivery meeting established timelines
- **Monthly**: Performance optimization and documentation updates

---

**Final Note**: These standards exist because the previous developer consistently failed to meet professional requirements. Competency in these areas is not negotiable - it's the minimum expectation for enterprise software development.