# Developer Onboarding Guide
**Snowmobile Product Data Reconciliation System**

## 🎯 Welcome

You're joining a critical project that processes Nordic snowmobile price lists and product catalogs using a **5-stage inheritance pipeline**. This system uses Claude AI to intelligently transform cryptic model codes into comprehensive product specifications suitable for e-commerce platforms.

## 📚 Required Reading (Day 1)

### Essential Documents
1. **Universal Development Standards** - Non-negotiable professional requirements
2. **Project Methodology and Technical Implementation** - Complete 5-stage pipeline architecture, validation methodology, and confidence scoring
3. **Pipeline Terminology Reference** - Standardized terminology (Model Code → Model → Model Family → Base Model)
4. **Database Schema - Inheritance Pipeline** - Complete database design and technical implementation details

### Key Concepts to Understand

#### The Core Challenge
Finnish price lists contain model codes like `LTTA`, `MVTL`, `UJTU` that represent specific snowmobile configurations. These codes must be **constructed into complete products** using catalog base models and Claude AI enhancement.

#### Example Data Flow
```
Price List Input:
LTTA | Rave | RE | 600R E-TEC | 129in/3300mm | Manual | €18,750.00

Stage 1: Base Model Matching
"Rave RE" → Lynx Rave RE catalog section (inheritance template)

Stage 2-4: Inheritance + Selection + Spring Options
Complete LTTA with 50+ technical specifications

Stage 5: Validation
Final product with confidence score ≥0.95 (auto-accept)
```

#### **NOT a Matching Problem - It's Construction!**
```
❌ OLD THINKING: Match LTTA against existing catalog products
✅ NEW REALITY: Construct complete LTTA using inheritance pipeline
```

## 🏗️ Architecture Understanding

### 5-Stage Inheritance Pipeline

#### **Stage 1: Base Model Matching**
- Extract model family from price entry (`Rave + RE`)
- Match to catalog base model (`Lynx Rave RE section`)
- 95%+ success rate with exact lookup
- Claude semantic matching for edge cases

#### **Stage 2: Full Specification Inheritance**
- Inherit ALL specifications from base model
- Platform, suspension, available options
- Creates complete template for customization

#### **Stage 3: Variant Selection**
- Select specific engine, track, features from price entry
- Apply selections to inherited specifications
- Build model-specific configuration

#### **Stage 4: Spring Options Enhancement**
- Research spring options using Claude domain knowledge
- Apply modifications (color, track, suspension, etc.)
- **Mission Critical**: Proper spring option interpretation

#### **Stage 5: Final Validation**
- Multi-layer validation (Claude + technical + business rules)
- Confidence scoring and auto-accept determination
- Complete audit trail generation

## 🛠️ Development Environment Setup

### Day 1 Setup Checklist
```bash
# 1. Clone and environment setup
git clone <repository-url>
cd snowmobile-reconciliation
poetry install
poetry shell

# 2. Install development tools
pre-commit install
make check-all  # Must pass 100%

# 3. Database setup
createdb snowmobile_dev
poetry run alembic upgrade head

# 4. Environment configuration
cp .env.example .env
# Configure Claude API key and database URL

# 5. Verify setup
make test-coverage  # Must achieve 80%+
make type-check     # mypy --strict must pass
```

### Mandatory Tool Configuration
```bash
# Git configuration
git config --global user.name "Your Name"
git config --global user.email "your.email@company.com"

# Pre-commit validation
pre-commit run --all-files  # Must pass

# IDE setup (VS Code recommended)
# Install extensions: Python, mypy, Black, Ruff
```

## 🧭 Project Navigation

### Critical Code Locations

#### Core Business Logic
- `src/models/domain.py` - Pydantic models for all data structures (see Universal Development Standards)
- `src/services/claude_enrichment.py` - Claude API integration and batching (see Project Methodology)
- `src/pipeline/inheritance_pipeline.py` - Main 5-stage pipeline controller (see Project Methodology)
- `src/services/base_model_matching.py` - Stage 1 implementation (see Database Schema documentation)
- `src/services/spring_options.py` - Stage 4 spring options processing (see Project Methodology)

