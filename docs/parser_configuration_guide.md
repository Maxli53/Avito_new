# Parser Configuration System Guide
**Intelligent PDF Processing with Dynamic Configuration Management**

## 🎯 Overview

The Parser Configuration System is an intelligent PDF processing framework that automatically selects optimal parsers, learns from new field discoveries, and adapts to different brands, markets, and document formats. This system transforms static PDF parsing into a dynamic, learning-based approach.

## 🏗️ System Architecture

### Core Components

```
PDF Input → Quality Assessor → Parser Router → Field Discovery → Configuration Update
    ↓             ↓                ↓              ↓                    ↓
Raw PDF → Quality Score → Optimal Parser → Known/Unknown → Learning Database
```

### Parser Stack
1. **PyMuPDF (Primary)** - Fast, accurate digital PDF processing
2. **Camelot (Specialized)** - Advanced table extraction for complex layouts
3. **Claude OCR (AI-Powered)** - Intelligent processing for scanned/damaged PDFs

## 📊 Configuration Structure

### Brand-Specific Configuration
```python
class BrandParserConfig(BaseModel):
    # Parser Selection
    primary_parser: PDFParserType = PDFParserType.PYMUPDF
    fallback_parsers: List[PDFParserType] = [PDFParserType.PDFPLUMBER, PDFParserType.CLAUDE_OCR]
    
    # Quality Thresholds
    ocr_confidence_threshold: float = 0.85
    min_table_confidence: float = 0.75
    
    # Field Mapping (Dynamic)
    known_field_mappings: Dict[str, str] = {
        "Tuote-nro": "model_code",
        "Malli": "malli", 
        "Paketti": "paketti",
        "Moottori": "moottori",
        "Kevätoptiot": "spring_options"
    }
    
    # Learning Behavior
    unknown_field_strategy: str = "claude_interpret"  # 'ignore', 'store_raw', 'claude_interpret'
    claude_interpretation_prompt: str = "..."
    
    # Performance Settings
    max_pages_per_batch: int = 50
    parallel_processing: bool = True
    max_workers: int = 4
```

### Market-Specific Configuration
```python
class MarketParserConfig(BaseModel):
    market_code: str = Field(regex=r"^[A-Z]{2}$")  # FI, SE, NO, DK
    currency_symbol: str
    decimal_separator: str = ","
    thousands_separator: str = "."
    
    # Market-specific field translations
    field_translations: Dict[str, str] = {
        "Väri": "color",    # Finnish
        "Färg": "color",    # Swedish  
        "Farge": "color",   # Norwegian
        "Farve": "color"    # Danish
    }
```

## 🔄 PDF Quality Assessment

### Quality Classifications
```python
class PDFQuality(Enum):
    DIGITAL_HIGH = "digital_high"      # Perfect digital PDF - PyMuPDF optimal
    DIGITAL_MEDIUM = "digital_medium"  # Minor issues - PyMuPDF with fallback
    SCANNED_GOOD = "scanned_good"      # Clear scan - PyMuPDF then Claude
    SCANNED_POOR = "scanned_poor"      # Poor scan - Direct to Claude OCR
    CORRUPTED = "corrupted"            # Damaged - Claude OCR only
```

### Quality Assessment Algorithm
```python
def assess_pdf_quality(pdf_path: str) -> PDFQuality:
    """Intelligent PDF quality assessment"""
    doc = fitz.open(pdf_path)
    
    # Analyze sample pages
    text_density_scores = []
    has_embedded_fonts = False
    
    for page_num in range(min(3, doc.page_count)):
        page = doc[page_num]
        
        # Calculate text density (digital indicator)
        text = page.get_text()
        page_area = page.rect.width * page.rect.height
        text_density = len(text.strip()) / (page_area / 1000)
        text_density_scores.append(text_density)
        
        # Check for embedded fonts (digital indicator)
        if page.get_fonts():
            has_embedded_fonts = True
    
    avg_text_density = sum(text_density_scores) / len(text_density_scores)
    
    # Classification logic
    if has_embedded_fonts and avg_text_density > 5.0:
        return PDFQuality.DIGITAL_HIGH
    elif avg_text_density > 2.0:
        return PDFQuality.DIGITAL_MEDIUM
    elif avg_text_density > 0.5:
        return PDFQuality.SCANNED_GOOD
    elif avg_text_density > 0.1:
        return PDFQuality.SCANNED_POOR
    else:
        return PDFQuality.CORRUPTED
```

