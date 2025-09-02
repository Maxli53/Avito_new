# HTML Generation Methodology
** From
Database
to
Final
Customer - Facing
Documentation **

## 🎯 Overview

This
methodology
documents
the
complete
workflow
for generating customer - facing HTML specification sheets from our PostgreSQL database after products have been processed through the 5-stage inheritance pipeline.

## 🏗️ Architecture Flow

```
Database(PostgreSQL) → Data
Extraction → Template
Engine → HTML
Generation → Quality
Validation → Final
Output
```

### Complete Data Journey
```
Price
List
PDF → 5 - Stage
Pipeline → Database
Storage → HTML
Templates → Customer
Documentation
```

## 📊 Data Extraction Strategy

### 1. Product Data Retrieval

#### Primary Query Pattern
```python


async def get_product_for_html_generation(sku: str) -> ProductHTMLData:
    """Retrieve complete product data for HTML generation"""

    query = """
            SELECT p.sku, \
                   p.brand, \
                   p.model_year, \
                   p.model_family, \
                   p.platform, \
                   p.category, \
                   p.engine_model, \
                   p.engine_displacement_cc, \
                   p.track_length_mm, \
                   p.track_width_mm, \
                   p.track_profile_mm, \
                   p.dry_weight_kg, \
                   p.full_specifications, \
                   p.marketing_texts, \
                   p.spring_modifications, \
                   p.confidence_score, \
                   p.validation_status, \

                   -- Get inheritance audit trail \
                   p.inheritance_audit_trail, \

                   -- Get model mapping details \
                   mm.processing_method, \
                   mm.base_model_matched, \
                   mm.stage_1_result, \
                   mm.stage_2_result, \
                   mm.stage_3_result, \
                   mm.stage_4_result, \
                   mm.stage_5_result, \
                   mm.auto_accepted, \

                   -- Get original price entry \
                   pe.price_amount, \
                   pe.currency, \
                   pe.market, \
                   pe.kevätoptiot, \
                   pe.vari, \

                   -- Get base model catalog data \
                   bmc.platform_specs, \
                   bmc.engine_options, \
                   bmc.track_options, \
                   bmc.suspension_specs, \
                   bmc.feature_options, \
                   bmc.color_options, \
                   bmc.dimensions, \
                   bmc.weight_specifications, \
                   bmc.standard_features

            FROM products p
                     LEFT JOIN model_mappings mm ON p.sku = mm.catalog_sku
                     LEFT JOIN price_entries pe ON pe.mapped_product_sku = p.sku
                     LEFT JOIN base_models_catalog bmc ON mm.base_model_id = bmc.id
            WHERE p.sku = %s
              AND p.deleted_at IS NULL
              AND p.validation_status = 'passed'
              AND p.confidence_score >= 0.95 \
            """

    return await execute_query(query, [sku])


```

### 2. Specification Data Processing

#### JSONB Data Extraction
```python


class SpecificationProcessor:
    """Process JSONB specifications for HTML display"""

    def extract_engine_specifications(self, full_specs: Dict) -> EngineSpecs:
        """Extract and format engine specifications"""
        engine_data = full_specs.get('engine', {})

        return EngineSpecs(
            model=engine_data.get('name'),
            displacement=engine_data.get('displacement_info'),
            type=engine_data.get('engine_type'),
            cylinders=engine_data.get('cylinders'),
            stroke=engine_data.get('stroke'),
            bore=engine_data.get('bore'),
            max_rpm=engine_data.get('maximum_engine_speed'),
            carburation=engine_data.get('carburation'),
            fuel_type=engine_data.get('fuel_type_octane'),
            oil_capacity=engine_data.get('oil_capacity')
        )

    def extract_track_specifications(self, full_specs: Dict) -> TrackSpecs:
        """Extract and format track specifications"""
        track_data = full_specs.get('track', {})

        return TrackSpecs(
            length=track_data.get('length'),
            width=track_data.get('width'),
            profile=track_data.get('profile'),
            type=track_data.get('track_type'),
            pattern=track_data.get('track_pattern'),
            manufacturer=track_data.get('manufacturer')
        )

    def extract_suspension_specifications(self, full_specs: Dict) -> SuspensionSpecs:
        """Extract and format suspension specifications"""
        suspension_data = full_specs.get('suspension', {})

        return SuspensionSpecs(
            front_type=suspension_data.get('front_suspension'),
            front_shock=suspension_data.get('front_shock'),
            rear_type=suspension_data.get('rear_suspension'),
            center_shock=suspension_data.get('center_shock'),
            rear_shock=suspension_data.get('rear_shock')
        )


```

