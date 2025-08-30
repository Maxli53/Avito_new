# Developer Onboarding Guide
**Snowmobile Product Data Reconciliation System**

## 🎯 Welcome

You're joining a critical project that processes Nordic snowmobile price lists and product catalogs. This system uses Claude AI to intelligently match cryptic variant codes to full product specifications, then exports the data to e-commerce platforms.

## 📚 Required Reading (Day 1)

### Essential Documents
1. **Universal Development Standards** - Non-negotiable professional requirements
2. **README.md** - Project overview and architecture
3. **New_approach.md** - Technical implementation details and database schema
4. **Data-Driven Validation.md** - Validation methodology and confidence scoring

### Key Concepts to Understand

#### The Core Challenge
Finnish price lists contain codes like `MVTL`, `UJTU`, `VETA` that represent specific snowmobile configurations. These codes must be matched to actual product SKUs and enriched with 50+ technical specifications from separate catalog documents.

#### Example Data Flow
```
Price List Input:
MVTL | Backcountry | X-RS | 850 E-TEC | 137in/3500mm | €21,950.00

Catalog Lookup:
MXZ X-RS 850 E-TEC → Engine: 165HP, Track: 3500x381mm, Weight: 203kg

Final Output:
Complete product with full specifications, marketing content, confidence score
```

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
- `src/models/domain.py` - Pydantic models for all data structures
- `src/services/enrichment.py` - Claude API integration
- `src/services/matching.py` - Product matching algorithms
- `src/pipeline/orchestrator.py` - Main pipeline controller

#### Database Layer
- `src/repositories/` - All database operations (NO direct SQL in business logic)
- `migrations/` - Database schema changes (Alembic)
- `scripts/db_init.py` - Database initialization

#### Testing Strategy
- `tests/unit/` - Component testing (80%+ coverage required)
- `tests/integration/` - End-to-end pipeline testing
- `tests/performance/` - Load and benchmark testing
- `tests/fixtures/` - Test data and mocks

### Data Flow Understanding

#### Input Sources
1. **Price Lists**: Finnish PDFs with variant codes and pricing
2. **Product Catalogs**: Technical specification PDFs
3. **Previous Enrichments**: Database of existing product data

#### Processing Stages
1. **PDF Extraction**: Raw text and table extraction
2. **Data Normalization**: Language and unit standardization
3. **Product Matching**: 3-tier matching strategy
4. **Claude Enrichment**: AI-powered validation and gap filling
5. **Quality Assurance**: Confidence scoring and error detection

#### Output Generation
1. **Database Storage**: PostgreSQL with JSONB specifications
2. **WooCommerce Export**: E-commerce platform integration
3. **HTML Specifications**: Customer-facing documentation
4. **Analytics Reports**: Processing and quality metrics

## 🎯 First Week Goals

### Days 1-2: Foundation
- [ ] Complete environment setup and tool installation
- [ ] Understand Universal Development Standards thoroughly
- [ ] Review existing codebase and database schema
- [ ] Run full test suite and achieve 100% pass rate

### Days 3-4: Core Understanding
- [ ] Trace through MVTL test case end-to-end
- [ ] Understand Claude API integration patterns
- [ ] Review PostgreSQL schema and JSONB usage
- [ ] Study product matching algorithms

### Day 5: Hands-on Development
- [ ] Implement small feature or bug fix
- [ ] Write comprehensive tests
- [ ] Pass all code quality checks
- [ ] Submit first pull request

## 🚨 Critical Success Factors

### Non-Negotiable Requirements
1. **Type Safety**: All functions must have complete type hints
2. **Test Coverage**: Minimum 80% coverage maintained
3. **Pydantic Models**: All data structures use Pydantic (NEVER dataclasses)
4. **Error Handling**: Comprehensive exception handling with custom exceptions
5. **Performance**: Meeting defined benchmarks for processing speed

### Immediate Rejection Criteria
- Using `requirements.txt` instead of Poetry
- Missing type hints on any function
- Test coverage below 80%
- Hardcoded values in production code
- TODO/FIXME comments in production code
- JavaScript/TypeScript files in `src/` directory

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

## 🔍 Understanding the Data

### Finnish Price List Format
```
Tuote-nro | Malli | Paketti | Moottori | Telamet | Käynnistin | Mittaristo | Kevätjousi | Väri | Suositushinta sis ALV%
MVTL | Backcountry | X-RS | 850 E-TEC | 137in/3500mm | Electric | 10.25 in. Color Touchscreen | Scandi Blue | 21 950,00 €
```

### Product Catalog Structure
- **Engine Specifications**: Displacement, HP, cooling type, fuel system
- **Track Details**: Length, width, profile, stud compatibility
- **Suspension**: Front/rear types, travel, adjustability
- **Dimensions**: Length, width, height, weight
- **Features**: Display type, starter, storage, accessories

### Matching Complexity
- **Language Barriers**: Finnish descriptions → English specifications
- **Unit Conversions**: Metric ↔ Imperial conversions
- **Variant Codes**: Cryptic codes → Full product names
- **Feature Mapping**: Marketing names → Technical specifications

## 🧪 Testing Philosophy

### Test-Driven Development
- Write tests BEFORE implementing features
- Achieve 80%+ coverage on all new code
- Include performance tests for critical paths
- Mock external dependencies (Claude API, database)

### Test Categories
1. **Unit Tests**: Individual component testing
2. **Integration Tests**: End-to-end pipeline testing
3. **Performance Tests**: Speed and memory benchmarks
4. **Load Tests**: High-volume processing validation

## 📞 Getting Help

### Code Review Process
1. Create feature branch from `develop`
2. Implement with comprehensive tests
3. Run `make validate-all` locally
4. Submit pull request with checklist completed
5. Address review feedback promptly

### Escalation Path
- **Technical Questions**: Review existing documentation first
- **Architecture Decisions**: Discuss in team meetings
- **Urgent Issues**: Document thoroughly before escalating
- **Performance Problems**: Include profiling data

---

**Remember**: This project handles sensitive pricing data and must meet enterprise security standards. Every line of code is subject to strict quality requirements. Success depends on following the Universal Development Standards without exception.