# Snowmobile Product Data Reconciliation System

**Enterprise-grade pipeline for processing Nordic snowmobile price lists and product catalogs with Claude AI integration**

## 🎯 Project Overview

### Business Problem
Finnish and Nordic snowmobile dealers receive price lists with cryptic variant codes (like "MVTL", "UJTU") that don't directly match product catalog SKUs. This system solves the complex challenge of reconciling these disparate data sources to create a comprehensive, enriched product database suitable for e-commerce platforms.

### Core Transformation
**Input**: `MVTL` → "MXZ X-RS 850 E-TEC with Smart-Shox" → €23,670  
**Output**: Complete product record with 50+ technical specifications, marketing content, and full audit trail

## 🏗️ System Architecture

### Data Flow Pipeline
```
PDF Sources → Ingestion → Normalization → Staging → Matching → Enrichment → Production
     │             │            │           │         │           │            │
  Price Lists   Raw Data     Clean Data   Temp DB   SKU Map   Claude AI    Final DB
  Catalogues    Extract      Standardize   Store    Generate  Validate     Export
```

### Pipeline Stages

1. **INGESTION**: Multi-format PDF parsing with OCR error correction
2. **NORMALIZATION**: Finnish/Swedish → English, unit standardization
3. **STAGING**: Temporary storage with complete source attribution
4. **MATCHING**: 3-tier matching strategy (exact → fuzzy → Claude AI)
5. **ENRICHMENT**: Claude validates and fills specification gaps
6. **PRODUCTION**: Final verified data with comprehensive audit trail

## 📋 Key Deliverables

### Primary Outputs
- **Unified Product Database**: PostgreSQL with complete product specifications
- **WooCommerce Export**: Ready-to-import CSV/JSON for e-commerce
- **HTML Specification Sheets**: Customer-facing product documentation
- **Reconciliation Reports**: Detailed matching and validation results
- **API Endpoints**: RESTful access to enriched product data

### Quality Metrics
- **Matching Rate**: ≥95% of price entries successfully matched
- **Confidence Score**: ≥0.95 average for automated matches
- **Data Completeness**: 100% of critical specifications filled
- **Manual Review**: <5% of products requiring human intervention

## 🛠️ Technology Stack

### Core Dependencies
- **Python 3.10+** with Poetry dependency management
- **PostgreSQL 15+** with JSONB for flexible specifications
- **Claude API** for intelligent product matching and enrichment
- **SQLAlchemy 2.0** with Pydantic models for data validation
- **FastAPI** for API endpoints and monitoring

### Data Processing
- **PyMuPDF**: PDF extraction and OCR
- **pandas**: Data manipulation and analysis
- **fuzzy-wuzzy**: Approximate string matching
- **Pydantic**: Runtime data validation and serialization

## 📁 Project Structure

```
snowmobile-reconciliation/
├── pyproject.toml              # Poetry configuration
├── .pre-commit-config.yaml     # Code quality automation
├── Makefile                    # Development commands
├── docker-compose.yml          # Local development environment
├── README.md                   # This file
├── CHANGELOG.md                # Version history
├── .env.example                # Environment template
├── src/
│   ├── __init__.py
│   ├── models/                 # Pydantic data models
│   │   ├── domain.py          # Core business entities
│   │   ├── dto.py             # Data transfer objects
│   │   └── enums.py           # Type definitions
│   ├── services/              # Business logic layer
│   │   ├── enrichment.py      # Claude API integration
│   │   ├── matching.py        # Product matching algorithms
│   │   └── validation.py      # Data quality assurance
│   ├── repositories/          # Data access layer
│   │   ├── product.py         # Product data operations
│   │   ├── price.py           # Price list operations
│   │   └── mapping.py         # SKU mapping operations
│   ├── parsers/               # PDF processing modules
│   │   ├── base.py            # Base parser interface
│   │   ├── price_list.py      # Price list extraction
│   │   └── catalog.py         # Specification extraction
│   ├── exporters/             # Output generation
│   │   ├── woocommerce.py     # WooCommerce format export
│   │   ├── html.py            # Specification sheet generation
│   │   └── reports.py         # Analytics and reporting
│   ├── pipeline/              # Orchestration
│   │   ├── orchestrator.py    # Main pipeline controller
│   │   └── stages.py          # Individual processing stages
│   ├── api/                   # REST API endpoints
│   │   ├── endpoints.py       # API route definitions
│   │   └── middleware.py      # Authentication, logging
│   └── cli/                   # Command line interface
│       └── commands.py        # CLI command definitions
├── tests/                     # Comprehensive test suite
│   ├── conftest.py           # Test configuration
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── performance/          # Performance benchmarks
│   └── fixtures/             # Test data
├── docs/                     # Documentation
│   ├── api.md               # API documentation
│   ├── deployment.md        # Deployment guide
│   └── troubleshooting.md   # Common issues
├── data/                    # Source documents
│   ├── price_lists/         # Finnish price list PDFs
│   ├── catalogs/            # Product specification PDFs
│   └── samples/             # Test data samples
├── migrations/              # Database schema changes
├── scripts/                 # Deployment and maintenance
│   ├── deploy.py           # Deployment automation
│   └── backup.py           # Database backup utilities
└── monitoring/             # Performance monitoring
    ├── grafana/            # Dashboard configuration
    └── prometheus/         # Metrics collection
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 15+
- Poetry
- Claude API key

### Installation
```bash
# Clone repository
git clone <repository-url>
cd snowmobile-reconciliation