### 3. Spring Modifications Processing

#### Spring Options Enhancement Data
```python


def process_spring_modifications(spring_mods: Dict, kevätoptiot: str) -> SpringEnhancements:
    """Process spring modifications for HTML display"""

    enhancements = SpringEnhancements()

    # Extract applied modifications from pipeline stage 4
    if 'applied_modifications' in spring_mods:
        mods = spring_mods['applied_modifications']

        # Color modifications
        if 'color_changes' in mods:
            enhancements.color_options = mods['color_changes']

        # Track modifications  
        if 'track_upgrades' in mods:
            enhancements.track_upgrades = mods['track_upgrades']

        # Feature additions
        if 'feature_additions' in mods:
            enhancements.feature_additions = mods['feature_additions']

        # Suspension modifications
        if 'suspension_upgrades' in mods:
            enhancements.suspension_upgrades = mods['suspension_upgrades']

    # Original spring options text for reference
    enhancements.original_text = kevätoptiot

    return enhancements


```

## 🎨 HTML Template System

### 1. Template Architecture

#### Multi-Brand Template Structure
```
templates /
├── base /
│   ├── layout.html  # Base layout template
│   ├── components /
│   │   ├── header.html  # Brand-specific headers
│   │   ├── specifications.html  # Spec table templates
│   │   ├── pipeline_status.html  # Processing status display
│   │   └── footer.html  # Brand-specific footers
├── brands /
│   ├── lynx /
│   │   ├── product_page.html  # Lynx-specific styling
│   │   └── styles.css  # Lynx brand colors/fonts
│   ├── ski - doo /
│   │   ├── product_page.html  # Ski-Doo-specific styling
│   │   └── styles.css  # Ski-Doo brand colors/fonts
│   └── sea - doo /
│       ├── product_page.html  # Sea-Doo-specific styling
│       └── styles.css  # Sea-Doo brand colors/fonts
└── static /
├── css /
│   └── common.css  # Shared styles
├── js /
│   └── interactive.js  # Interactive features
└── images /
└── brand_logos /  # Brand logo assets
```

### 2. Template Engine Configuration

#### Jinja2 Template Service
```python
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path


class HTMLTemplateService:
    """Professional HTML template rendering service"""

    def __init__(self, template_dir: Path):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Register custom filters
        self.env.filters['format_price'] = self._format_price
        self.env.filters['format_measurement'] = self._format_measurement
        self.env.filters['brand_color'] = self._get_brand_color
        self.env.filters['confidence_badge'] = self._format_confidence_badge

    def render_product_specification(self,
                                     product_data: ProductHTMLData,
                                     template_name: str = None) -> str:
        """Render complete product specification HTML"""

        # Auto-detect template based on brand
        if not template_name:
            template_name = f"brands/{product_data.brand.lower()}/product_page.html"

        template = self.env.get_template(template_name)

        return template.render(
            product=product_data,
            generation_timestamp=datetime.now(),
            pipeline_version="2.0",
            system_name="Snowmobile Product Reconciliation System"
        )

    def _format_price(self, amount: Decimal, currency: str) -> str:
        """Format price with proper currency symbol and formatting"""
        currency_symbols = {'EUR': '€', 'SEK': 'kr', 'NOK': 'kr', 'DKK': 'kr'}
        symbol = currency_symbols.get(currency, currency)

        if currency == 'EUR':
            return f"{amount:,.0f} {symbol}"
        else:
            return f"{symbol} {amount:,.0f}"

    def _format_measurement(self, value: int, unit: str, imperial: bool = False) -> str:
        """Format measurements with unit conversion"""
        if unit == 'mm' and imperial:
            inches = value / 25.4
            return f"{value}mm ({inches:.1f}in)"
        elif unit == 'kg' and imperial:
            pounds = value * 2.20462
            return f"{value}kg ({pounds:.0f}lbs)"
        else:
            return f"{value}{unit}"


```

### 3. Brand-Specific Template Logic

