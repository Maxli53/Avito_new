# ReportLab Integration Guide

## Overview

This guide explains how to integrate the Unified ReportLab Vehicle Specification Generator into your existing 5-stage inheritance pipeline system. The integration adds professional PDF specification sheet generation as a natural extension of your product processing workflow.

## 🎯 Integration Objectives

- **Seamless Pipeline Integration**: Add PDF generation as Stage 6 after Final Validation
- **Multi-Brand Support**: Handle Lynx, Ski-Doo, and future brands with brand-specific styling
- **Quality-Aware Generation**: Only generate PDFs for high-confidence products (≥95%)
- **WooCommerce Integration**: Extend existing tools with specification sheet generation
- **Automated Workflow**: Generate specs automatically during pipeline processing

## 📋 Prerequisites

### Dependencies
```bash
# Add to pyproject.toml
poetry add reportlab pandas pillow
```

### Directory Structure
```
your-project/
├── src/
│   ├── services/
│   │   ├── reportlab_service.py          # New service
│   │   └── unified_reportlab_generator.py # Core generator
│   ├── pipeline/stages/
│   │   └── spec_sheet_generation.py      # New pipeline stage
│   └── cli.py                            # Extended CLI
├── generated_specs/                      # PDF output directory
├── vehicle_images/                       # Vehicle images (optional)
├── vehicles.db                          # ReportLab database
└── business.db                          # Your existing database
```

## 🔧 Core Components

### 1. Unified ReportLab Generator

The core generator supports multiple brands with configurable styling:

```python
from unified_reportlab_generator import UnifiedVehicleSpecGenerator, BrandConfigs

# Brand-specific generators
lynx_generator = UnifiedVehicleSpecGenerator(brand_config=BrandConfigs.LYNX)
skidoo_generator = UnifiedVehicleSpecGenerator(brand_config=BrandConfigs.SKIDOO)

# Generate specification sheet
spec_path = lynx_generator.generate_spec_sheet(
    vehicle_id=1, 
    output_path="lynx_rave_re_spec.pdf",
    image_path="images/rave_re.jpg"
)
```

### 2. Pipeline Integration Service

Bridges your pipeline output with PDF generation:

```python
from src.services.reportlab_service import SpecSheetGenerationService, SpecSheetConfig

# Configure service
config = SpecSheetConfig(
    output_directory=Path("generated_specs"),
    generate_for_brands=['lynx', 'ski-doo'],
    auto_generate_after_pipeline=True,
    quality_threshold=0.95
)

service = SpecSheetGenerationService(config)

# Generate from pipeline product
spec_path = await service.generate_spec_sheet_from_product(product)
```

### 3. Pipeline Stage Implementation

Add as Stage 6 in your existing pipeline:

```python
from src.pipeline.stages.spec_sheet_generation import SpecSheetPipelineStage

# Create stage
spec_stage = SpecSheetPipelineStage(
    config=pipeline_config,
    spec_sheet_service=spec_sheet_service
)

# Add to pipeline
pipeline_stages = [
    base_model_matching_stage,           # Stage 1
    specification_inheritance_stage,      # Stage 2
    customization_processing_stage,       # Stage 3
    spring_options_enhancement_stage,     # Stage 4
    final_validation_stage,              # Stage 5
    spec_stage                           # Stage 6 - NEW
]
```

## 🔄 Data Flow Integration

### Pipeline Product → ReportLab Database

The service automatically converts your pipeline `Product` objects to ReportLab database format:

```python
# Your pipeline produces Product objects
product = Product(
    sku="LTTA2024",
    model="Rave",
    moottori="600R E-TEC",
    specifications={
        'engine': {'name': '600R E-TEC', 'displacement_info': '600cc'},
        'platform': 'REV Gen4',
        'headlights': 'Premium LED'
    }
)

# Service converts and syncs to ReportLab database
vehicle_id = await service._sync_product_to_database(product, 'lynx')

# ReportLab generator creates PDF
spec_path = generator.generate_spec_sheet(vehicle_id)
```

