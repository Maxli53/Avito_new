# Snowmobile Reconciliation System - Complete Technical Integration Plan

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PDF Files     │ -> │  6-Stage Pipeline │ -> │  HTML Output    │
│ (Price Lists)   │    │   + Claude AI     │    │ (Spec Sheets)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         v                       v                       v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PostgreSQL    │ <- │   Repository     │ -> │  WooCommerce    │
│   Database      │    │     Layer        │    │   Sync API      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🎯 Critical Implementation Tasks

### **Phase 1: Database Foundation** ⚡ HIGHEST PRIORITY

#### 1.1 Schema Deployment
```sql
-- Execute complete PostgreSQL schema (20+ tables)
-- Key tables with specific integration requirements:

CREATE TABLE products (
    sku VARCHAR(20) PRIMARY KEY,
    brand VARCHAR(50) NOT NULL,
    model_year INTEGER NOT NULL,
    model_family VARCHAR(100),
    full_specifications JSONB NOT NULL DEFAULT '{}',
    spring_modifications JSONB DEFAULT '{}',
    confidence_score DECIMAL(3,2),
    validation_status VARCHAR(20) DEFAULT 'pending',
    auto_accepted BOOLEAN DEFAULT FALSE,
    inheritance_audit_trail JSONB DEFAULT '{}'
);

CREATE TABLE base_models_catalog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lookup_key VARCHAR(200) NOT NULL UNIQUE,  -- "Lynx_Rave RE_2026"
    brand VARCHAR(50) NOT NULL,
    model_family VARCHAR(100) NOT NULL,
    model_year INTEGER NOT NULL,
    base_specifications JSONB NOT NULL DEFAULT '{}',
    available_variants JSONB DEFAULT '{}',
    spring_options_available JSONB DEFAULT '[]'
);

CREATE TABLE spring_options_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand VARCHAR(50) NOT NULL,
    option_name VARCHAR(200) NOT NULL,
    option_type VARCHAR(50) NOT NULL,
    specifications JSONB NOT NULL DEFAULT '{}'
);
```

#### 1.2 Repository Implementations
```python
# CRITICAL: Complete these missing repositories

# src/repositories/base_model_repository.py
class BaseModelRepository(BaseRepository[BaseModelCatalog]):
    async def find_by_lookup_key(self, brand: str, model_family: str, year: int) -> Optional[BaseModelCatalog]:
        lookup_key = f"{brand}_{model_family}_{year}"
        # Implementation needed

    async def get_available_variants(self, base_model_id: UUID) -> Dict[str, Any]:
        # Extract available variants from JSONB
        # Implementation needed

# src/repositories/spring_options_repository.py  
class SpringOptionsRepository(BaseRepository[SpringOption]):
    async def find_by_option_name(self, option_name: str, brand: str) -> Optional[SpringOption]:
        # Fuzzy matching for spring options
        # Implementation needed
        
    async def get_modifications_for_options(self, option_names: List[str]) -> Dict[str, Any]:
        # Aggregate all modifications from multiple options
        # Implementation needed
```

### **Phase 2: Pipeline Stage Completions** 🔧 CORE BUSINESS LOGIC

#### 2.1 Stage 2: Specification Inheritance
```python
# src/pipeline/stages/specification_inheritance.py
class SpecificationInheritanceStage(BasePipelineStage):
    """Inherit complete specifications from base model catalog"""
    
    async def _execute_stage(self, context: PipelineContext) -> StageResult:
        # 1. Get base model from catalog using matched base_model_id
        base_model = await self.base_model_repo.get_by_id(context.base_model_id)
        
        # 2. Copy base specifications to working product
        inherited_specs = base_model.base_specifications.copy()
        
        # 3. Apply any model-specific overrides from price entry
        # 4. Calculate inheritance confidence score
        # 5. Create audit trail of inheritance decisions
        
        return StageResult(
            success=True,
            confidence_score=confidence,
            data={"inherited_specifications": inherited_specs}
        )
```

#### 2.2 Stage 3: Customization Processing  
```python
# src/pipeline/stages/customization_processing.py
class CustomizationProcessingStage(BasePipelineStage):
    """Process track length, engine, and other customizations"""
    
    async def _execute_stage(self, context: PipelineContext) -> StageResult:
        # 1. Parse customization fields from price entry:
        #    - Track length (137cm, 129cm, etc.)
        #    - Engine type (850 E-TEC, 600R E-TEC, etc.)
        #    - Color options
        #    - Display type (digital, analog)
        
        # 2. Apply customizations to inherited specifications
        # 3. Validate customization compatibility
        # 4. Update specifications with selected variants
        
        return StageResult(
            success=True,
            confidence_score=confidence,
            data={"customized_specifications": final_specs}
        )
```