#### Dynamic Brand Styling
```python


class BrandTemplateConfig:
    """Brand-specific template configurations"""

    LYNX = {
        'primary_color': '#C41E3A',  # Lynx Red
        'secondary_color': '#2C2C2C',  # Dark Gray
        'accent_color': '#FFD700',  # Gold
        'font_family': 'Arial, sans-serif',
        'logo_path': 'images/brand_logos/lynx_logo.png',
        'header_style': 'bold_red',
        'spec_table_style': 'lynx_premium'
    }

    SKI_DOO = {
        'primary_color': '#FFD700',  # Ski-Doo Yellow
        'secondary_color': '#000000',  # Black
        'accent_color': '#FF6600',  # Orange
        'font_family': 'Helvetica, Arial, sans-serif',
        'logo_path': 'images/brand_logos/skidoo_logo.png',
        'header_style': 'bold_yellow',
        'spec_table_style': 'skidoo_sport'
    }

    SEA_DOO = {
        'primary_color': '#0066CC',  # Sea-Doo Blue
        'secondary_color': '#003366',  # Dark Blue
        'accent_color': '#FF9900',  # Orange
        'font_family': 'Verdana, sans-serif',
        'logo_path': 'images/brand_logos/seadoo_logo.png',
        'header_style': 'bold_blue',
        'spec_table_style': 'seadoo_marine'
    }


```

## 📝 HTML Generation Pipeline

### Stage 6: HTML Specification Generation

#### Complete HTML Generation Process
```python
from typing import Dict, List, Optional
from pathlib import Path
from src.models.domain import Product, ProductHTMLData
from src.services.html_template_service import HTMLTemplateService


class HTMLGenerationPipeline:
    """Stage 6: Generate customer-facing HTML specifications"""

    def __init__(self, template_service: HTMLTemplateService, output_dir: Path):
        self.template_service = template_service
        self.output_dir = output_dir
        self.quality_threshold = 0.95

    async def generate_html_specification(self,
                                          product_sku: str,
                                          template_override: str = None) -> HTMLGenerationResult:
        """Generate complete HTML specification for a product"""

        try:
            # 1. Extract complete product data from database
            product_data = await self._extract_product_data(product_sku)

            # 2. Validate product quality
            if not self._validate_product_quality(product_data):
                return HTMLGenerationResult(
                    success=False,
                    error=f"Product {product_sku} does not meet quality threshold"
                )

            # 3. Process specifications for HTML display
            html_data = await self._process_specifications_for_html(product_data)

            # 4. Generate HTML using brand-specific template
            html_content = self.template_service.render_product_specification(
                html_data, template_override
            )

            # 5. Apply post-processing optimizations
            optimized_html = await self._optimize_html_output(html_content, html_data)

            # 6. Save to output directory with proper naming
            output_path = await self._save_html_file(optimized_html, html_data)

            # 7. Generate accompanying assets (CSS, images, etc.)
            assets = await self._generate_accompanying_assets(html_data, output_path)

            return HTMLGenerationResult(
                success=True,
                output_path=output_path,
                assets=assets,
                generation_metadata=self._create_generation_metadata(html_data)
            )

        except Exception as e:
            logger.error(f"HTML generation failed for {product_sku}: {e}")
            return HTMLGenerationResult(success=False, error=str(e))

    async def _extract_product_data(self, sku: str) -> ProductHTMLData:
        """Extract complete product data from all related tables"""

        # Main product query with all joins
        query = """
                SELECT p.*, \
                       mm.processing_method, \
                       mm.confidence_score as mapping_confidence, \
                       mm.stage_4_result   as spring_stage_result, \
                       mm.complete_audit_trail, \
                       pe.price_amount, \
                       pe.currency, \
                       pe.market, \
                       pe.kevätoptiot, \
                       pe.vari             as original_color, \
                       bmc.platform_specs, \
                       bmc.engine_options, \
                       bmc.track_options, \
                       bmc.standard_features
                FROM products p
                         LEFT JOIN model_mappings mm ON p.sku = mm.catalog_sku
                         LEFT JOIN price_entries pe ON pe.mapped_product_sku = p.sku
                         LEFT JOIN base_models_catalog bmc ON mm.base_model_id = bmc.id
                WHERE p.sku = %s \
                  AND p.deleted_at IS NULL \
                """

        result = await self._execute_query(query, [sku])
        return ProductHTMLData.from_database_row(result[0])

    async def _process_specifications_for_html(self,
                                               product_data: ProductHTMLData) -> ProcessedHTMLData:
        """Process raw specifications into HTML-ready format"""

        processor = SpecificationProcessor()

        # Extract core specifications
        engine_specs = processor.extract_engine_specifications(product_data.full_specifications)
        track_specs = processor.extract_track_specifications(product_data.full_specifications)
        suspension_specs = processor.extract_suspension_specifications(product_data.full_specifications)
        feature_specs = processor.extract_feature_specifications(product_data.full_specifications)

        # Process spring modifications
        spring_enhancements = processor.process_spring_modifications(
            product_data.spring_modifications,
            product_data.kevätoptiot
        )

        # Generate pipeline status for HTML
        pipeline_status = self._generate_pipeline_status_data(product_data)

        # Format pricing information
        pricing_info = self._format_pricing_information(product_data)

        return ProcessedHTMLData(
            basic_info=BasicProductInfo.from_product_data(product_data),
            engine_specifications=engine_specs,
            track_specifications=track_specs,
            suspension_specifications=suspension_specs,
            feature_specifications=feature_specs,
            spring_enhancements=spring_enhancements,
            pipeline_status=pipeline_status,
            pricing_information=pricing_info,
            quality_metrics=self._generate_quality_metrics(product_data)
        )


```