#### Database Layer
- `src/repositories/product_repository.py` - Product data operations (see Database Schema documentation)
- `src/repositories/base_model_repository.py` - Catalog base model storage (see Database Schema documentation)
- `migrations/` - Database schema changes (Alembic) (see Database Schema documentation)
- `scripts/catalog_ingestion.py` - Import catalog data (see Project Methodology)

#### Pipeline Implementation
- `src/pipeline/stages/` - Individual stage implementations (see Project Methodology for each stage)
- `src/pipeline/validation/` - Multi-layer validation framework (see Project Methodology validation section)
- `src/pipeline/confidence.py` - Confidence scoring algorithms (see Project Methodology confidence scoring)

#### Testing Strategy
- `tests/unit/pipeline/` - Pipeline stage testing (80%+ coverage required)
- `tests/integration/` - End-to-end pipeline testing
- `tests/performance/` - Load and benchmark testing
- `tests/fixtures/` - Test data (LTTA, MVTL test cases)

### Data Flow Understanding

#### Input Sources
1. **Price Lists**: Finnish PDFs with model codes and pricing
2. **Product Catalogs**: Technical specification PDFs (base models)
3. **Previous Processing**: Database of existing model mappings

#### Processing Architecture
1. **PDF Extraction**: Raw text and table extraction with Claude OCR correction
2. **Data Normalization**: Language and unit standardization
3. **5-Stage Inheritance Pipeline**: Core product construction
4. **Quality Assurance**: Confidence scoring and validation
5. **Output Generation**: Complete products with full specifications

#### Output Generation
1. **Database Storage**: PostgreSQL with JSONB specifications and inheritance audit trails
2. **WooCommerce Export**: E-commerce platform integration
3. **HTML Specifications**: Customer-facing product documentation
4. **Analytics Reports**: Processing quality and performance metrics

## 🎯 First Week Goals

### Days 1-2: Foundation
- [ ] Complete environment setup and tool installation
- [ ] Understand Universal Development Standards thoroughly
- [ ] Review 5-stage inheritance pipeline architecture
- [ ] Run full test suite and achieve 100% pass rate

### Days 3-4: Pipeline Understanding
- [ ] Trace through LTTA test case end-to-end (all 5 stages)
- [ ] Understand Claude API integration and batching patterns
- [ ] Review base model catalog structure and inheritance
- [ ] Study spring options detection and processing

### Day 5: Hands-on Development
- [ ] Implement small pipeline enhancement or bug fix
- [ ] Write comprehensive tests covering new functionality
- [ ] Pass all code quality checks (mypy --strict, 80%+ coverage)
- [ ] Submit first pull request following all standards

## 🚨 Critical Success Factors

### Non-Negotiable Requirements
1. **Type Safety**: All functions must have complete type hints
2. **Test Coverage**: Minimum 80% coverage maintained across all pipeline stages
3. **Pydantic Models**: All data structures use Pydantic (NEVER dataclasses)
4. **Error Handling**: Comprehensive exception handling with audit trails
5. **Performance**: Pipeline must process 100+ products/minute

### Immediate Rejection Criteria
- Using `requirements.txt` instead of Poetry
- Missing type hints on any function
- Test coverage below 80%
- Hardcoded values in production code
- TODO/FIXME comments in production code
- References to old "3-tier matching" approach

## 🎓 Learning Path

### Week 1: Foundation
1. **Environment Mastery**: Complete setup without assistance
2. **Pipeline Architecture**: Understand all 5 stages thoroughly
3. **Testing Proficiency**: Write comprehensive test suites for pipeline stages
4. **Quality Tools**: Master all code quality tools and validation

### Week 2: Domain Expertise
1. **Base Model Inheritance**: Master catalog structure and inheritance patterns (see Database Schema documentation)
2. **Claude Integration**: Optimize API usage, prompt engineering, and batching (see Project Methodology Claude integration sections)
3. **Spring Options**: Understand detection and enhancement patterns (see Project Methodology spring options processing)
4. **Database Operations**: Master PostgreSQL JSONB operations and audit trails (see Database Schema documentation)