#### 2.3 Stage 4: Spring Options Enhancement
```python
# src/pipeline/stages/spring_options_enhancement.py
class SpringOptionsEnhancementStage(BasePipelineStage):
    """Process 'Kevätoptiot' field with Claude research fallback"""
    
    async def _execute_stage(self, context: PipelineContext) -> StageResult:
        spring_options_text = context.price_entry.get("spring_options", "")
        
        if not spring_options_text:
            return StageResult(success=True, confidence_score=1.0)
        
        # 1. Parse comma-separated spring options
        options = [opt.strip() for opt in spring_options_text.split(",")]
        
        modifications = {}
        total_confidence = 0.0
        
        for option in options:
            # 2. Try known options lookup first
            known_option = await self.spring_repo.find_by_option_name(option, context.brand)
            
            if known_option:
                # Use validated database option
                modifications.update(known_option.specifications)
                total_confidence += 1.0
            else:
                # 3. Claude research for unknown options
                claude_result = await self.claude_service.research_spring_option(
                    option_text=option,
                    model_context=context.product_specs,
                    brand=context.brand
                )
                modifications.update(claude_result.modifications)
                total_confidence += claude_result.confidence
        
        # 4. Apply all modifications to product specifications
        final_specs = self._apply_spring_modifications(
            context.product_specs, 
            modifications
        )
        
        avg_confidence = total_confidence / len(options) if options else 1.0
        
        return StageResult(
            success=True,
            confidence_score=avg_confidence,
            data={"spring_enhanced_specifications": final_specs}
        )
```

#### 2.4 Stage 5: Final Validation
```python
# src/pipeline/stages/final_validation.py
class FinalValidationStage(BasePipelineStage):
    """Multi-layer validation with 95%+ confidence requirement"""
    
    async def _execute_stage(self, context: PipelineContext) -> StageResult:
        validator = MultiLayerValidator(self.config)
        
        # 1. Technical validation (required fields, data types)
        tech_validation = await validator.validate_technical_completeness(
            context.product_specs
        )
        
        # 2. Business rules validation (realistic combinations)
        business_validation = await validator.validate_business_rules(
            context.product_specs
        )
        
        # 3. Claude quality validation (semantic consistency)
        claude_validation = await self.claude_service.validate_product_quality(
            product_specs=context.product_specs,
            price_entry=context.price_entry,
            inheritance_trail=context.audit_trail
        )
        
        # 4. Calculate final confidence score
        final_confidence = self._calculate_weighted_confidence([
            tech_validation.confidence,
            business_validation.confidence, 
            claude_validation.confidence
        ])
        
        # 5. Auto-acceptance decision (≥95% confidence)
        auto_accepted = final_confidence >= 0.95
        
        return StageResult(
            success=True,
            confidence_score=final_confidence,
            data={
                "final_product": context.product_specs,
                "auto_accepted": auto_accepted,
                "validation_details": {
                    "technical": tech_validation,
                    "business": business_validation,
                    "claude": claude_validation
                }
            }
        )
```

### **Phase 3: Missing Service Implementations** 🔧

#### 3.1 PDF Processing Service
```python
# src/services/pdf_processing.py
class PDFProcessingService:
    """Stage 0: Intelligent PDF parsing with quality assessment"""
    
    async def process_price_list_pdf(self, pdf_file: Path) -> PDFProcessingResult:
        # 1. Assess document quality (digital vs scanned)
        quality = await self._assess_document_quality(pdf_file)
        
        # 2. Select optimal parser based on quality
        parser = self._select_parser(quality)  # PyMuPDF, Camelot, Claude OCR
        
        # 3. Extract price entries with confidence scores
        entries = await parser.extract_price_entries(pdf_file)
        
        # 4. Apply parser configuration for market/language
        configured_entries = await self._apply_parser_config(entries)
        
        return PDFProcessingResult(
            price_entries=configured_entries,
            quality_assessment=quality,
            parser_used=parser.name,
            extraction_confidence=confidence
        )
```