### HTML Template Structure

#### Base Template (layout.html)
```html
< !DOCTYPE
html >
< html
lang = "en" >
< head >
< meta
charset = "UTF-8" >
< meta
name = "viewport"
content = "width=device-width, initial-scale=1.0" >
< title > {{product.model_family}}
{{product.model_year}} - {{product.brand}} < / title >
< link
rel = "stylesheet"
href = "static/css/common.css" >
< link
rel = "stylesheet"
href = "static/css/brands/{{ product.brand.lower() }}.css" >
< / head >
< body


class ="brand-{{ product.brand.lower() }}" >


{ % include
'components/header.html' %}

< main


class ="specification-container" >


{ % block
content %}{ % endblock %}
< / main >

{ % include
'components/footer.html' %}
< script
src = "static/js/interactive.js" > < / script >
< / body >
< / html >
```

#### Product Specification Template
```html
{ % extends
"base/layout.html" %}

{ % block
content %}
< div


class ="product-specification" >

< !-- Product
Header -->
< header


class ="product-header" >

< div


class ="product-title" >

< h1 > {{product.brand}}
{{product.model_family}} < / h1 >
< h2 > {{product.model_year}}
Model
Year < / h2 >
< div


class ="sku-badge" > SKU: {{product.sku}} <

/ div >
< / div >

{ % if product.product_image %}
< div


class ="product-image" >

< img
src = "{{ product.product_image }}"
alt = "{{ product.model_family }}" / >
< / div >
{ % endif %}
< / header >

< !-- Key
Highlights -->
< section


class ="key-highlights" >

< h3 > Key
Specifications < / h3 >
< div


class ="highlights-grid" >

< div


class ="highlight-item" >

< span


class ="label" > Engine < / span >

< span


class ="value" > {{specifications.engine.model}} < / span >

< / div >
< div


class ="highlight-item" >

< span


class ="label" > Track < / span >

< span


class ="value" > {{specifications.track.length}}mm / {{specifications.track.width}}mm < / span >

< / div >
< div


class ="highlight-item" >

< span


class ="label" > Weight < / span >

< span


class ="value" > {{product.dry_weight_kg | format_measurement('kg', true)}} < / span >

< / div >
< div


class ="highlight-item" >

< span


class ="label" > Price < / span >

< span


class ="value" > {{pricing.amount | format_price(pricing.currency)}} < / span >

< / div >
< / div >
< / section >

< !-- Detailed
Specifications -->
< section


class ="detailed-specifications" >

< h3 > Complete
Specifications < / h3 >

< !-- Engine
Specifications -->
< div


class ="spec-category" >

< h4 >🔧 Engine
Specifications < / h4 >
< table


class ="spec-table" >

< tr > < td > Engine
Model < / td > < td > {{specifications.engine.model}} < / td > < / tr >
< tr > < td > Displacement < / td > < td > {{specifications.engine.displacement}} < / td > < / tr >
< tr > < td > Cylinders < / td > < td > {{specifications.engine.cylinders}} < / td > < / tr >
< tr > < td > Max
RPM < / td > < td > {{specifications.engine.max_rpm}} < / td > < / tr >
< tr > < td > Fuel
Type < / td > < td > {{specifications.engine.fuel_type}} < / td > < / tr >
< tr > < td > Oil
Capacity < / td > < td > {{specifications.engine.oil_capacity}} < / td > < / tr >
< / table >
< / div >

< !-- Track
Specifications -->
< div


class ="spec-category" >

< h4 >🛤️
Track
Specifications < / h4 >
< table


class ="spec-table" >

< tr > < td > Track
Length < / td > < td > {{specifications.track.length | format_measurement('mm', true)}} < / td > < / tr >
< tr > < td > Track
Width < / td > < td > {{specifications.track.width | format_measurement('mm', true)}} < / td > < / tr >
< tr > < td > Track
Profile < / td > < td > {{specifications.track.profile}}
mm < / td > < / tr >
< tr > < td > Track
Type < / td > < td > {{specifications.track.type}} < / td > < / tr >
< tr > < td > Track
Pattern < / td > < td > {{specifications.track.pattern}} < / td > < / tr >
< / table >
< / div >

< !-- Suspension
Specifications -->
< div


class ="spec-category" >

< h4 >🏔️
Suspension
Specifications < / h4 >
< table


class ="spec-table" >

< tr > < td > Front
Suspension < / td > < td > {{specifications.suspension.front_type}} < / td > < / tr >
< tr > < td > Front
Shock < / td > < td > {{specifications.suspension.front_shock}} < / td > < / tr >
< tr > < td > Rear
Suspension < / td > < td > {{specifications.suspension.rear_type}} < / td > < / tr >
< tr > < td > Center
Shock < / td > < td > {{specifications.suspension.center_shock}} < / td > < / tr >
< tr > < td > Rear
Shock < / td > < td > {{specifications.suspension.rear_shock}} < / td > < / tr >
< / table >
< / div >

< !-- Spring
Options
Enhancement -->
{ % if spring_enhancements.has_modifications %}
< div


class ="spec-category spring-options" >

< h4 >🌸 Spring
Options & Enhancements < / h4 >
< div


class ="spring-modifications" >


{ % if spring_enhancements.color_options %}
< div


class ="modification-item" >

< strong > Color
Enhancement: < / strong > {{spring_enhancements.color_options | join(', ')}}
< / div >
{ % endif %}

{ % if spring_enhancements.track_upgrades %}
< div


class ="modification-item" >

< strong > Track
Upgrades: < / strong > {{spring_enhancements.track_upgrades | join(', ')}}
< / div >
{ % endif %}

{ % if spring_enhancements.feature_additions %}
< div


class ="modification-item" >

< strong > Added
Features: < / strong > {{spring_enhancements.feature_additions | join(', ')}}
< / div >
{ % endif %}
< / div >

< div


class ="original-spring-text" >

< em > Original
Spring
Options: < / em > {{spring_enhancements.original_text}}
< / div >
< / div >
{ % endif %}
< / section >

< !-- Pipeline
Processing
Status -->
< section


class ="pipeline-status" >

< h3 >🔧 Processing
Quality & Validation < / h3 >
< div


class ="status-grid" >


{ %
for stage in pipeline_status.stages %}
< div


class ="status-item {{ 'completed' if stage.completed else 'failed' }}" >

< span


class ="status-check" > {{'✅' if stage.completed else '❌'}} < / span >

< span


class ="stage-name" > {{stage.name}} < / span >


{ % if stage.confidence_score %}
< span


class ="confidence-score" > {{stage.confidence_score | confidence_badge}} < / span >


{ % endif %}
< / div >
{ % endfor %}
< / div >

< div


class ="overall-quality" >

< div


class ="quality-score" >

< span


class ="label" > Overall Confidence:<

    / span >
< span


class ="score {{ 'high' if product.confidence_score >= 0.95 else 'medium' }}" >


{{(product.confidence_score * 100) | round(1)}} %
< / span >
< / div >
< div


class ="processing-method" >

< span


class ="label" > Processing Method:<

    / span >
< span


class ="method" > {{pipeline_status.processing_method | title}} < / span >

< / div >
< / div >
< / section >

< !-- Source
Attribution -->
< section


class ="source-attribution" >

< h3 >📚 Data
Sources & Validation < / h3 >
< div


class ="source-list" >

< div


class ="source-item" >

< strong > Base
Model
Source: < / strong > {{product.base_model_source}}
< / div >
< div


class ="source-item" >

< strong > Price
List
Source: < / strong > {{pricing.source_file}}
< / div >
< div


class ="source-item" >

< strong > Processing
Date: < / strong > {{product.created_at | format_datetime}}
< / div >
< div


class ="source-item" >

< strong > Validation
Status: < / strong >
< span


class ="validation-{{ product.validation_status }}" > {{product.validation_status | title}} < / span >

< / div >
< / div >
< / section >
< / div >
{ % endblock %}
```