### Brand Detection Logic

Automatic brand detection from SKU patterns:

```python
def _extract_brand_from_product(product: Product) -> Optional[str]:
    sku = product.sku.upper()
    
    # Lynx patterns
    if any(code in sku for code in ['LX', 'LTTA', 'LUTC', 'RAVE']):
        return 'lynx'
    
    # Ski-Doo patterns  
    if any(code in sku for code in ['MXZ', 'RENEGADE', 'SUMMIT']):
        return 'ski-doo'
    
    return None
```

## 🛠️ WooCommerce Integration

### Extend Existing Tools

Add specification generation to your existing WooCommerce functions:

```python
# Add to your ridebase-woocommerce tools
@register_function("generate_product_specifications")
async def generate_product_specifications(
    sku_list: List[str], 
    brand: Optional[str] = None,
    force_regenerate: bool = False
) -> Dict[str, str]:
    """Generate PDF specifications for WooCommerce products"""
    
    service = SpecSheetGenerationService(SpecSheetConfig())
    integration = WooCommerceSpecSheetIntegration(service)
    
    results = await integration.generate_specs_for_sku_list(sku_list)
    
    return {
        'generated_count': len(results),
        'specifications': results,
        'success': True
    }
```

### SKU-Based Generation

Generate specifications for existing products:

```python
# From your consolidated product data
sku_list = ['LTTA', 'MXZ123', 'RAVE_RE_600']

# Generate specifications
results = await generate_product_specifications(sku_list)

# Results contain file paths
for sku, spec_path in results['specifications'].items():
    print(f"Generated {sku}: {spec_path}")
```

## 🖥️ CLI Integration

### New Commands

Add specification commands to your existing CLI:

```bash
# Generate single specification
python -m src.cli specs generate LTTA --brand lynx --force

# Generate all specifications for brand
python -m src.cli specs generate-all --brand ski-doo --batch-size 10

# Check generation status
python -m src.cli specs status

# Regenerate all from price lists
python -m src.cli specs regenerate-from-pricelists
```

### CLI Implementation

```python
# Add to your existing CLI
@cli.group()
def specs():
    """Specification sheet generation commands"""
    pass

@specs.command()
@click.argument('sku')
@click.option('--brand', help='Vehicle brand (lynx, ski-doo)')
@click.option('--force', is_flag=True, help='Generate even if quality is low')
def generate(sku: str, brand: str, force: bool):
    """Generate specification sheet for single SKU"""
    config = SpecSheetConfig()
    service = SpecSheetGenerationService(config)
    
    # Implementation depends on your existing data access patterns
    click.echo(f"Generating specification sheet for {sku}...")
```

## ⚙️ Configuration

### SpecSheetConfig Options

```python
@dataclass
class SpecSheetConfig:
    # Output configuration
    output_directory: Path = Path("generated_specs")
    include_images: bool = True
    image_directory: Path = Path("vehicle_images")
    
    # Brand filtering
    generate_for_brands: List[str] = None  # ['lynx', 'ski-doo'] or None for all
    
    # Quality control
    quality_threshold: float = 0.95  # Only generate if processing confidence ≥ 95%
    auto_generate_after_pipeline: bool = True
```

### Brand Configuration

Add new brands easily:

```python
# Custom brand configuration
SEADOO = BrandConfig(
    name="Sea-Doo",
    primary_color="#0066CC",    # Sea-Doo blue
    secondary_color="#333333",
    accent_color="#F0F8FF",
    title_font_size=32,
    footer_disclaimer="Sea-Doo reserves the right to modify specifications."
)

# Use custom configuration
generator = UnifiedVehicleSpecGenerator(brand_config=SEADOO)
```

## 🚀 Implementation Steps

### Step 1: Install and Setup