#### 3.2 HTML Generation Service  
```python
# src/services/html_generation.py
class HTMLGenerationService:
    """Stage 6: Brand-specific HTML specification sheets"""
    
    async def generate_specification_sheet(self, 
                                         product: ProductModel, 
                                         language: str = "en") -> HTMLDocument:
        # 1. Validate product meets quality threshold (≥95% confidence)
        if product.confidence_score < 0.95:
            raise ValidationError("Product quality insufficient for HTML generation")
        
        # 2. Load brand-specific template
        template = await self._load_brand_template(product.brand)
        
        # 3. Generate multi-language content
        content = await self._generate_localized_content(product, language)
        
        # 4. Apply brand styling and assets
        styled_html = await self._apply_brand_styling(content, product.brand)
        
        # 5. Validate HTML quality and accessibility
        validation = await self._validate_html_output(styled_html)
        
        return HTMLDocument(
            html_content=styled_html,
            language=language,
            brand=product.brand,
            sku=product.sku,
            generation_timestamp=datetime.utcnow(),
            validation_passed=validation.passed
        )
```

### **Phase 4: Data Integration Bridges** 🌉

#### 4.1 Import/Export Pipeline
```python
# src/services/data_import_export.py
class DataImportExportService:
    """Handle CSV/Excel imports and multiple export formats"""
    
    async def import_from_excel(self, file_data: bytes, mapping_rules: dict) -> ImportResult:
        # 1. Detect Excel structure (sheets, columns, formats)
        # 2. Apply mapping rules to normalize field names
        # 3. Validate data integrity and business rules
        # 4. Insert into appropriate database tables
        # 5. Track import job progress and errors
        
    async def export_products(self, filters: dict, format: str) -> ExportResult:
        # 1. Query products based on filters
        # 2. Format data according to export type (CSV, Excel, JSON)
        # 3. Include confidence scores and validation status
        # 4. Generate export file with proper headers
```

#### 4.2 WooCommerce Synchronization
```python
# src/services/woocommerce_sync.py
class WooCommerceSyncService:
    """Bidirectional sync with WooCommerce stores"""
    
    async def sync_products_to_woocommerce(self, sku_list: List[str]) -> SyncResult:
        # 1. Get high-confidence products (≥95%) from database
        # 2. Transform specifications to WooCommerce product format
        # 3. Create/update products via WooCommerce REST API
        # 4. Handle variations, attributes, and custom fields
        # 5. Track sync status and handle conflicts
        
    async def pull_woocommerce_changes(self, store_id: str) -> SyncResult:
        # 1. Get modified products from WooCommerce
        # 2. Compare with database versions
        # 3. Apply business rules for conflict resolution
        # 4. Update database with approved changes
```

### **Phase 5: Integration Points & Data Flow** 🔄

#### 5.1 Complete Pipeline Orchestration
```python
# src/pipeline/inheritance_pipeline.py (ENHANCED)
class InheritancePipeline:
    """Complete 6-stage processing with full integration"""
    
    def __init__(self, 
                 product_repo: ProductRepository,
                 base_model_repo: BaseModelRepository,
                 spring_repo: SpringOptionsRepository,
                 claude_service: ClaudeEnrichmentService,
                 pdf_service: PDFProcessingService,
                 html_service: HTMLGenerationService):
        self.repositories = {
            'product': product_repo,
            'base_model': base_model_repo,
            'spring_options': spring_repo
        }
        self.services = {
            'claude': claude_service,
            'pdf': pdf_service,
            'html': html_service
        }
    
    async def process_complete_price_list(self, pdf_file: Path) -> ProcessingJobResult:
        """Execute complete end-to-end processing"""
        
        # Stage 0: PDF Processing
        pdf_result = await self.services['pdf'].process_price_list_pdf(pdf_file)
        
        results = []
        for price_entry in pdf_result.price_entries:
            # Create pipeline context
            context = PipelineContext(
                price_entry=price_entry,
                repositories=self.repositories,
                services=self.services
            )
            
            # Execute all 5 stages sequentially
            stage_1 = await self.stage_1_base_model_matching.execute(context)
            context.update_from_stage(stage_1)
            
            stage_2 = await self.stage_2_specification_inheritance.execute(context)
            context.update_from_stage(stage_2)
            
            stage_3 = await self.stage_3_customization_processing.execute(context)
            context.update_from_stage(stage_3)
            
            stage_4 = await self.stage_4_spring_options_enhancement.execute(context)
            context.update_from_stage(stage_4)
            
            stage_5 = await self.stage_5_final_validation.execute(context)
            
            # Save to database if validation passed
            if stage_5.success and stage_5.confidence_score >= 0.95:
                product = await self.repositories['product'].create(context.final_product)
                
                # Generate HTML if auto-accepted
                if stage_5.data.get('auto_accepted'):
                    html_doc = await self.services['html'].generate_specification_sheet(product)
                    results.append({'product': product, 'html': html_doc})
                else:
                    results.append({'product': product, 'html': None})
            
        return ProcessingJobResult(
            total_processed=len(pdf_result.price_entries),
            successful=len([r for r in results if r['product']]),
            auto_accepted=len([r for r in results if r['html']]),
            results=results
        )
```