## 🔄 Complete Workflow Implementation

### 1. Batch HTML Generation

#### Process Multiple Products
```python


class BatchHTMLGenerator:
    """Generate HTML specifications for multiple products"""

    async def generate_batch_html(self,
                                  sku_list: List[str],
                                  output_format: str = "individual") -> BatchGenerationResult:
        """Generate HTML for multiple products"""

        results = []

        for sku in sku_list:
            try:
                # Generate individual HTML
                result = await self.html_pipeline.generate_html_specification(sku)
                results.append(result)

                # Update generation tracking
                await self._update_generation_tracking(sku, result)

            except Exception as e:
                logger.error(f"Failed to generate HTML for {sku}: {e}")
                results.append(HTMLGenerationResult(success=False, sku=sku, error=str(e)))

        # Generate batch summary if requested
        if output_format == "catalog":
            catalog_html = await self._generate_catalog_page(results)
            return BatchGenerationResult(
                individual_results=results,
                catalog_page=catalog_html,
                success_count=len([r for r in results if r.success])
            )

        return BatchGenerationResult(individual_results=results)


```

### 2. Quality-Based Generation

#### Only Generate High-Quality HTML
```python


def _validate_product_quality(self, product_data: ProductHTMLData) -> bool:
    """Validate product meets quality standards for HTML generation"""

    quality_checks = [
        # Minimum confidence score
        product_data.confidence_score >= self.quality_threshold,

        # Validation must have passed
        product_data.validation_status == 'passed',

        # Must have essential specifications
        bool(product_data.engine_model),
        bool(product_data.track_length_mm),
        bool(product_data.dry_weight_kg),

        # Must have completed all pipeline stages
        product_data.stage_5_completed == True,

        # Spring modifications must be processed if present
        not product_data.kevätoptiot or bool(product_data.spring_modifications)
    ]

    return all(quality_checks)


```