```bash
# 1. Add dependencies
poetry add reportlab pandas pillow

# 2. Create directories
mkdir -p generated_specs vehicle_images

# 3. Add files to project
cp unified_reportlab_generator.py src/services/
cp reportlab_integration.py src/services/reportlab_service.py
```

### Step 2: Database Integration

```python
# Create ReportLab database schema
from src.services.unified_reportlab_generator import create_sample_database
create_sample_database()

# Or integrate with your existing database
DATABASE_MAPPING = {
    'business_db': 'business.db',
    'reportlab_db': 'vehicles.db'
}
```

### Step 3: Pipeline Integration

```python
# Add to your pipeline initialization
from src.services.reportlab_service import SpecSheetGenerationService, SpecSheetConfig
from src.pipeline.stages.spec_sheet_generation import SpecSheetPipelineStage

# Configure service
spec_config = SpecSheetConfig(
    output_directory=Path("generated_specs"),
    generate_for_brands=['lynx', 'ski-doo'],
    auto_generate_after_pipeline=True,
    quality_threshold=0.95
)

spec_service = SpecSheetGenerationService(spec_config)
spec_stage = SpecSheetPipelineStage(pipeline_config, spec_service)

# Add to pipeline stages
pipeline.add_stage(spec_stage)
```

### Step 4: Test Integration

```python
# Test with existing pipeline
async def test_integration():
    # Run your existing pipeline
    result = await pipeline.process_price_entries(price_entries)
    
    # Verify specification generation
    generated_specs = result.pipeline_results[-1]['generated_specifications']
    print(f"Generated {len(generated_specs)} specification sheets")
    
    # Manual generation test
    service = SpecSheetGenerationService(SpecSheetConfig())
    spec_path = await service.generate_spec_sheet_from_product(product)
    print(f"Manual generation: {spec_path}")
```

## 📊 Quality Control

### Confidence-Based Generation

```python
# Only generate for high-quality products
if product.processing_confidence >= 0.95:
    spec_path = await service.generate_spec_sheet_from_product(product)
else:
    logger.info(f"Skipping {product.sku} - confidence {product.processing_confidence:.2f} too low")
```

### Error Handling

```python
try:
    spec_path = generator.generate_spec_sheet(vehicle_id)
    logger.info(f"Generated specification: {spec_path}")
except Exception as e:
    logger.error(f"Specification generation failed: {e}")
    # Continue pipeline processing
```

## 🔍 Monitoring and Logging

### Generation Metrics

```python
# Track generation statistics
@dataclass
class GenerationMetrics:
    total_requested: int = 0
    successfully_generated: int = 0
    skipped_low_quality: int = 0
    failed_generation: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_requested == 0:
            return 0.0
        return self.successfully_generated / self.total_requested
```

### Log Integration

```python
# Add to your existing logging
logger = logging.getLogger('pipeline.specifications')

# Log generation events
logger.info(f"Generating specification for {product.sku} (confidence: {product.processing_confidence:.2f})")
logger.info(f"Generated specification: {spec_path}")
logger.warning(f"Skipped {product.sku} - quality below threshold")
logger.error(f"Generation failed for {product.sku}: {error}")
```

## 🔄 Maintenance and Updates

### Database Schema Updates

When adding new fields to your pipeline:

```python
# Add new fields to ReportLab database
cursor.execute("""
ALTER TABLE vehicles 
ADD COLUMN new_field TEXT
""")

# Update sync function
def _sync_product_to_database(self, product: Product, brand: str):
    # Add new field mapping
    specs = product.specifications
    new_field_value = specs.get('new_field', '')
    # ... rest of sync logic
```

### Brand Extension

Adding support for new brands:

```python
# 1. Create brand configuration
NEW_BRAND = BrandConfig(
    name="NewBrand",
    primary_color="#FF5500",
    secondary_color="#333333",
    accent_color="#F5F5F5"
)

# 2. Add to brand detection
def _extract_brand_from_product(self, product: Product) -> Optional[str]:
    sku = product.sku.upper()
    # ... existing patterns
    
    # New brand patterns
    if any(code in sku for code in ['NB', 'NEWB', 'BRAND']):
        return 'newbrand'
```

## 🎯 Best Practices

### Performance Optimization

```python
# Cache generators for better performance
self._generators: Dict[str, UnifiedVehicleSpecGenerator] = {}

# Batch processing for multiple products
async def generate_batch(self, products: List[Product]) -> List[str]:
    """Generate specifications for multiple products efficiently"""
    tasks = []
    for product in products:
        task = self.generate_spec_sheet_from_product(product)
        tasks.append(task)
    
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### Error Recovery

```python
# Graceful degradation
async def generate_with_fallback(self, product: Product) -> Optional[str]:
    """Generate with multiple fallback strategies"""
    
    # Try primary generation
    try:
        return await self.generate_spec_sheet_from_product(product)
    except DatabaseError:
        # Fallback: Generate without database sync
        return await self.generate_minimal_spec(product)
    except Exception as e:
        # Log error but don't fail pipeline
        self.logger.error(f"Specification generation failed: {e}")
        return None
```

### Testing Integration

```python
# Integration tests
async def test_pipeline_with_specs():
    """Test complete pipeline with specification generation"""
    
    # Setup test data
    price_entries = create_test_price_entries()
    
    # Run pipeline
    result = await pipeline.process_price_entries(price_entries)
    
    # Verify specifications generated
    assert result.success
    assert len(result.pipeline_results[-1]['generated_specifications']) > 0
    
    # Verify file creation
    spec_dir = Path("generated_specs")
    pdf_files = list(spec_dir.glob("*.pdf"))
    assert len(pdf_files) > 0
```

## 🚨 Troubleshooting

### Common Issues

**1. Database Sync Errors**
```python
# Check database connection
try:
    conn = sqlite3.connect(self.database_path)
    conn.execute("SELECT 1").fetchone()
except Exception as e:
    logger.error(f"Database connection failed: {e}")
```

**2. Missing Images**
```python
# Verify image directory exists
if not self.config.image_directory.exists():
    logger.warning(f"Image directory not found: {self.config.image_directory}")
    self.config.include_images = False
```

**3. PDF Generation Failures**
```python
# Debug ReportLab issues
try:
    generator.generate_spec_sheet(vehicle_id)
except Exception as e:
    logger.error(f"ReportLab error: {e}")
    logger.debug(f"Vehicle data: {vehicle_data}")
```

### Health Checks

```python
def health_check(self) -> Dict[str, bool]:
    """Check integration health"""
    return {
        'output_directory_writable': self._check_output_directory(),
        'database_accessible': self._check_database_connection(),
        'image_directory_exists': self._check_image_directory(),
        'generators_initialized': len(self._generators) > 0
    }
```

## 📈 Future Enhancements

### Planned Features

1. **Multi-Language Support**: Generate specifications in multiple languages
2. **Custom Templates**: Brand-specific template customization
3. **Batch Processing**: Efficient bulk generation with progress tracking
4. **Cloud Storage**: Direct upload to S3/Azure for web access
5. **Email Integration**: Automatic spec sheet delivery

### Extensibility Points

```python
# Custom specification formatters
class CustomSpecFormatter(BaseSpecFormatter):
    """Brand-specific specification formatting"""
    
    def format_engine_specs(self, engine_data: Dict) -> List[str]:
        # Custom formatting logic
        pass

# Template system integration
class TemplateManager:
    """Manage specification templates"""
    
    def load_template(self, brand: str, template_type: str) -> Template:
        # Load brand-specific templates
        pass
```

This integration maintains your existing architecture while adding professional PDF generation as a natural extension of your product processing pipeline. The ReportLab generator becomes another output format alongside your WooCommerce exports and HTML specifications.