# Install dependencies
poetry install
poetry shell

# Setup pre-commit hooks
pre-commit install

# Initialize database
make db-setup

# Configure environment
cp .env.example .env
# Edit .env with your Claude API key and database credentials
```

### Basic Usage
```bash
# Process price list with full pipeline
poetry run python -m src.cli process-price-list \
  --pdf "data/price_lists/ski_doo_2026_fi.pdf" \
  --market FI \
  --year 2026

# Generate WooCommerce export
poetry run python -m src.cli export-woocommerce \
  --output "exports/ski_doo_2026.csv"

# Run validation suite
poetry run python -m src.cli validate-data \
  --confidence-threshold 0.95
```

## 🔧 Development Workflow

### Code Quality Standards
```bash
# Run all quality checks
make check-all

# Individual checks
make lint           # Code formatting and style
make type-check     # Type validation with mypy --strict
make test           # Full test suite with 80%+ coverage
make security-scan  # Security vulnerability assessment
```

### Development Commands
```bash
# Start local development environment
make dev-up

# Run tests with coverage
make test-coverage

# Performance profiling
make profile

# Database operations
make db-migrate     # Apply migrations
make db-backup      # Create backup
make db-reset       # Reset to clean state
```

## 📊 Pipeline Methodology

### Matching Strategy
The system employs a sophisticated 3-tier matching approach:

1. **Exact Match** (Primary): Direct SKU matching against catalog data
2. **Fuzzy Match** (Secondary): Approximate string matching with confidence scoring
3. **Claude AI Match** (Tertiary): Semantic understanding of product descriptions

### Confidence Scoring
Each match receives a confidence score (0.0-1.0):
- **≥0.95**: Automatic acceptance
- **0.80-0.94**: Flagged for review
- **<0.80**: Manual intervention required

### Data Validation Framework
- **Source Attribution**: Every data point traceable to source PDF and page
- **Multi-language Support**: Original Finnish/Swedish + English translations
- **Specification Completeness**: 100% target for critical specifications
- **Quality Assurance**: Automated validation with human oversight

## 🎯 Critical Success Factors

### Performance Requirements
- **Processing Speed**: 100 products/minute minimum
- **API Efficiency**: Batch processing (10 products per Claude call)
- **Memory Usage**: <2GB for typical price list processing
- **Database Performance**: <100ms for standard queries

### Data Quality Targets
- **Match Success Rate**: ≥95% automated matching
- **Specification Coverage**: 100% for engine, track, weight, dimensions
- **Error Rate**: <1% false positives in matching
- **Review Queue**: <5% manual intervention required

## 🔍 Example: MVTL Processing

### Input Processing
```
Raw Price List Entry:
MVTL | Backcountry | X-RS | 850 E-TEC | 137in/3500mm | Electric | 10.25 in. Color Touchscreen Display | Scandi Blue | €21,950.00
```

### Matching Logic
1. **Parse Components**: Extract model family (Backcountry), trim (X-RS), engine (850 E-TEC)
2. **Catalog Search**: Find matching specifications in product catalogs
3. **Claude Enrichment**: Validate match and fill missing specifications
4. **Confidence Assessment**: Score match quality (target ≥0.95)

### Final Output
```json
{
  "sku": "MVTL",
  "product_name": "MXZ X-RS 850 E-TEC Backcountry",
  "price": 21950.00,
  "currency": "EUR",
  "market": "FI",
  "specifications": {
    "engine": {
      "model": "850 E-TEC",
      "displacement_cc": 849,
      "hp": 165,
      "type": "liquid-cooled-two-stroke"
    },
    "track": {
      "length_mm": 3500,
      "width_mm": 381,
      "profile": "2.5in-64mm-powdermax"
    },
    "weight": {
      "dry_weight_kg": 203
    }
  },
  "confidence_score": 0.98,
  "source_attribution": ["price_list_2026_fi.pdf:page_2", "catalog_2026_specifications.pdf:page_45"]
}
```

## 📈 Monitoring and Analytics

### Key Performance Indicators
- **Processing Throughput**: Products processed per hour
- **Match Quality Distribution**: Confidence score histogram
- **Manual Review Queue**: Items requiring human validation
- **API Cost Tracking**: Claude API usage and optimization
- **Database Performance**: Query response times and optimization

### Quality Assurance Reports
- **Daily Processing Summary**: Automated email reports
- **Weekly Quality Review**: Match accuracy and error analysis
- **Monthly Cost Analysis**: API usage and optimization recommendations

## 🚀 Deployment

### Production Environment
```bash
# Build and deploy
make build
make deploy-staging    # Staging environment validation
make deploy-prod       # Production deployment (manual approval)

