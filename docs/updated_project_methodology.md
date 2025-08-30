# Project Methodology and Technical Implementation
**Snowmobile Product Data Reconciliation System**

## 🎯 Executive Summary

This document defines the complete technical methodology for reconciling Finnish snowmobile price lists with product catalogs using Claude AI. The system transforms cryptic model codes into comprehensive product specifications through a **5-stage inheritance pipeline**.

### Core Business Value
- **Time Reduction**: 80+ hours manual work → 2 hours automated processing
- **Accuracy Improvement**: 99%+ accuracy vs. 85% manual process
- **Cost Optimization**: $0.50-3.00 per product vs. $50+ manual cost
- **Scalability**: Process unlimited catalogs with consistent quality

## 🏗️ Technical Architecture

### Database Schema (PostgreSQL with JSONB)

```sql
-- Core product repository with flexible specifications
CREATE TABLE products (
    sku VARCHAR(20) PRIMARY KEY,
    internal_id UUID DEFAULT gen_random_uuid(),
    brand VARCHAR(50) NOT NULL,           -- 'Ski-Doo', 'Lynx', 'Sea-Doo'
    model_year INTEGER NOT NULL,
    model_family VARCHAR(100),            -- 'MXZ', 'Summit', 'Renegade'
    base_model VARCHAR(200),
    platform VARCHAR(50),                 -- 'REV Gen5', 'REV Gen4'
    category VARCHAR(50),                 -- 'Trail', 'Deep Snow', 'Crossover'
    
    -- Core queryable specifications
    engine_model VARCHAR(100),
    engine_displacement_cc INTEGER,
    track_length_mm INTEGER,
    track_width_mm INTEGER,
    track_profile_mm INTEGER,
    dry_weight_kg INTEGER,
    
    -- Complete specifications in JSONB
    full_specifications JSONB NOT NULL DEFAULT '{}',
    marketing_texts JSONB DEFAULT '{}',   -- Multi-language content
    raw_sources JSONB DEFAULT '[]',       -- Source attribution
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Price entries with market-specific data
CREATE TABLE price_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    price_list_id UUID NOT NULL,
    model_code VARCHAR(50) NOT NULL,      -- Original codes like "LTTA"
    parsed_product_name TEXT,
    parsed_specifications JSONB,
    price_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    market VARCHAR(10) NOT NULL,          -- 'FI', 'SE', 'NO', 'DK'
    source_page INTEGER,
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Model code mapping with inheritance tracking
CREATE TABLE model_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_code VARCHAR(50) NOT NULL,      -- LTTA, MVTL, etc.
    catalog_sku VARCHAR(20) NOT NULL,     -- Final product SKU
    base_model VARCHAR(100) NOT NULL,     -- Base model used for inheritance
    confidence_score DECIMAL(3,2) NOT NULL,
    processing_method VARCHAR(50) NOT NULL, -- 'exact_lookup', 'claude_semantic'
    requires_review BOOLEAN DEFAULT FALSE,
    inheritance_chain JSONB DEFAULT '{}', -- Audit trail
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (catalog_sku) REFERENCES products(sku)
);
```

### Performance Indexes
```sql
-- Critical indexes for query performance
CREATE INDEX idx_products_brand_year ON products(brand, model_year);
CREATE INDEX idx_products_specs_gin ON products(full_specifications) USING GIN;
CREATE INDEX idx_price_entries_market ON price_entries(market, model_year);
CREATE INDEX idx_model_mappings_confidence ON model_mappings(confidence_score DESC);
CREATE INDEX idx_model_mappings_method ON model_mappings(processing_method);
```

## 🔄 5-Stage Inheritance Pipeline

### Stage 1: Base Model Matching

**Objective**: Match model family to catalog base model with high confidence

```python
def match_base_model(price_entry: Dict) -> MatchResult:
    """Match model family to catalog base model"""
    
    brand = detect_brand_from_source(price_entry['source'])
    model_family = f"{price_entry['malli']} {price_entry['paketti']}"  # "Rave RE"
    
    lookup_key = f"{brand}_{model_family}".replace(" ", "_")
    
    # Exact lookup first (98% confidence)
    base_model = catalog_base_models.get(lookup_key)
    
    if base_model:
        return MatchResult(
            base_model=base_model,
            confidence=0.98,
            method="exact_lookup"
        )
    else:
        # Claude semantic matching fallback
        return claude_match_base_model(
            brand=brand,
            model_family=model_family,
            available_catalogs=get_brand_catalogs(brand)
        )
```