#### 5.2 API Layer Integration
```python
# src/main.py (FastAPI Application)
from fastapi import FastAPI, UploadFile, BackgroundTasks
from src.pipeline.inheritance_pipeline import InheritancePipeline
from src.services.woocommerce_sync import WooCommerceSyncService

app = FastAPI(title="Snowmobile Reconciliation API")

# Initialize all dependencies
pipeline = InheritancePipeline(
    product_repo=ProductRepository(db_session),
    base_model_repo=BaseModelRepository(db_session),
    spring_repo=SpringOptionsRepository(db_session),
    claude_service=ClaudeEnrichmentService(config),
    pdf_service=PDFProcessingService(config),
    html_service=HTMLGenerationService(config)
)

@app.post("/api/process-price-list")
async def process_price_list(file: UploadFile, background_tasks: BackgroundTasks):
    """Process uploaded PDF price list through complete pipeline"""
    
    # Save uploaded file
    pdf_path = await save_upload(file)
    
    # Start background processing
    background_tasks.add_task(pipeline.process_complete_price_list, pdf_path)
    
    return {"message": "Processing started", "job_id": job_id}

@app.get("/api/products/{sku}/html")
async def get_product_html(sku: str, language: str = "en"):
    """Get HTML specification sheet for product"""
    
    product = await pipeline.repositories['product'].get_by_sku(sku)
    if not product or product.confidence_score < 0.95:
        raise HTTPException(404, "Product not found or quality insufficient")
    
    html_doc = await pipeline.services['html'].generate_specification_sheet(product, language)
    return HTMLResponse(html_doc.html_content)

@app.post("/api/sync-to-woocommerce")
async def sync_to_woocommerce(sku_list: List[str], store_id: str):
    """Sync high-confidence products to WooCommerce"""
    
    sync_service = WooCommerceSyncService(config)
    result = await sync_service.sync_products_to_woocommerce(sku_list)
    
    return {"synced": result.successful, "failed": result.failed, "details": result.details}
```

### **Phase 6: Quality Assurance & Testing** 🧪

#### 6.1 Integration Testing Framework
```python
# tests/integration/test_complete_pipeline.py
class TestCompletePipeline:
    """End-to-end pipeline testing with real data"""
    
    async def test_lynx_price_list_processing(self):
        """Test complete Lynx price list processing"""
        
        # Load real Lynx PDF price list
        pdf_path = Path("tests/fixtures/lynx_price_list_2026.pdf")
        
        # Process through complete pipeline
        result = await self.pipeline.process_complete_price_list(pdf_path)
        
        # Verify results
        assert result.successful > 0
        assert result.auto_accepted > 0
        
        # Check specific model codes were processed correctly
        ltta_product = await self.product_repo.get_by_sku("LTTA-some-generated-sku")
        assert ltta_product.model_family == "Rave RE"
        assert ltta_product.confidence_score >= 0.95
        
        # Verify HTML generation
        html_doc = await self.html_service.generate_specification_sheet(ltta_product)
        assert "Rave RE" in html_doc.html_content
        assert html_doc.validation_passed
    
    async def test_spring_options_processing(self):
        """Test spring options enhancement with Claude fallback"""
        
        # Test known spring option
        context = create_test_context(spring_options="Black edition")
        result = await self.stage_4.execute(context)
        assert result.confidence_score >= 0.95
        
        # Test unknown spring option (triggers Claude research)
        context = create_test_context(spring_options="Custom racing setup")
        result = await self.stage_4.execute(context)
        assert result.success
        assert result.confidence_score >= 0.7  # Lower but still valid
```

