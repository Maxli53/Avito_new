"""
Blind End-to-End Pipeline Test
Tests ADTD and ADTC model codes from Ski-Doo 2026 documents
No predetermined outcomes - discovers what actually happens
"""
import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import all pipeline components
import sys
sys.path.append("snowmobile-reconciliation")

from src.models.database import Base, ProductTable
from src.models.domain import PipelineConfig, PriceEntry, ProductSpecification
from src.services.claude_enrichment import ClaudeEnrichmentService
from src.services.pdf_extraction_service import PDFProcessingService
from src.repositories.product_repository import ProductRepository
from src.repositories.base_model_repository import BaseModelRepository
from src.pipeline.inheritance_pipeline import InheritancePipeline
from src.pipeline.validation.multi_layer_validator import MultiLayerValidator


class BlindE2ETest:
    """
    Blind end-to-end test - no expected outcomes.
    Just run the pipeline and see what happens.
    """
    
    def __init__(self):
        # Load configuration from environment
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        if not self.claude_api_key:
            raise ValueError("CLAUDE_API_KEY not found in environment variables")
            
        self.config = PipelineConfig()
        self.test_timestamp = datetime.now()
        self.target_models = ["ADTD", "ADTC"]
        
        # BOTH PDFs needed for complete processing - using real paths from @data
        self.price_list_pdf = Path("TEST_DUAL_PARSER_PIPELINE/docs/SKI-DOO_2026-PRICE_LIST.pdf")
        self.spec_book_pdf = Path(
            "../../../AppData/Roaming/JetBrains/PyCharm2025.1/scratches/SKIDOO_2026 PRODUCT SPEC BOOK 1-35.pdf")
        
        # Real PostgreSQL database connection
        self.database_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://snowmobile_user:snowmobile_pass@localhost:5432/snowmobile_reconciliation')
        
        # Storage for all captured data
        self.captured_data = {
            "test_metadata": {
                "timestamp": self.test_timestamp.isoformat(),
                "price_list_pdf": str(self.price_list_pdf),
                "spec_book_pdf": str(self.spec_book_pdf),
                "target_models": self.target_models,
                "test_type": "blind_e2e",
                "database_url": self.database_url.split('@')[1] if '@' in self.database_url else "localhost",
                "claude_api_key_configured": bool(self.claude_api_key)
            },
            "extraction_stage": {},
            "pipeline_stages": {},
            "final_products": {},
            "database_operations": {},
            "performance_metrics": {},
            "errors_and_warnings": []
        }
        
    async def run_blind_test(self):
        """Execute the blind test and capture everything"""
        print("\n" + "="*80)
        print("BLIND END-TO-END PIPELINE TEST")
        print("="*80)
        print(f"Timestamp: {self.test_timestamp}")
        print(f"Price List PDF: {self.price_list_pdf}")
        print(f"Spec Book PDF: {self.spec_book_pdf}")
        print(f"Target Models: {', '.join(self.target_models)}")
        print(f"Database: {self.database_url.split('@')[1] if '@' in self.database_url else 'localhost'}")
        print(f"Claude API: {'CONFIGURED' if self.claude_api_key else 'MISSING'}")
        print("="*80)
        
        # Check both PDFs exist
        if not self.price_list_pdf.exists():
            raise FileNotFoundError(f"Price list PDF not found: {self.price_list_pdf}")
        if not self.spec_book_pdf.exists():
            raise FileNotFoundError(f"Spec book PDF not found: {self.spec_book_pdf}")
            
        print(f"Both PDF files found")
        print(f"   Price List: {self.price_list_pdf.stat().st_size:,} bytes")
        print(f"   Spec Book: {self.spec_book_pdf.stat().st_size:,} bytes")
        
        # Initialize real PostgreSQL database
        print("\nInitializing Real PostgreSQL Database...")
        try:
            engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            # Create all tables - will use simplified schema for SQLite fallback
            async with engine.begin() as conn:
                # For SQLite fallback, we'll create a simplified schema
                if "sqlite" in str(engine.url):
                    # Create simplified tables for testing
                    await conn.execute(text('''
                        CREATE TABLE IF NOT EXISTS products (
                            id TEXT PRIMARY KEY,
                            model_code TEXT NOT NULL,
                            base_model_id TEXT,
                            brand TEXT NOT NULL,
                            model_name TEXT,
                            model_year INTEGER,
                            price REAL,
                            currency TEXT DEFAULT 'EUR',
                            specifications TEXT,  -- JSON as text
                            overall_confidence REAL,
                            confidence_level TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            processed_by TEXT
                        )
                    '''))
                    
                    await conn.execute(text('''
                        CREATE TABLE IF NOT EXISTS processing_statistics (
                            metric_name TEXT PRIMARY KEY,
                            metric_value INTEGER DEFAULT 0
                        )
                    '''))
                    
                    print("Created simplified SQLite schema for testing")
                else:
                    await conn.run_sync(Base.metadata.create_all)
            
            session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            print("PostgreSQL database initialized with full enterprise schema")
            
        except Exception as e:
            print(f"Database connection failed: {e}")
            print("   Falling back to SQLite for testing...")
            engine = create_async_engine(
                f"sqlite+aiosqlite:///blind_test_{self.test_timestamp:%Y%m%d_%H%M%S}.db",
                echo=False
            )
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            
            self.captured_data["errors_and_warnings"].append(f"PostgreSQL connection failed, using SQLite: {str(e)}")
        
        # Initialize services with real Claude API key
        print("Initializing Services with Real Claude API...")
        claude_service = ClaudeEnrichmentService(
            self.config.claude,
            api_key=self.claude_api_key  # Use real API key from environment
        )
        pdf_service = PDFProcessingService(claude_service)
        validator = MultiLayerValidator(self.config.pipeline)
        
        try:
            # STAGE 0: PDF EXTRACTION FROM PRICE LIST
            print("\n" + "-"*60)
            print("STAGE 0: PDF EXTRACTION FROM PRICE LIST")
            print("-"*60)
            
            extraction_start = datetime.now()
            
            print(f"Extracting from price list: {self.price_list_pdf}")
            print(f"File size: {self.price_list_pdf.stat().st_size:,} bytes")
            
            # Extract ALL price entries from price list using real PDF processing
            try:
                all_price_entries = await pdf_service.process_price_list_pdf(
                    self.price_list_pdf,
                    "ADTD"  # Start with first model, should find both ADTD and ADTC
                )
                
                print(f"PDF processing result: {type(all_price_entries)}")
                
                # Handle different return types from PDF service
                if hasattr(all_price_entries, 'extraction_success'):
                    # Single extraction result
                    if all_price_entries.extraction_success:
                        price_entry = PriceEntry(
                            model_code=all_price_entries.model_code,
                            price=all_price_entries.price,
                            currency=all_price_entries.currency,
                            model_name=all_price_entries.model_name,
                            brand="Ski-Doo",
                            model_year=2026,
                            specifications=all_price_entries.specifications or {}
                        )
                        all_price_entries = [price_entry]
                    else:
                        all_price_entries = []
                elif isinstance(all_price_entries, list):
                    # Already a list of entries
                    pass
                else:
                    # Convert single entry to list
                    all_price_entries = [all_price_entries] if all_price_entries else []
                
                # Try to extract ADTC separately if not found
                if not any(entry.model_code == "ADTC" for entry in all_price_entries):
                    print("Attempting to extract ADTC separately...")
                    adtc_result = await pdf_service.process_price_list_pdf(
                        self.price_list_pdf,
                        "ADTC"
                    )
                    
                    if hasattr(adtc_result, 'extraction_success') and adtc_result.extraction_success:
                        adtc_entry = PriceEntry(
                            model_code=adtc_result.model_code,
                            price=adtc_result.price,
                            currency=adtc_result.currency,
                            model_name=adtc_result.model_name,
                            brand="Ski-Doo",
                            model_year=2026,
                            specifications=adtc_result.specifications or {}
                        )
                        all_price_entries.append(adtc_entry)
                
            except Exception as e:
                print(f"PDF extraction error: {e}")
                self.captured_data["errors_and_warnings"].append(f"PDF extraction failed: {str(e)}")
                all_price_entries = []
            
            print(f"Total entries extracted: {len(all_price_entries) if all_price_entries else 0}")
            
            # Filter to our target models
            target_entries = [
                entry for entry in (all_price_entries or [])
                if entry.model_code in self.target_models
            ]
            
            print(f"Target model entries found: {len(target_entries)}")
            
            # Capture extraction details
            self.captured_data["extraction_stage"] = {
                "price_list_extraction": {
                    "total_entries": len(all_price_entries) if all_price_entries else 0,
                    "target_entries_found": len(target_entries),
                    "models_found": [e.model_code for e in target_entries],
                    "extraction_time_ms": (datetime.now() - extraction_start).total_seconds() * 1000
                },
                "raw_price_entries": [
                    {
                        "model_code": e.model_code,
                        "brand": e.brand,
                        "model_year": e.model_year,
                        "price": float(e.price) if e.price else 0.0,
                        "currency": e.currency,
                        "model_name": e.model_name,
                        "specifications": e.specifications
                    }
                    for e in target_entries
                ]
            }
            
            if not target_entries:
                error_msg = f"No entries found for models {self.target_models} in price list"
                print(f"{error_msg}")
                self.captured_data["errors_and_warnings"].append(error_msg)
                await self._generate_report()
                return
            
            # Print what we found
            for entry in target_entries:
                print(f"\n  Model: {entry.model_code}")
                print(f"  Name: {entry.model_name}")
                print(f"  Price: {entry.price} {entry.currency}")
                print(f"  Year: {entry.model_year}")
                print(f"  Initial Specs: {json.dumps(entry.specifications, indent=2)}")
            
            # STAGE 0.5: ENRICH WITH SPEC BOOK (if PDF service supports it)
            print("\n" + "-"*60)
            print("STAGE 0.5: ENRICHMENT FROM SPEC BOOK")
            print("-"*60)
            
            spec_extraction_start = datetime.now()
            
            print(f"Checking spec book for additional details: {self.spec_book_pdf}")
            print(f"File size: {self.spec_book_pdf.stat().st_size:,} bytes")
            
            # Note: This depends on how your PDF service handles spec extraction
            self.captured_data["extraction_stage"]["spec_book_available"] = True
            self.captured_data["extraction_stage"]["spec_extraction_time_ms"] = (
                datetime.now() - spec_extraction_start
            ).total_seconds() * 1000
            
            # STAGES 1-5: INHERITANCE PIPELINE
            print("\n" + "-"*60)
            print("STAGES 1-5: INHERITANCE PIPELINE PROCESSING")
            print("-"*60)
            
            async with session_maker() as session:
                product_repo = ProductRepository(session)
                base_model_repo = BaseModelRepository(session)
                
                pipeline = InheritancePipeline(
                    config=self.config,
                    product_repository=product_repo,
                    base_model_repository=base_model_repo,
                    claude_service=claude_service,
                    validator=validator,
                    pdf_service=pdf_service
                )
                
                pipeline_start = datetime.now()
                
                # Process through the 5-stage pipeline
                result = await pipeline.process_price_entries(target_entries)
                
                pipeline_duration = (datetime.now() - pipeline_start).total_seconds() * 1000
                
                print(f"\nPipeline Results:")
                print(f"  Success: {result.success}")
                print(f"  Products Processed: {result.products_processed}")
                print(f"  Products Successful: {result.products_successful}")
                print(f"  Products Failed: {result.products_failed}")
                print(f"  Processing Time: {result.total_processing_time_ms:.2f}ms")
                print(f"  Claude Tokens Used: {result.claude_tokens_used}")
                print(f"  Claude Cost: ${result.claude_cost_total:.4f}")
                
                # Capture pipeline stage details
                self.captured_data["pipeline_stages"] = {
                    "summary": {
                        "success": result.success,
                        "products_processed": result.products_processed,
                        "products_successful": result.products_successful,
                        "products_failed": result.products_failed,
                        "processing_time_ms": result.total_processing_time_ms,
                        "claude_tokens_used": result.claude_tokens_used,
                        "claude_cost": result.claude_cost_total
                    },
                    "products": []
                }
                
                # Capture detailed product results
                if result.products:
                    for product in result.products:
                        print(f"\n  Product: {product.model_code}")
                        print(f"    Product ID: {product.product_id}")
                        print(f"    Base Model ID: {product.base_model_id}")
                        print(f"    Confidence: {product.overall_confidence:.2%}")
                        print(f"    Confidence Level: {product.confidence_level}")
                        
                        product_data = {
                            "product_id": str(product.product_id),
                            "model_code": product.model_code,
                            "model_year": product.model_year,
                            "base_model_id": product.base_model_id,
                            "overall_confidence": product.overall_confidence,
                            "confidence_level": product.confidence_level.value,
                            "specifications": product.specifications,
                            "pipeline_results": [
                                {
                                    "stage": pr.stage.value if hasattr(pr.stage, 'value') else str(pr.stage),
                                    "success": pr.success,
                                    "confidence": pr.confidence_score,
                                    "processing_time_ms": pr.processing_time_ms,
                                    "error_message": "; ".join(pr.errors) if pr.errors else None
                                }
                                for pr in product.pipeline_results
                            ]
                        }
                        
                        self.captured_data["pipeline_stages"]["products"].append(product_data)
                        self.captured_data["final_products"][product.model_code] = product_data
                        
                        # DATABASE STORAGE TEST
                        print(f"\n    Testing database storage for {product.model_code}...")
                        
                        try:
                            # Save to database
                            saved_product = await product_repo.create_product(
                                product,
                                audit_user="blind_test"
                            )
                            
                            # Retrieve to verify
                            retrieved_product = await product_repo.get_by_model_code(
                                product.model_code,
                                product.model_year
                            )
                            
                            db_success = (
                                saved_product is not None and 
                                retrieved_product is not None and
                                saved_product.product_id == retrieved_product.product_id
                            )
                            
                            print(f"      Storage: {'Success' if saved_product else 'Failed'}")
                            print(f"      Retrieval: {'Success' if retrieved_product else 'Failed'}")
                            print(f"      Verification: {'Match' if db_success else 'Mismatch'}")
                            
                            self.captured_data["database_operations"][product.model_code] = {
                                "storage_success": saved_product is not None,
                                "retrieval_success": retrieved_product is not None,
                                "id_match": db_success,
                                "stored_id": str(saved_product.product_id) if saved_product else None
                            }
                            
                        except Exception as e:
                            print(f"      Database error: {e}")
                            self.captured_data["database_operations"][product.model_code] = {
                                "error": str(e)
                            }
                            self.captured_data["errors_and_warnings"].append(
                                f"Database error for {product.model_code}: {e}"
                            )
                
                # Get final statistics
                try:
                    stats = await product_repo.get_processing_statistics()
                    self.captured_data["database_operations"]["statistics"] = stats
                except Exception as e:
                    self.captured_data["errors_and_warnings"].append(f"Failed to get statistics: {e}")
                
            # PERFORMANCE METRICS
            total_duration = (datetime.now() - self.test_timestamp).total_seconds() * 1000
            
            self.captured_data["performance_metrics"] = {
                "total_test_duration_ms": total_duration,
                "pdf_extraction_ms": self.captured_data["extraction_stage"]["price_list_extraction"]["extraction_time_ms"],
                "pipeline_processing_ms": pipeline_duration,
                "database_operations_ms": total_duration - pipeline_duration - self.captured_data["extraction_stage"]["price_list_extraction"]["extraction_time_ms"],
                "claude_api_calls": result.claude_tokens_used > 0,
                "claude_tokens": result.claude_tokens_used,
                "claude_cost_usd": result.claude_cost_total
            }
            
        except Exception as e:
            print(f"\nTEST FAILED WITH ERROR: {e}")
            self.captured_data["errors_and_warnings"].append(f"Fatal error: {str(e)}")
            import traceback
            self.captured_data["errors_and_warnings"].append(traceback.format_exc())
            
        finally:
            # Cleanup
            await claude_service.close()
            await engine.dispose()
            
            # Generate report
            await self._generate_report()
    
    async def _generate_report(self):
        """Generate HTML report with all captured data"""
        print("\n" + "-"*60)
        print("GENERATING REPORT")
        print("-"*60)
        
        # Create results directory
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        # Save JSON data
        json_file = results_dir / f"blind_test_{self.test_timestamp:%Y%m%d_%H%M%S}.json"
        
        with open(json_file, "w") as f:
            json.dump(self.captured_data, f, indent=2, default=str)
        
        print(f"JSON data saved: {json_file}")
        
        # Generate HTML report
        html_content = self._create_html_report()
        
        html_file = results_dir / f"blind_test_{self.test_timestamp:%Y%m%d_%H%M%S}.html"
        with open(html_file, "w") as f:
            f.write(html_content)
        
        print(f"HTML report saved: {html_file}")
        print(f"   Open in browser: file://{html_file.absolute()}")
        
    def _create_html_report(self) -> str:
        """Create detailed HTML report"""
        
        # Build product cards HTML
        product_cards = ""
        for model_code, product_data in self.captured_data.get("final_products", {}).items():
            pipeline_stages_html = ""
            for stage in product_data.get("pipeline_results", []):
                stage_status = "✅" if stage["success"] else "❌"
                confidence = stage.get("confidence", 0)
                processing_time = stage.get("processing_time_ms", 0)
                pipeline_stages_html += f"""
                <div class="stage-result">
                    <span>{stage_status} {stage['stage']}</span>
                    <span>Confidence: {confidence:.2%}</span>
                    <span>{processing_time:.1f}ms</span>
                </div>
                """
            
            db_status = self.captured_data.get("database_operations", {}).get(model_code, {})
            db_html = f"""
            <div class="db-status">
                <span>Storage: {'✅' if db_status.get('storage_success') else '❌'}</span>
                <span>Retrieval: {'✅' if db_status.get('retrieval_success') else '❌'}</span>
            </div>
            """
            
            product_cards += f"""
            <div class="product-card">
                <h3>{model_code}</h3>
                <div class="product-details">
                    <div class="metric">
                        <span class="label">Product ID:</span>
                        <span class="value">{product_data['product_id']}</span>
                    </div>
                    <div class="metric">
                        <span class="label">Base Model:</span>
                        <span class="value">{product_data.get('base_model_id', 'None')}</span>
                    </div>
                    <div class="metric">
                        <span class="label">Confidence:</span>
                        <span class="value">{product_data['overall_confidence']:.2%}</span>
                    </div>
                    <div class="metric">
                        <span class="label">Level:</span>
                        <span class="value">{product_data['confidence_level']}</span>
                    </div>
                </div>
                
                <h4>Pipeline Stages</h4>
                <div class="pipeline-stages">
                    {pipeline_stages_html}
                </div>
                
                <h4>Database Operations</h4>
                {db_html}
                
                <h4>Specifications</h4>
                <pre class="spec-json">{json.dumps(product_data.get('specifications', {}), indent=2)}</pre>
            </div>
            """
        
        # Build errors/warnings HTML
        errors_html = ""
        if self.captured_data.get("errors_and_warnings"):
            for error in self.captured_data["errors_and_warnings"]:
                errors_html += f"<div class='error-item'>{error}</div>"
        else:
            errors_html = "<div class='success-message'>No errors or warnings!</div>"
        
        # Performance metrics
        perf = self.captured_data.get("performance_metrics", {})
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Blind E2E Test - {self.test_timestamp:%Y-%m-%d %H:%M}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{ 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .test-meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .meta-item {{
            background: rgba(255,255,255,0.1);
            padding: 10px 15px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }}
        
        .content {{
            padding: 40px;
        }}
        
        section {{
            margin-bottom: 40px;
        }}
        
        h2 {{
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        
        .extraction-summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .summary-card .number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .raw-entries {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        
        .product-card {{
            background: #f9fafb;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
        }}
        
        .product-card h3 {{
            color: #764ba2;
            font-size: 1.5em;
            margin-bottom: 20px;
        }}
        
        .product-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 10px;
            background: white;
            border-radius: 6px;
        }}
        
        .metric .label {{
            color: #6b7280;
            font-weight: 500;
        }}
        
        .metric .value {{
            color: #111827;
            font-weight: bold;
        }}
        
        .pipeline-stages {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        
        .stage-result {{
            display: flex;
            justify-content: space-between;
            padding: 8px;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        .stage-result:last-child {{
            border-bottom: none;
        }}
        
        .db-status {{
            display: flex;
            gap: 20px;
            padding: 10px;
            background: white;
            border-radius: 6px;
        }}
        
        .spec-json {{
            background: #1f2937;
            color: #10b981;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            line-height: 1.4;
        }}
        
        .performance-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        
        .perf-card {{
            background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .perf-card .label {{
            color: #6b7280;
            font-size: 0.9em;
            display: block;
            margin-bottom: 5px;
        }}
        
        .perf-card .value {{
            color: #111827;
            font-size: 1.5em;
            font-weight: bold;
        }}
        
        .errors-section {{
            background: #fef2f2;
            border: 2px solid #fecaca;
            border-radius: 10px;
            padding: 20px;
        }}
        
        .error-item {{
            background: white;
            padding: 10px;
            margin: 10px 0;
            border-left: 4px solid #ef4444;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9em;
        }}
        
        .success-message {{
            background: #d1fae5;
            color: #065f46;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            font-weight: 500;
        }}
        
        h4 {{
            color: #374151;
            margin: 20px 0 10px 0;
            font-size: 1.1em;
        }}
        
        footer {{
            background: #f9fafb;
            padding: 20px;
            text-align: center;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Blind End-to-End Pipeline Test</h1>
            <div class="test-meta">
                <div class="meta-item">
                    <strong>Timestamp:</strong><br>
                    {self.test_timestamp:%Y-%m-%d %H:%M:%S}
                </div>
                <div class="meta-item">
                    <strong>Price List:</strong><br>
                    {self.price_list_pdf.name}
                </div>
                <div class="meta-item">
                    <strong>Spec Book:</strong><br>
                    {self.spec_book_pdf.name}
                </div>
                <div class="meta-item">
                    <strong>Target Models:</strong><br>
                    {', '.join(self.target_models)}
                </div>
                <div class="meta-item">
                    <strong>Database:</strong><br>
                    {self.captured_data['test_metadata']['database_url']}
                </div>
                <div class="meta-item">
                    <strong>Claude API:</strong><br>
                    {'Configured' if self.captured_data['test_metadata']['claude_api_key_configured'] else 'Missing'}
                </div>
            </div>
        </header>
        
        <div class="content">
            <section>
                <h2>Stage 0: PDF Extraction</h2>
                <div class="extraction-summary">
                    <div class="summary-card">
                        <div class="number">{self.captured_data.get('extraction_stage', {}).get('price_list_extraction', {}).get('total_entries', 0)}</div>
                        <div>Total Entries Extracted</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{self.captured_data.get('extraction_stage', {}).get('price_list_extraction', {}).get('target_entries_found', 0)}</div>
                        <div>Target Models Found</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{self.captured_data.get('extraction_stage', {}).get('price_list_extraction', {}).get('extraction_time_ms', 0):.0f}ms</div>
                        <div>Extraction Time</div>
                    </div>
                </div>
                
                <h4>Raw Extracted Data</h4>
                <div class="raw-entries">
                    <pre>{json.dumps(self.captured_data.get('extraction_stage', {}).get('raw_price_entries', []), indent=2)}</pre>
                </div>
            </section>
            
            <section>
                <h2>Stages 1-5: Pipeline Processing</h2>
                <div class="extraction-summary">
                    <div class="summary-card">
                        <div class="number">{self.captured_data.get('pipeline_stages', {}).get('summary', {}).get('products_successful', 0)}</div>
                        <div>Products Successful</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{self.captured_data.get('pipeline_stages', {}).get('summary', {}).get('products_failed', 0)}</div>
                        <div>Products Failed</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{self.captured_data.get('pipeline_stages', {}).get('summary', {}).get('processing_time_ms', 0):.0f}ms</div>
                        <div>Processing Time</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">${self.captured_data.get('pipeline_stages', {}).get('summary', {}).get('claude_cost', 0):.4f}</div>
                        <div>Claude Cost</div>
                    </div>
                </div>
                
                {product_cards if product_cards else '<div class="error-item">No products were successfully processed</div>'}
            </section>
            
            <section>
                <h2>Performance Metrics</h2>
                <div class="performance-grid">
                    <div class="perf-card">
                        <span class="label">Total Test Duration</span>
                        <span class="value">{perf.get('total_test_duration_ms', 0):.0f}ms</span>
                    </div>
                    <div class="perf-card">
                        <span class="label">PDF Extraction</span>
                        <span class="value">{perf.get('pdf_extraction_ms', 0):.0f}ms</span>
                    </div>
                    <div class="perf-card">
                        <span class="label">Pipeline Processing</span>
                        <span class="value">{perf.get('pipeline_processing_ms', 0):.0f}ms</span>
                    </div>
                    <div class="perf-card">
                        <span class="label">Database Operations</span>
                        <span class="value">{perf.get('database_operations_ms', 0):.0f}ms</span>
                    </div>
                    <div class="perf-card">
                        <span class="label">Claude Tokens</span>
                        <span class="value">{perf.get('claude_tokens', 0):,}</span>
                    </div>
                    <div class="perf-card">
                        <span class="label">Total Cost</span>
                        <span class="value">${perf.get('claude_cost_usd', 0):.4f}</span>
                    </div>
                </div>
            </section>
            
            <section>
                <h2>Errors and Warnings</h2>
                <div class="errors-section">
                    {errors_html}
                </div>
            </section>
        </div>
        
        <footer>
            <p>Blind E2E Test Complete - No predetermined outcomes, just facts</p>
            <p>Generated: {datetime.now():%Y-%m-%d %H:%M:%S}</p>
        </footer>
    </div>
</body>
</html>
"""


async def main():
    """Run the blind test"""
    test = BlindE2ETest()
    await test.run_blind_test()
    print("\n" + "="*80)
    print("BLIND TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())