## 🤖 Intelligent Parser Routing

### Router Decision Matrix
| PDF Quality | Primary | Fallback 1 | Fallback 2 | Expected Success |
|-------------|---------|------------|------------|------------------|
| digital_high | PyMuPDF | Camelot | Claude OCR | 98% |
| digital_medium | PyMuPDF | Camelot | Claude OCR | 95% |
| scanned_good | PyMuPDF | Claude OCR | - | 90% |
| scanned_poor | Claude OCR | - | - | 85% |
| corrupted | Claude OCR | - | - | 75% |

### Router Implementation
```python
def route_to_optimal_parser(pdf_path: str, quality: PDFQuality, config: BrandParserConfig) -> Parser:
    """Route PDF to optimal parser based on quality and configuration"""
    
    if quality in [PDFQuality.DIGITAL_HIGH, PDFQuality.DIGITAL_MEDIUM]:
        # Digital PDFs: Start with PyMuPDF
        primary_result = parse_with_pymupdf(pdf_path, config)
        
        if primary_result.confidence < 0.85:
            # Try Camelot for better table extraction
            camelot_result = parse_with_camelot(pdf_path, config)
            if camelot_result.confidence > primary_result.confidence:
                return camelot_result
        
        if primary_result.confidence < 0.70:
            # Final fallback to Claude
            return parse_with_claude_ocr(pdf_path, config)
            
        return primary_result
        
    elif quality == PDFQuality.SCANNED_GOOD:
        # Try PyMuPDF first, then Claude
        primary_result = parse_with_pymupdf(pdf_path, config)
        if primary_result.confidence < 0.60:
            return parse_with_claude_ocr(pdf_path, config)
        return primary_result
        
    else:  # SCANNED_POOR or CORRUPTED
        # Go directly to Claude OCR
        return parse_with_claude_ocr(pdf_path, config)
```

## 🔍 Field Discovery System

### Unknown Field Handling
```python
def handle_unknown_field(brand: str, field_name: str, field_value: str) -> FieldDiscoveryResult:
    """Process newly discovered fields"""
    
    config = parser_config.get_config_for_brand(brand)
    
    if config.unknown_field_strategy == "claude_interpret":
        # Use Claude to understand the field
        claude_result = claude_interpret_field(
            brand=brand,
            field_name=field_name,
            field_value=field_value,
            context="snowmobile price list parsing"
        )
        
        # Store discovery for learning
        discovery_id = store_field_discovery(
            brand=brand,
            field_name=field_name,
            field_value=field_value,
            claude_interpretation=claude_result
        )
        
        # Auto-update configuration if confidence is high
        if claude_result.get('confidence', 0) >= 0.90:
            update_field_mapping(brand, field_name, claude_result['mapped_to'])
            logger.info(f"✅ Auto-learned: {field_name} -> {claude_result['mapped_to']}")
        
        return FieldDiscoveryResult(
            discovery_id=discovery_id,
            action='interpreted',
            mapped_to=claude_result.get('mapped_to'),
            confidence=claude_result.get('confidence', 0.5)
        )
```

### Learning Examples
```python
# Example 1: New display specification discovered
original_field = "12.3 in Color Touchscreen"
claude_interpretation = {
    "field_type": "specification",
    "category": "display",
    "mapped_to": "display_specifications",
    "confidence": 0.95,
    "specifications": {
        "display_size_inches": 12.3,
        "display_type": "touchscreen",
        "display_color": "color"
    }
}

# Example 2: New spring option discovered
original_field = "Performance Edition"
claude_interpretation = {
    "field_type": "spring_option",
    "category": "performance_package", 
    "mapped_to": "spring_options",
    "confidence": 0.92,
    "modifications": {
        "suspension": "upgraded_performance",
        "track": "performance_track",
        "color_scheme": "performance_colors"
    }
}

# Example 3: New market-specific field
original_field = "Leveranstid"  # Swedish for delivery time
claude_interpretation = {
    "field_type": "metadata",
    "category": "logistics",
    "mapped_to": "delivery_time",
    "confidence": 0.88,
    "language": "swedish"
}
```

## 📈 Performance Monitoring