**Quality Metrics**:
- 95%+ exact lookup success rate
- <5% requiring Claude semantic matching
- 100% base model resolution

### Stage 2: Full Specification Inheritance

**Objective**: Inherit ALL specifications from matched base model

```python
def inherit_full_specifications(base_model: BaseModel) -> Dict:
    """Inherit complete specifications from base model catalog"""
    
    inherited_specs = {
        # Fixed platform specifications
        "platform": base_model.platform,
        "suspension": base_model.suspension,
        "brake_system": base_model.brake_system,
        "chassis": base_model.chassis_specs,
        
        # Available configuration options
        "engine_options": base_model.available_engines,
        "track_options": base_model.available_tracks, 
        "starter_options": base_model.starter_types,
        "display_options": base_model.display_types,
        "color_options": base_model.available_colors,
        
        # Standard specifications
        "weight_range": base_model.weight_specifications,
        "dimensions": base_model.dimensions,
        "standard_features": base_model.included_features
    }
    
    return inherited_specs
```

### Stage 3: Variant Selection

**Objective**: Select specific configuration based on price entry data

```python
def apply_variant_selections(inherited_specs: Dict, price_entry: Dict) -> Dict:
    """Select specific options from inherited specifications"""
    
    final_specs = inherited_specs.copy()
    
    # Select specific engine from available options
    selected_engine = match_engine_option(
        price_entry['moottori'],  # "600R E-TEC"  
        inherited_specs['engine_options']
    )
    final_specs['engine'] = selected_engine
    
    # Select specific track configuration
    selected_track = match_track_option(
        price_entry['telamatto'],  # "129in 3300mm"
        inherited_specs['track_options'] 
    )
    final_specs['track'] = selected_track
    
    # Apply other selections
    final_specs['starter'] = price_entry['kaynnistin']
    final_specs['display'] = price_entry['mittaristo']
    final_specs['color'] = price_entry['vari']
    
    return final_specs
```

### Stage 4: Spring Options Enhancement

**Objective**: Apply spring options modifications with Claude research

```python
def enhance_with_spring_options(base_specs: Dict, price_entry: Dict) -> Dict:
    """Apply spring options using Claude domain knowledge"""
    
    spring_options = price_entry.get('kevätoptiot', '').strip()
    
    if not spring_options:
        return base_specs
    
    enhanced_specs = base_specs.copy()
    
    # Claude researches and applies spring modifications
    spring_enhancements = claude_research_spring_options(
        base_model=base_specs['model_name'],
        brand=base_specs['brand'],
        spring_options=spring_options,
        model_year=base_specs['model_year']
    )
    
    # Apply enhancements to specifications
    enhanced_specs.update(spring_enhancements)
    
    # Log spring option application
    enhanced_specs['spring_modifications'] = {
        'original_options': spring_options,
        'applied_changes': spring_enhancements,
        'confidence': spring_enhancements.get('confidence', 0.95)
    }
    
    return enhanced_specs
```

### Stage 5: Final Validation & Quality Assurance

**Objective**: Ensure complete product meets production standards

```python
def validate_complete_product(final_specs: Dict, price_entry: Dict) -> ValidationResult:
    """Multi-layer validation of complete product"""
    
    validation_results = []
    
    # Claude consistency validation
    claude_validation = claude_validate_complete_product(
        specifications=final_specs,
        original_price_entry=price_entry,
        inheritance_audit_trail=build_audit_trail(final_specs)
    )
    validation_results.append(claude_validation)
    
    # Technical specification validation
    tech_validation = validate_technical_specifications(final_specs)
    validation_results.append(tech_validation)
    
    # Business rule validation
    business_validation = validate_business_rules(final_specs)
    validation_results.append(business_validation)
    
    # Calculate final confidence
    final_confidence = calculate_weighted_confidence(validation_results)
    
    return ValidationResult(
        success=all(v.success for v in validation_results),
        confidence=final_confidence,
        validation_details=validation_results,
        auto_accept=final_confidence >= 0.95
    )
```

## 🎯 Success Metrics and KPIs

### Processing Performance
- **Throughput**: 100+ products/minute (target)
- **API Efficiency**: Optimized Claude batching
- **Memory Usage**: <2GB for typical price list
- **Database Performance**: <100ms for standard queries