### 3. Multi-Language Support

#### Localized HTML Generation
```python


class LocalizedHTMLGenerator:
    """Generate HTML in multiple languages"""

    LANGUAGE_CONFIGS = {
        'fi': {'name': 'Finnish', 'currency': 'EUR', 'market': 'FI'},
        'se': {'name': 'Swedish', 'currency': 'SEK', 'market': 'SE'},
        'no': {'name': 'Norwegian', 'currency': 'NOK', 'market': 'NO'},
        'dk': {'name': 'Danish', 'currency': 'DKK', 'market': 'DK'},
        'en': {'name': 'English', 'currency': 'EUR', 'market': 'International'}
    }

    async def generate_multilingual_html(self,
                                         sku: str,
                                         languages: List[str] = None) -> Dict[str, HTMLGenerationResult]:
        """Generate HTML in multiple languages"""

        if not languages:
            languages = ['fi', 'en']  # Default languages

        results = {}

        for lang in languages:
            try:
                # Get localized product data
                localized_data = await self._get_localized_product_data(sku, lang)

                # Generate HTML with language-specific template
                template_name = f"brands/{localized_data.brand.lower()}/product_page_{lang}.html"
                html_result = await self.html_pipeline.generate_html_specification(
                    sku, template_override=template_name
                )

                results[lang] = html_result

            except Exception as e:
                logger.error(f"Failed to generate {lang} HTML for {sku}: {e}")
                results[lang] = HTMLGenerationResult(success=False, error=str(e))

        return results


```

## 📁 Output Organization

### File Structure Strategy

#### Generated HTML Organization
```
generated_html /
├── products /
│   ├── lynx /
│   │   ├── 2026 /
│   │   │   ├── LTTA /
│   │   │   │   ├── specification.html
│   │   │   │   ├── specification_fi.html
│   │   │   │   ├── specification_en.html
│   │   │   │   └── assets /
│   │   │   │       ├── product_image.jpg
│   │   │   │       └── styling.css
│   │   │   └── LUTC /
│   │   │       └── ...
│   │   └── 2025 /
│   │       └── ...
│   ├── ski - doo /
│   │   ├── 2026 /
│   │   └── 2025 /
│   └── sea - doo /
│       └── ...
├── catalogs /
│   ├── lynx_2026_catalog.html
│   ├── skidoo_2026_catalog.html
│   └── brand_comparison.html
├── static /
│   ├── css /
│   │   ├── common.css
│   │   └── brands /
│   │       ├── lynx.css
│   │       ├── ski - doo.css
│   │       └── sea - doo.css
│   ├── js /
│   │   ├── interactive.js
│   │   └── specification_viewer.js
│   └── images /
│       ├── brand_logos /
│       └── product_images /
└── index.html  # Main catalog entry point
```