# Monitor deployment
make health-check
make logs
make metrics
```

### Environment Configuration
```bash
# Production environment variables
DATABASE_URL=postgresql://user:pass@prod-db:5432/snowmobile_prod
CLAUDE_API_KEY=sk-ant-api03-...
ENVIRONMENT=production
LOG_LEVEL=INFO
REDIS_URL=redis://prod-redis:6379/0
```

## 🎯 Business Value

### Immediate Benefits
- **Time Savings**: Eliminates manual price-catalog reconciliation (80+ hours → 2 hours)
- **Accuracy Improvement**: 99%+ accuracy vs. 85% manual process
- **E-commerce Ready**: Direct WooCommerce import capability
- **Multi-market Support**: Handles Finnish, Swedish, Norwegian price lists

### Long-term Value
- **Scalability**: Process any number of product catalogs
- **Consistency**: Standardized product data across all channels
- **Automation**: Seasonal price updates with minimal manual intervention
- **Quality Assurance**: Built-in validation and confidence scoring

## ⚠️ Development Requirements

This project must adhere to the **Universal Development Standards**:

- ✅ **Python 3.10+** with Poetry (NEVER requirements.txt)
- ✅ **Pydantic models** for all data structures (NEVER dataclasses)
- ✅ **Type hints** on all functions and classes
- ✅ **80%+ test coverage** with comprehensive test suite
- ✅ **mypy --strict** with zero errors
- ✅ **Security validation** and input sanitization
- ✅ **Performance testing** with benchmarks
- ✅ **Pre-commit hooks** for code quality automation

**Automatic rejection criteria**: Using requirements.txt, missing type hints, test coverage below 80%, hardcoded values, TODO/FIXME comments in production code.

## 📞 Support

### Common Issues
- **Claude API Rate Limits**: Increase batch processing delays
- **PDF Parsing Errors**: Validate PDF format and OCR quality
- **Database Performance**: Check indexes and query optimization
- **Memory Usage**: Monitor large file processing and batch sizes

### Getting Help
- Check `docs/troubleshooting.md` for detailed solutions
- Review `CHANGELOG.md` for recent changes
- Submit issues with complete error logs and environment details

---

**Note**: This system processes sensitive pricing data. Ensure all security protocols are followed and API keys are properly secured.