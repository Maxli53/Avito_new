# 🛷 Snowmobile Dual Parser Pipeline

**Intelligent PDF-to-Product Pipeline with Claude-Powered Inheritance**

A streamlined data pipeline that transforms snowmobile price lists and product catalogs (PDFs) into complete, market-ready product specifications with HTML output. The system uses deterministic matching followed by Claude AI intelligent inheritance to resolve product variations.

## 🎯 Core Concept

```mermaid
graph LR
    PL[Price List PDFs] --> PE[(price_entries)]
    CAT[Catalog PDFs] --> BMC[(base_models_catalog)]
    PE --> MATCH[Deterministic<br/>Matching]
    BMC --> MATCH
    MATCH --> CLAUDE[Claude Intelligent<br/>Inheritance]
    CLAUDE --> PROD[(products)]
    PROD --> HTML[HTML Output]
```

**Key Innovation**: Model codes in price lists contain deterministic mappings to base models in catalogs. Claude AI intelligently adjusts base specifications based on specific model code variations.

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone or create the project directory
cd TEST_DUAL_PARSER_PIPELINE

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env with your database URL and Claude API key
```

### 2. Database Setup

```bash
# Create PostgreSQL database
createdb snowmobile_dual_parser

# Run schema setup
psql -d snowmobile_dual_parser -f schema.sql
```

### 3. Configure Environment

Edit `.env` file:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/snowmobile_dual_parser
CLAUDE_API_KEY=sk-ant-your-claude-api-key-here
API_HOST=0.0.0.0
API_PORT=8000
```

### 4. Run the System

**API Server:**
```bash
python main.py api
```

**CLI Interface:**
```bash
# Process all new documents
python main.py cli process

# Upload a price list
python main.py cli upload-price-list --pdf-path price_list.pdf --brand Lynx --market FI --year 2026

# Upload a catalog  
python main.py cli upload-catalog --pdf-path catalog.pdf --brand Lynx --year 2026

# Get status
python main.py cli status
```

## 📋 System Overview

### Data Flow

1. **Price List Extraction**: Extract structured data from price list PDFs
2. **Catalog Extraction**: Extract base model specifications from catalog PDFs
3. **Deterministic Matching**: Match price entries to base models using lookup keys
4. **Claude Inheritance**: Intelligently resolve specifications using Claude AI
5. **Product Generation**: Create final products with HTML output

### Key Components

- **Price Lists**: Finnish market price data with model codes and specific configurations
- **Catalogs**: Complete product specification books with all possible variations
- **Matching**: Deterministic lookup key matching with fuzzy fallback
- **Claude AI**: Intelligent specification inheritance and HTML generation
- **Products**: Final output with resolved specs and HTML sheets

## 🔧 Architecture

### Service Layer
```
src/
├── api/                 # FastAPI web interface
├── services/           # Core business logic
│   ├── price_extractor.py      # PDF price list extraction
│   ├── catalog_extractor.py    # PDF catalog extraction
│   ├── matching_service.py     # Deterministic matching
│   └── claude_inheritance.py   # AI-powered inheritance
├── pipeline/           # Orchestration
├── repositories/       # Data access
└── models/            # Domain models
```

### Database Schema
```sql
-- Core tables
price_lists              # Metadata for uploaded price PDFs
price_entries           # Extracted price data
catalogs                # Metadata for uploaded catalog PDFs  
base_models_catalog     # Extracted base model specifications
products                # Final generated products
```

## 🎮 API Endpoints

### Document Upload
- `POST /api/price-lists/upload` - Upload price list PDF
- `POST /api/catalogs/upload` - Upload catalog PDF

### Processing
- `POST /api/pipeline/run` - Run complete pipeline
- `POST /api/products/generate` - Generate products from matched entries

### Data Access
- `GET /api/products/{sku}` - Get product details
- `GET /api/products/{sku}/html` - Get HTML specification sheet
- `GET /api/status` - Pipeline status and statistics

### Monitoring
- `GET /api/jobs/{job_id}/status` - Check job status
- `GET /api/health` - Health check
- `GET /api/statistics` - Detailed statistics

## 📊 Example Data Flow

### Input: Price List Entry
```
Model Code | Malli | Paketti | Moottori    | Telamatto      | Hinta
LTTA      | Rave  | RE      | 600R E-TEC  | 137in 3500mm   | €18,750.00
```

### Input: Catalog Base Model
```
Model Family: Rave RE
Available Engines: [600R E-TEC, 850 E-TEC, 850 E-TEC Turbo R]
Available Tracks: [129in, 137in, 146in, 154in]
Features: ["Electric starter", "LED headlights", "Quick-release seat", ...]
```

### Output: Resolved Product
```json
{
  "sku": "LYNX-LTTA-FI-2026",
  "specifications": {
    "engine": {
      "displacement": "600R",
      "type": "E-TEC",
      "power": "125 HP"
    },
    "track": {
      "length": "137 inches",
      "width": "3500mm",
      "type": "Cobra"
    },
    "features": ["LED headlights", "Quick-release seat"]
  },
  "html_content": "<html>...</html>"
}
```

## 🔍 Processing Statistics

### Expected Performance
- **Matching Success Rate**: >90% deterministic matches
- **Processing Time**: <30 seconds per product
- **Claude API Cost**: <$0.50 per product
- **Confidence Score**: >0.95 for auto-approval

### Volume Expectations
- **Price Lists**: 4-5 markets × 3 brands × monthly updates = ~15/month
- **Products**: ~200-300 per price list = ~3,000-4,500/month

## 🛠️ Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
flake8 src/
```

### Database Migrations
```bash
# Run schema updates
psql -d snowmobile_dual_parser -f schema_updates.sql
```

## 📈 Monitoring Queries

```sql
-- Processing success rate
SELECT 
    COUNT(*) FILTER (WHERE status = 'completed') * 100.0 / COUNT(*) as success_rate,
    AVG(confidence_score) as avg_confidence
FROM products
WHERE created_at >= NOW() - INTERVAL '7 days';

-- Unmatched entries requiring attention
SELECT 
    pe.model_code,
    pe.malli,
    pe.paketti,
    pe.catalog_lookup_key,
    COUNT(*) as occurrences
FROM price_entries pe
LEFT JOIN base_models_catalog bmc ON pe.catalog_lookup_key = bmc.lookup_key
WHERE bmc.id IS NULL
GROUP BY 1,2,3,4
ORDER BY occurrences DESC;
```

## 🚀 Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py", "api"]
```

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@localhost/snowmobile_db
CLAUDE_API_KEY=sk-ant-...
PDF_STORAGE_PATH=/data/pdfs
HTML_OUTPUT_PATH=/data/html
LOG_LEVEL=INFO
```

## 📝 License

This project is part of the Avito snowmobile data processing system.

## 🤝 Contributing

1. Follow the established code patterns
2. Add tests for new functionality
3. Update documentation
4. Ensure all tests pass

## 🔧 Troubleshooting

### Common Issues

**Database Connection Errors**:
- Check DATABASE_URL format
- Ensure PostgreSQL is running
- Verify credentials

**Claude API Errors**:
- Verify CLAUDE_API_KEY is set
- Check API rate limits
- Monitor token usage

**PDF Processing Failures**:
- Check PDF file permissions
- Ensure PDFs are not password protected
- Verify PDF format compatibility

### Logs

Check application logs:
```bash
tail -f logs/pipeline.log
```

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python main.py api
```