#### 6.2 Performance & Load Testing
```python
# tests/performance/test_bulk_operations.py
class TestBulkPerformance:
    """Performance testing for bulk operations"""
    
    async def test_bulk_price_list_processing(self):
        """Test processing multiple price lists simultaneously"""
        
        # Process 5 price lists concurrently
        pdf_files = [f"tests/fixtures/price_list_{i}.pdf" for i in range(5)]
        
        start_time = time.time()
        results = await asyncio.gather(*[
            self.pipeline.process_complete_price_list(pdf) for pdf in pdf_files
        ])
        processing_time = time.time() - start_time
        
        # Performance requirements
        assert processing_time < 300  # 5 minutes max for 5 lists
        assert sum(r.successful for r in results) > 100  # Min 100 products processed
        
        # Claude API cost tracking
        total_cost = sum(r.claude_cost_usd for r in results)
        assert total_cost < 50.0  # Max $50 per batch
```

### **Phase 7: Operations & Monitoring** 📊

#### 7.1 Database Operations
```python
# src/database/operations.py
class DatabaseOperations:
    """Database management and optimization"""
    
    async def sync_from_documents(self):
        """Sync database with latest uploaded documents"""
        # 1. Detect new/modified documents in repository
        # 2. Process changes through pipeline
        # 3. Update affected products
        # 4. Maintain data consistency
    
    async def backup_with_versioning(self):
        """Create versioned database backup"""
        # 1. Create timestamped backup
        # 2. Compress and store
        # 3. Clean old backups (keep last 30)
        # 4. Verify backup integrity
    
    async def optimize_performance(self):
        """Optimize database for query performance"""
        # 1. Analyze query patterns
        # 2. Add/remove indexes as needed
        # 3. Update table statistics
        # 4. Monitor slow queries
```

#### 7.2 Monitoring & Health Checks
```python
# src/monitoring/health_checks.py
class SystemHealthMonitor:
    """Comprehensive system health monitoring"""
    
    async def check_pipeline_health(self) -> HealthStatus:
        # 1. Database connectivity and performance
        # 2. Claude API availability and costs
        # 3. Processing queue status
        # 4. Recent error rates
        # 5. Confidence score distributions
        
    async def check_data_quality(self) -> QualityReport:
        # 1. Products with low confidence scores
        # 2. Failed validation rates
        # 3. Spring options coverage
        # 4. Processing time trends
```

## 🚀 Implementation Priority Queue

### **Week 1: Critical Path** 
1. ✅ Deploy database schema completely
2. ✅ Implement missing repositories (base_model, spring_options)
3. ✅ Complete Stage 2 (Specification Inheritance)
4. ✅ Complete Stage 3 (Customization Processing)

### **Week 2: Core Features**
5. ✅ Complete Stage 4 (Spring Options Enhancement) 
6. ✅ Complete Stage 5 (Final Validation)
7. ✅ Implement PDF Processing Service
8. ✅ Integration testing with real PDF files

### **Week 3: Output & Sync**
9. ✅ Implement HTML Generation Service
10. ✅ WooCommerce synchronization service
11. ✅ Import/Export data bridges
12. ✅ Performance optimization and monitoring

### **Week 4: Production Ready**
13. ✅ Complete test coverage (80%+)
14. ✅ Performance testing and optimization
15. ✅ Production deployment configuration
16. ✅ Monitoring and alerting setup

## 🔧 Technical Validation Checklist

### **Development Standards Compliance**
- [ ] Poetry configuration with strict type checking
- [ ] Pydantic models for all business data structures
- [ ] Repository pattern with proper dependency injection
- [ ] 80%+ test coverage with real data testing
- [ ] Pre-commit hooks with quality automation
- [ ] No hardcoded values outside configuration
- [ ] Comprehensive error handling and logging

### **Architecture Integration**
- [ ] All 6 pipeline stages fully implemented
- [ ] Database schema deployed with proper indexes
- [ ] Claude API integration with cost tracking
- [ ] PDF processing with quality assessment
- [ ] HTML generation with brand templates
- [ ] WooCommerce sync with conflict resolution

### **Production Readiness**
- [ ] Performance testing under load
- [ ] Security validation and input sanitization
- [ ] Monitoring and health check endpoints
- [ ] Backup and recovery procedures
- [ ] Documentation and developer onboarding

## 🎯 Success Metrics

**Quality Targets:**
- 95%+ products auto-accepted after pipeline processing
- <5% manual review rate for high-confidence products
- <$0.50 average Claude API cost per product processed
- <30 seconds average processing time per price list entry

**Technical Targets:**
- 80%+ test coverage maintained
- Zero mypy --strict errors
- <100ms database query response times
- 99.9% pipeline success rate

This integration plan provides the complete technical roadmap to connect all components into a production-ready system following enterprise development standards.