## 🎯 Integration with Existing Tools

### WooCommerce Tool Extension

#### Add HTML Generation to Existing Functions
```python


# Extend existing ridebase-woocommerce tools
@register_woocommerce_function
async def generate_product_html_specifications(
        sku_list: List[str],
        languages: List[str] = None,
        template_override: str = None,
        quality_threshold: float = 0.95
) -> Dict[str, Any]:
    """Generate HTML specifications for WooCommerce products"""

    html_generator = HTMLGenerationPipeline(
        template_service=HTMLTemplateService(Path("templates")),
        output_dir=Path("generated_html/products")
    )

    results = {}

    for sku in sku_list:
        try:
            # Check if product exists and meets quality threshold
            product_quality = await check_product_quality(sku, quality_threshold)
            if not product_quality.meets_threshold:
                results[sku] = {
                    'success': False,
                    'error': f'Quality score {product_quality.score:.2f} below threshold {quality_threshold}'
                }
                continue

            # Generate HTML specification
            if languages:
                # Multi-language generation
                lang_generator = LocalizedHTMLGenerator(html_generator)
                lang_results = await lang_generator.generate_multilingual_html(sku, languages)
                results[sku] = {
                    'success': True,
                    'languages': lang_results,
                    'primary_url': lang_results.get('fi', lang_results.get('en')).output_path
                }
            else:
                # Single language generation
                result = await html_generator.generate_html_specification(sku, template_override)
                results[sku] = {
                    'success': result.success,
                    'url': result.output_path if result.success else None,
                    'error': result.error if not result.success else None
                }

        except Exception as e:
            logger.error(f"HTML generation failed for {sku}: {e}")
            results[sku] = {'success': False, 'error': str(e)}

    return {
        'total_requested': len(sku_list),
        'successful': len([r for r in results.values() if r.get('success')]),
        'failed': len([r for r in results.values() if not r.get('success')]),
        'results': results
    }


```

### CLI Integration

#### Command Line Interface
```bash
# Generate single product HTML
python - m
src.cli
html
generate
LTTA - -language
fi, en - -template
premium

# Generate batch HTML for all Lynx products
python - m
src.cli
html
generate - brand
lynx - -year
2026 - -quality - threshold
0.95

# Generate complete catalog HTML
python - m
src.cli
html
generate - catalog - -brands
lynx, ski - doo - -include - comparisons

# Validate HTML quality
python - m
src.cli
html
validate - -output - dir
generated_html / products

# Regenerate HTML for updated products
python - m
src.cli
html
regenerate - -updated - since
"2024-01-01" - -force
```

## 🔍 Quality Assurance & Validation

### HTML Quality Validation

#### Automated HTML Validation
```python


class HTMLQualityValidator:
    """Validate generated HTML quality and completeness"""

    async def validate_html_output(self, html_path: Path, product_sku: str) -> HTMLValidationResult:
        """Comprehensive HTML validation"""

        validation_results = []

        # 1. HTML Structure Validation
        structure_result = await self._validate_html_structure(html_path)
        validation_results.append(structure_result)

        # 2. Content Completeness Validation
        completeness_result = await self._validate_content_completeness(html_path, product_sku)
        validation_results.append(completeness_result)

        # 3. Brand Compliance Validation
        brand_result = await self._validate_brand_compliance(html_path, product_sku)
        validation_results.append(brand_result)

        # 4. Accessibility Validation
        accessibility_result = await self._validate_accessibility(html_path)
        validation_results.append(accessibility_result)

        # 5. Performance Validation
        performance_result = await self._validate_performance(html_path)
        validation_results.append(performance_result)

        return HTMLValidationResult(
            overall_score=self._calculate_overall_score(validation_results),
            validation_details=validation_results,
            recommendations=self._generate_recommendations(validation_results)
        )


```

### Content Accuracy Verification