### Week 3: Production Readiness
1. **Feature Delivery**: Complete pipeline enhancements following all standards
2. **Error Handling**: Implement robust error recovery and audit trails
3. **Monitoring**: Add comprehensive logging and performance metrics
4. **Performance Optimization**: Identify and resolve pipeline bottlenecks

### Week 4: Advanced Implementation
1. **Claude Optimization**: Advanced prompt engineering and result validation (see Project Methodology Claude sections)
2. **Database Performance**: Query optimization and indexing strategies (see Database Schema performance sections)
3. **Pipeline Extensions**: Support for new brands/markets (see Project Methodology for extensibility patterns)
4. **Quality Assurance**: Advanced validation patterns and confidence tuning (see Project Methodology validation framework)

## 🔍 Key Technical Patterns

### Inheritance Pipeline Pattern
```python
@dataclass
class PipelineStage:
    """Base class for all pipeline stages"""
    stage_name: str
    
    async def process(self, input_data: Dict) -> StageResult:
        try:
            result = await self._execute_stage(input_data)
            return StageResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Stage {self.stage_name} failed", error=str(e))
            return StageResult(success=False, error=str(e))
    
    async def _execute_stage(self, input_data: Dict) -> Dict:
        raise NotImplementedError
```

### Claude API Optimization
```python
class ClaudeService:
    """Optimized Claude API integration"""
    
    async def batch_enrich(self, products: List[Dict]) -> List[EnrichmentResult]:
        """Process multiple products in single API call"""
        
        # Batch up to 5 products per call for efficiency
        batches = chunk_list(products, batch_size=5)
        
        results = []
        for batch in batches:
            batch_result = await self._process_batch(batch)
            results.extend(batch_result)
            
        return results
```

### Database Audit Trail Pattern
```python
def build_inheritance_audit_trail(final_specs: Dict, price_entry: Dict) -> Dict:
    """Create complete audit trail for debugging and validation"""
    
    return {
        "original_model_code": price_entry.get("tuote_nro"),
        "base_model_matched": final_specs.get("base_model_source"),
        "inheritance_timestamp": datetime.utcnow().isoformat(),
        "selections_applied": final_specs.get("variant_selections", {}),
        "spring_options_processed": final_specs.get("spring_modifications", {}),
        "confidence_breakdown": final_specs.get("confidence_components", {}),
        "validation_results": final_specs.get("validation_summary", {})
    }
```

## 📊 Performance Benchmarks

### Pipeline Performance Targets
- **Stage 1 (Base Model Matching)**: <200ms per product
- **Stage 2-3 (Inheritance + Selection)**: <100ms per product
- **Stage 4 (Spring Options)**: <500ms per product (includes Claude API)
- **Stage 5 (Validation)**: <300ms per product (includes Claude validation)
- **Total Pipeline**: <1.1 seconds per product

### Quality Targets
- **Base Model Match Success**: ≥95%
- **Overall Pipeline Success**: ≥99%
- **Auto-Accept Rate**: ≥95% (confidence ≥0.95)
- **Spring Options Resolution**: 100% for populated fields

## 🔧 Common Debugging Patterns

### Pipeline Stage Debugging
```python
# Enable detailed logging for specific stages
logger.setLevel(logging.DEBUG)

# Trace pipeline execution
with pipeline_tracer(model_code="LTTA") as tracer:
    result = await inheritance_pipeline.process(price_entry)
    tracer.log_stage_results()
```

### Claude API Debugging
```python
# Mock Claude API for testing
@pytest.fixture
def mock_claude_service():
    with patch('src.services.claude_enrichment.ClaudeService') as mock:
        mock.return_value.batch_enrich.return_value = mock_enrichment_results()
        yield mock
```

This onboarding guide provides the foundation for understanding our inheritance-based product construction pipeline. The focus is on **building complete products** rather than matching existing ones, using systematic inheritance and Claude AI enhancement.