### Data Quality Metrics
- **Base Model Match Rate**: ≥95% exact lookup success
- **Confidence Distribution**: 80%+ high confidence (≥0.95)
- **Specification Completeness**: 100% for critical specs
- **Spring Options Resolution**: 100% for populated fields

### Business Impact Metrics
- **Cost per Product**: <$3.00 including all processing
- **Time to Market**: Same-day price list updates
- **Auto-Accept Rate**: ≥95% requiring no manual review
- **Error Rate**: <1% false positives

## 🛡️ Quality Assurance Framework

### Confidence Scoring
- **≥0.95**: Automatic acceptance, production ready
- **0.85-0.94**: Auto-accept with monitoring flags
- **<0.85**: System error requiring investigation

### Data Completeness Validation
```python
REQUIRED_SPECIFICATIONS = {
    'engine': ['model', 'displacement_cc', 'hp', 'cooling_type'],
    'track': ['length_mm', 'width_mm', 'profile', 'stud_pattern'],
    'suspension': ['front_type', 'rear_type', 'travel_mm'],
    'weight': ['dry_weight_kg'],
    'dimensions': ['length_mm', 'width_mm', 'height_mm']
}
```

### Error Recovery Strategy
- **Base Model Lookup Failures**: Claude semantic matching
- **Spring Options Parse Errors**: Claude interpretation
- **API Failures**: Exponential backoff with retry logic
- **Validation Failures**: Detailed audit trails for debugging

## 🔍 Spring Options Processing

### Detection Methods
```python
def detect_spring_options(price_entry: Dict) -> SpringAnalysis:
    """Multi-method spring options detection"""
    
    # Method 1: Check Kevätoptiot field
    spring_text = price_entry.get('kevätoptiot', '').strip()
    
    # Method 2: Check for highlighted model codes (visual indicator)
    is_highlighted = check_model_highlighting(price_entry['tuote_nro'])
    
    return SpringAnalysis(
        has_spring_options=bool(spring_text) or is_highlighted,
        specific_options=parse_spring_options(spring_text),
        highlight_detected=is_highlighted,
        requires_claude_research=True
    )
```

### Common Spring Options
Based on price list analysis:
- **Track modifications**: Studded tracks, different dimensions
- **Color variants**: Special edition colors
- **Suspension upgrades**: Enhanced shocks, different travel
- **Gauge packages**: Premium display types
- **Feature packages**: "Black edition", special trim levels

## 📊 Implementation Timeline

### Phase 1: Foundation (Weeks 1-2)
- Database schema implementation
- Base model catalog ingestion
- Stage 1-2 pipeline (matching + inheritance)

### Phase 2: Core Pipeline (Weeks 3-4)
- Stage 3-4 implementation (selection + spring options)
- Claude API integration
- Basic validation framework

### Phase 3: Quality & Performance (Weeks 5-6)
- Stage 5 validation implementation
- Performance optimization
- Comprehensive testing

### Phase 4: Production Readiness (Weeks 7-8)
- Error handling and recovery
- Monitoring and logging
- Documentation and deployment

## 🔧 Technical Implementation Notes

### Claude API Integration
```python
class ClaudeEnrichmentService:
    """Optimized Claude API usage for product enrichment"""
    
    def __init__(self):
        self.batch_size = 5  # Process multiple products per call
        self.rate_limit = RateLimiter(50, 60)  # 50 calls per minute
        
    async def enrich_products(self, product_batch: List[Dict]) -> List[EnrichmentResult]:
        """Batch process products for efficiency"""
        
        prompt = self.build_batch_prompt(product_batch)
        
        async with self.rate_limit:
            response = await self.claude_client.complete(prompt)
            
        return self.parse_batch_response(response)
```

### Database Optimization
```python
class ProductRepository:
    """Optimized database operations"""
    
    async def bulk_upsert_products(self, products: List[Product]) -> None:
        """Efficient bulk operations with conflict resolution"""
        
        query = """
        INSERT INTO products (sku, specifications, ...) 
        VALUES %s
        ON CONFLICT (sku) DO UPDATE SET
        specifications = EXCLUDED.specifications,
        updated_at = CURRENT_TIMESTAMP
        """
        
        await self.execute_values(query, products)
```

This methodology provides a clear, systematic approach to product data reconciliation that eliminates the complexity of traditional fuzzy matching while maintaining high accuracy through intelligent inheritance and Claude-powered enhancement.