#### Cross-Reference with Database
```python


async def verify_html_accuracy(self, html_path: Path, product_sku: str) -> AccuracyReport:
    """Verify HTML content matches database specifications"""

    # Parse HTML content
    html_data = await self._parse_html_content(html_path)

    # Get database data
    db_data = await self._get_database_specifications(product_sku)

    # Compare key specifications
    accuracy_checks = {
        'engine_model': html_data.engine_model == db_data.engine_model,
        'track_length': html_data.track_length == db_data.track_length_mm,
        'price_amount': html_data.price_amount == db_data.price_amount,
        'spring_options': self._compare_spring_options(html_data.spring_options, db_data.kevätoptiot)
    }

    return AccuracyReport(
        accuracy_score=sum(accuracy_checks.values()) / len(accuracy_checks),
        failed_checks=[k for k, v in accuracy_checks.items() if not v],
        verification_timestamp=datetime.now()
    )


```

## 🚀 Deployment & Production

### Production HTML Generation Pipeline

#### Complete Production Workflow
```python


class ProductionHTMLWorkflow:
    """Production-ready HTML generation workflow"""

    async def process_updated_products(self) -> WorkflowResult:
        """Generate HTML for all updated products since last run"""

        # 1. Identify products needing HTML generation
        updated_products = await self._get_updated_products_since_last_run()

        # 2. Filter by quality threshold
        quality_products = [p for p in updated_products if p.confidence_score >= 0.95]

        # 3. Generate HTML specifications
        html_results = await self.batch_generator.generate_batch_html(
            [p.sku for p in quality_products]
        )

        # 4. Validate generated HTML
        validation_results = []
        for result in html_results.individual_results:
            if result.success:
                validation = await self.validator.validate_html_output(
                    result.output_path, result.sku
                )
                validation_results.append(validation)

        # 5. Update WooCommerce if configured
        if self.config.auto_update_woocommerce:
            await self._update_woocommerce_specifications(html_results)

        # 6. Generate performance report
        performance_report = self._generate_performance_report(
            html_results, validation_results
        )

        return WorkflowResult(
            html_results=html_results,
            validation_results=validation_results,
            performance_report=performance_report
        )


```

### Monitoring & Analytics

#### HTML Generation Metrics
```python


class HTMLGenerationMetrics:
    """Track HTML generation performance and quality"""

    async def record_generation_metrics(self,
                                        generation_result: HTMLGenerationResult,
                                        processing_time_ms: int) -> None:
        """Record metrics in quality_metrics table"""

        metrics_to_record = [
            ('html_generation_success_rate', 1.0 if generation_result.success else 0.0),
            ('html_generation_time_ms', processing_time_ms),
            ('html_file_size_kb', generation_result.file_size_kb if generation_result.success else 0),
            ('html_validation_score', generation_result.validation_score if generation_result.success else 0)
        ]

        for metric_name, value in metrics_to_record:
            await self._insert_quality_metric(
                metric_type='html_generation',
                metric_name=metric_name,
                measured_value=value,
                measurement_date=date.today(),
                sample_size=1
            )


```

## 🎯 Summary: Database to HTML Methodology

### Complete Process Flow

1. ** Data
Extraction **: Query
PostgreSQL
for complete product data including all pipeline results
2. ** Quality
Validation **: Ensure
product
meets
confidence and validation
thresholds
3. ** Specification
Processing **: Transform
JSONB
data
into
HTML - ready
structures
4. ** Template
Rendering **: Apply
brand - specific
Jinja2
templates
with proper styling
5. ** Asset
Generation **: Create
accompanying
CSS, images, and interactive
features
6. ** Quality
Assurance **: Validate
HTML
structure, content
accuracy, and accessibility
7. ** File
Organization **: Save
to
structured
directory
with proper naming conventions
8. ** Integration **: Update
WooCommerce and other
systems
with generated HTML links
9. ** Monitoring **: Track
generation
metrics and performance in quality_metrics
table

### Key Success Factors

- ** Quality
First **: Only
generate
HTML
for products with ≥95 %confidence
- ** Brand
Consistency **: Use
brand - specific
templates and styling
- ** Complete
Traceability **: Include
full
pipeline
status and source
attribution
- ** Performance
Optimization **: Efficient
batch
processing and caching
- ** Validation **: Automated
quality
checks and accuracy
verification
- ** Scalability **: Support
for multi - language and multi-brand generation

This
methodology
ensures
that
our
database - driven
HTML
generation
maintains
the
same
high
quality
standards as our
inheritance
pipeline
while producing professional, customer-ready specification documents.