### Key Metrics Dashboard
```python
# Parser Performance Metrics
parser_stats = {
    "pymupdf": {
        "success_rate": 0.94,
        "avg_processing_time_ms": 450,
        "avg_confidence": 0.91,
        "documents_processed": 1247
    },
    "camelot": {
        "success_rate": 0.89,
        "avg_processing_time_ms": 1200,
        "avg_confidence": 0.87,
        "documents_processed": 156
    },
    "claude_ocr": {
        "success_rate": 0.82,
        "avg_processing_time_ms": 3400,
        "avg_confidence": 0.79,
        "documents_processed": 203
    }
}

# Field Discovery Statistics
field_discovery_stats = {
    "total_unknown_fields_discovered": 47,
    "successfully_classified": 42,
    "auto_learned_mappings": 38,
    "requiring_human_validation": 5,
    "average_classification_confidence": 0.89
}

# System Learning Progress
learning_progress = {
    "ski_doo_field_coverage": 0.96,  # 96% of fields automatically mapped
    "lynx_field_coverage": 0.94,
    "sea_doo_field_coverage": 0.91,
    "total_learned_patterns": 127,
    "configuration_updates_last_30_days": 23
}
```

### Real-Time Monitoring Queries
```sql
-- Parser performance by brand/date
SELECT 
    brand,
    parser_used,
    DATE(processed_at) as date,
    COUNT(*) as documents,
    AVG(processing_time_ms) as avg_time,
    AVG(extraction_confidence) as avg_confidence,
    COUNT(*) FILTER (WHERE success = FALSE) as failures
FROM parser_performance_log
WHERE processed_at >= NOW() - INTERVAL '7 days'
GROUP BY brand, parser_used, DATE(processed_at)
ORDER BY date DESC, avg_confidence DESC;

-- Unknown fields requiring attention
SELECT 
    brand,
    original_field_name,
    field_frequency,
    classification_confidence,
    human_validated,
    last_seen_at
FROM discovered_fields 
WHERE human_validated = FALSE 
AND field_frequency >= 3
ORDER BY field_frequency DESC, classification_confidence ASC;

-- Configuration update history
SELECT 
    brand,
    market,
    version,
    success_rate,
    total_documents_processed,
    created_at,
    created_by
FROM parser_configurations 
WHERE updated_at >= NOW() - INTERVAL '30 days'
ORDER BY updated_at DESC;
```

## 🛠️ Configuration Management

### Creating Brand Configuration
```python
def create_brand_configuration(brand: str, market: str, year: int) -> BrandParserConfig:
    """Create new brand configuration with sensible defaults"""
    
    base_config = BrandParserConfig(
        primary_parser=PDFParserType.PYMUPDF,
        fallback_parsers=[PDFParserType.CAMELOT, PDFParserType.CLAUDE_OCR],
        ocr_confidence_threshold=0.85,
        min_table_confidence=0.75,
        unknown_field_strategy="claude_interpret"
    )
    
    # Brand-specific customizations
    if brand == "Ski-Doo":
        base_config.known_field_mappings.update({
            "Tuote-nro": "model_code",
            "Malli": "malli",
            "Paketti": "paketti",
            "rMotion": "suspension_type"  # Ski-Doo specific
        })
        base_config.header_detection_patterns.extend([
            r"SUOSITUSHINNASTO", r"MXZ", r"Summit"
        ])
        
    elif brand == "Lynx":
        base_config.known_field_mappings.update({
            "Tuote-nro": "model_code", 
            "Trail": "category",
            "Crossover": "category",
            "KEVÄTENNAKKOMALLI": "spring_preview"  # Lynx specific
        })
        
    elif brand == "Sea-Doo":
        base_config.expected_language = "en"
        base_config.known_field_mappings = {
            "Model": "model_code",
            "Engine": "moottori", 
            "Features": "features",
            "Color": "color"
        }
    
    return base_config
```

### Updating Configuration
```python
def update_parser_configuration(
    brand: str,
    market: str, 
    year: int,
    updates: Dict[str, any]
) -> ConfigurationUpdateResult:
    """Update parser configuration with validation"""
    
    # Get current configuration
    current_config = get_parser_configuration(brand, market, year)
    
    # Validate updates
    validation_result = validate_configuration_updates(current_config, updates)
    if not validation_result.valid:
        raise ConfigurationValidationError(validation_result.errors)
    
    # Create new version
    new_version = current_config.version + 1
    updated_config = current_config.copy(update=updates)
    updated_config.version = new_version
    
    # Store new configuration
    store_parser_configuration(brand, market, year, updated_config)
    
    # Deactivate old configuration
    deactivate_configuration(current_config.id)
    
    logger.info(f"✅ Updated parser configuration: {brand}/{market}/{year} v{new_version}")
    
    return ConfigurationUpdateResult(
        success=True,
        new_version=new_version,
        changes=updates
    )
```

## 🔧 Development Usage

### Basic Usage
```python
from src.config.parser_configuration import parser_config

# Get configuration for brand
config = parser_config.get_config_for_brand("Ski-Doo")

# Process PDF with intelligent routing
result = parse_pdf_intelligent(
    pdf_path="2026_ski_doo_price_list.pdf",
    brand="Ski-Doo",
    market="FI"
)

# Handle results
if result.success:
    print(f"✅ Parsed with {result.parser_used} (confidence: {result.confidence:.2%})")
    for row in result.data:
        print(f"Product: {row.get('model_code')} - {row.get('malli')}")
else:
    print(f"❌ Parsing failed: {result.error_message}")
```

### Advanced Configuration
```python
# Custom configuration for new brand
custom_config = BrandParserConfig(
    primary_parser=PDFParserType.CAMELOT,  # Use Camelot as primary
    fallback_parsers=[PDFParserType.PYMUPDF, PDFParserType.CLAUDE_OCR],
    min_table_confidence=0.90,  # Higher quality threshold
    known_field_mappings={
        "Product_Code": "model_code",
        "Model_Name": "malli",
        "Engine_Spec": "moottori"
    },
    unknown_field_strategy="store_raw",  # Don't interpret unknown fields
    max_workers=2  # Reduce parallelism
)

# Register custom configuration
parser_config.brand_configs["NewBrand"] = custom_config
```

### Field Discovery Integration
```python
# Handle discovered fields in your processing
def process_with_field_discovery(pdf_data: List[Dict], brand: str):
    """Process data with automatic field discovery"""
    
    processed_data = []
    
    for row in pdf_data:
        processed_row = {}
        
        for field_name, field_value in row.items():
            # Check if field is known
            config = parser_config.get_config_for_brand(brand)
            
            if field_name in config.known_field_mappings:
                # Use known mapping
                mapped_field = config.known_field_mappings[field_name]
                processed_row[mapped_field] = field_value
            else:
                # Handle unknown field
                discovery_result = parser_config.handle_unknown_field(
                    brand=brand,
                    field_name=field_name,
                    field_value=field_value
                )
                
                if discovery_result['action'] == 'claude_interpretation_needed':
                    # Queue for Claude processing
                    queue_for_interpretation(discovery_result)
                
                # Store raw for now
                processed_row[f"unknown_{field_name}"] = field_value
        
        processed_data.append(processed_row)
    
    return processed_data
```

## 🎯 Best Practices

### Configuration Management
- **Version Control**: Always increment version numbers for configuration changes
- **Testing**: Test configuration changes with representative PDF samples
- **Rollback**: Keep previous versions for rollback capability
- **Documentation**: Document all configuration changes and reasoning

### Field Discovery
- **Validation**: Always validate auto-learned field mappings before production use
- **Monitoring**: Monitor field discovery accuracy and adjust confidence thresholds
- **Human Oversight**: Review unknown fields with low confidence scores
- **Context**: Provide rich context to Claude for better field interpretation

### Performance Optimization
- **Parser Selection**: Monitor parser performance and adjust routing logic
- **Batch Processing**: Process multiple PDFs in batches for efficiency
- **Caching**: Cache frequently accessed configurations
- **Monitoring**: Set up alerts for performance degradation

## 🚀 Future Enhancements

### Planned Features
- **Machine Learning Integration**: ML models for parser selection and field classification
- **Advanced Pattern Recognition**: Detect PDF layout patterns for optimal processing
- **Multi-Language Support**: Enhanced support for additional European languages  
- **Real-Time Configuration Updates**: Hot-reload configuration changes without restart
- **A/B Testing Framework**: Test different configurations and routing strategies

This Parser Configuration System transforms static PDF processing into an intelligent, adaptive system that continuously improves its accuracy and efficiency through learning and optimization.