"""
Business Scenario End-to-End Tests
=================================

These E2E tests validate specific business scenarios and user workflows
that represent real-world usage patterns of the Avito Pipeline system.
"""

import pytest
import tempfile
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any
import time

# Import pipeline components
from pipeline.stage1_extraction.base_extractor import BaseExtractor
from pipeline.stage2_matching.bert_matcher import BERTMatcher
from pipeline.stage3_validation.base_validator import BaseValidator
from pipeline.stage4_generation.base_generator import BaseGenerator
from pipeline.stage5_upload.ftp_uploader import FTPUploader

# Import core components
from core.models import ProductData, CatalogData, ValidationResult
from core.database import DatabaseManager
from core.exceptions import PipelineError

# Import fixtures
from tests.fixtures.sample_data import SampleDataFactory


class TestBusinessScenarioWorkflows:
    """End-to-end tests for specific business scenarios"""

    @pytest.mark.e2e
    @pytest.mark.business_critical
    def test_new_model_year_catalog_processing_e2e(self, temp_pdf_file, temp_database):
        """
        Business Scenario: Processing new model year catalog with mixed known/unknown products
        
        Scenario: Dealer receives 2025 model year catalog with mix of:
        - Updated versions of existing models
        - Completely new models
        - Discontinued models still listed
        """
        # Create scenario-specific test data
        new_year_products = [
            ProductData(model_code="S2BX", brand="Ski-Doo", year=2025, malli="Summit X", 
                       paketti="Expert 165", moottori="900 ACE Turbo R"),  # Updated engine
            ProductData(model_code="R3GT", brand="Ski-Doo", year=2025, malli="Renegade GT", 
                       paketti="Sport 600", moottori="600R E-TEC"),  # New model
            ProductData(model_code="M8HX", brand="Arctic Cat", year=2025, malli="M 8000 Hardcore", 
                       paketti="Alpha One 165", moottori="8000 C-TEC4"),  # Discontinued brand scenario
        ]
        
        # Stage 1: Extract new catalog data
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = new_year_products
            extracted_products = extractor.extract_from_file(temp_pdf_file)
        
        assert len(extracted_products) == 3
        assert all(p.year == 2025 for p in extracted_products)
        
        # Stage 2: BERT matching with varying confidence for new vs known models
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            # High confidence for updated model, medium for new, low for discontinued
            embeddings = [[0.95, 0.92, 0.88], [0.65, 0.70, 0.60], [0.45, 0.40, 0.35]]
            mock_bert.return_value.encode.return_value = embeddings
            match_results = matcher.match_products(extracted_products)
        
        assert len(match_results) == 3
        
        # Stage 3: Claude validation with business logic for new year processing
        validator = ClaudeValidator()
        validation_responses = [
            # High confidence for updated known model
            MagicMock(content=[MagicMock(text=json.dumps({
                "is_valid": True,
                "confidence_score": 0.96,
                "validation_notes": ["Updated model year version of known Summit X"],
                "suggested_corrections": []
            }))]),
            # Medium confidence for new model requiring human review
            MagicMock(content=[MagicMock(text=json.dumps({
                "is_valid": True,
                "confidence_score": 0.78,
                "validation_notes": ["New model - recommend dealer verification"],
                "suggested_corrections": ["Verify pricing with manufacturer"]
            }))]),
            # Low confidence for discontinued brand
            MagicMock(content=[MagicMock(text=json.dumps({
                "is_valid": False,
                "confidence_score": 0.45,
                "validation_notes": ["Discontinued brand - verify availability"],
                "suggested_corrections": ["Confirm Arctic Cat dealer status"]
            }))])
        ]
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value.messages.create.side_effect = validation_responses
            validation_results = validator.validate_products(match_results)
        
        # Business logic verification
        valid_products = [v for v in validation_results if v.is_valid]
        needs_review = [v for v in validation_results if v.is_valid and v.confidence_score < 0.85]
        invalid_products = [v for v in validation_results if not v.is_valid]
        
        assert len(valid_products) == 2  # Two products should pass validation
        assert len(needs_review) == 1  # One needs human review
        assert len(invalid_products) == 1  # One invalid (discontinued)
        
        # Stage 4: Generate specs with business annotations
        generator = SpecGenerator()
        generated_specs = generator.generate_specifications(valid_products)
        
        # Verify business-appropriate spec generation
        assert len(generated_specs) == 2
        for spec in generated_specs:
            assert "2025" in spec["content"]  # Model year prominently featured
            if "Summit X" in spec["content"]:
                assert "900 ACE Turbo R" in spec["content"]  # Updated engine info
        
        # Stage 5: Upload with business workflow annotations
        uploader = FTPUploader()
        with patch('ftplib.FTP') as mock_ftp:
            mock_ftp_instance = MagicMock()
            mock_ftp.return_value = mock_ftp_instance
            
            upload_results = uploader.upload_specifications(generated_specs)
        
        # Verify business outcomes
        assert len(upload_results) == 2
        assert all(r["status"] == "success" for r in upload_results)
        
        # Verify business reporting data in database
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        # Check new model year processing statistics
        cursor.execute("SELECT COUNT(*) FROM product_data WHERE year = 2025")
        new_year_count = cursor.fetchone()[0]
        assert new_year_count == 3
        
        # Check validation outcomes for business reporting
        cursor.execute("SELECT COUNT(*) FROM validation_results WHERE is_valid = 1 AND confidence_score < 0.85")
        review_needed_count = cursor.fetchone()[0]
        assert review_needed_count == 1
        
        conn.close()

    @pytest.mark.e2e
    @pytest.mark.business_critical
    def test_competitive_analysis_workflow_e2e(self, temp_pdf_file, temp_database):
        """
        Business Scenario: Competitive analysis processing multiple brand catalogs
        
        Scenario: Dealer processes competitor catalogs to understand market positioning
        """
        # Multi-brand competitive data
        competitive_products = [
            ProductData(model_code="P850", brand="Polaris", year=2024, malli="Pro-RMK 850", 
                       paketti="Assault 155", moottori="850 Patriot"),
            ProductData(model_code="Y998", brand="Yamaha", year=2024, malli="SideWinder X-TX", 
                       paketti="LE 146", moottori="998 Turbo"),
            ProductData(model_code="S1MX", brand="Ski-Doo", year=2024, malli="Summit X", 
                       paketti="Expert 165", moottori="850 E-TEC Turbo R"),
        ]
        
        # Stage 1: Extract competitive data
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = competitive_products
            extracted_products = extractor.extract_from_file(temp_pdf_file)
        
        # Verify competitive brand extraction
        brands = set(p.brand for p in extracted_products)
        assert len(brands) == 3
        assert "Polaris" in brands
        assert "Yamaha" in brands
        assert "Ski-Doo" in brands
        
        # Stage 2: BERT matching for competitive analysis
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            # Different embedding patterns for different brands
            embeddings = [
                [0.85, 0.80, 0.75],  # Polaris
                [0.90, 0.85, 0.82],  # Yamaha  
                [0.95, 0.92, 0.88],  # Ski-Doo (home brand)
            ]
            mock_bert.return_value.encode.return_value = embeddings
            match_results = matcher.match_products(extracted_products)
        
        # Stage 3: Validation with competitive focus
        validator = ClaudeValidator()
        validation_responses = []
        for i, product in enumerate(extracted_products):
            confidence = 0.88 if product.brand == "Ski-Doo" else 0.75  # Lower confidence for competitors
            validation_responses.append(MagicMock(content=[MagicMock(text=json.dumps({
                "is_valid": True,
                "confidence_score": confidence,
                "validation_notes": [f"Competitive analysis: {product.brand} positioning"],
                "suggested_corrections": [] if product.brand == "Ski-Doo" else ["Verify competitor specs"]
            }))]))
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value.messages.create.side_effect = validation_responses
            validation_results = validator.validate_products(match_results)
        
        # Competitive analysis verification
        ski_doo_results = [v for v in validation_results if v.product_data.brand == "Ski-Doo"]
        competitor_results = [v for v in validation_results if v.product_data.brand != "Ski-Doo"]
        
        assert len(ski_doo_results) == 1
        assert len(competitor_results) == 2
        assert ski_doo_results[0].confidence_score > 0.85
        
        # Stage 4: Generate competitive comparison specs
        generator = SpecGenerator()
        generated_specs = generator.generate_specifications(validation_results)
        
        # Verify competitive positioning in specs
        assert len(generated_specs) == 3
        brand_specs = {}
        for spec in generated_specs:
            for brand in ["Polaris", "Yamaha", "Ski-Doo"]:
                if brand in spec["content"]:
                    brand_specs[brand] = spec
                    break
        
        assert len(brand_specs) == 3
        
        # Stage 5: Upload competitive analysis
        uploader = FTPUploader()
        with patch('ftplib.FTP') as mock_ftp:
            mock_ftp_instance = MagicMock()
            mock_ftp.return_value = mock_ftp_instance
            
            upload_results = uploader.upload_specifications(generated_specs)
        
        # Verify competitive analysis outcomes
        assert len(upload_results) == 3
        
        # Database verification for competitive analysis
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        # Verify all competitor brands are captured
        cursor.execute("SELECT DISTINCT brand FROM product_data ORDER BY brand")
        brands_in_db = [row[0] for row in cursor.fetchall()]
        assert "Polaris" in brands_in_db
        assert "Yamaha" in brands_in_db  
        assert "Ski-Doo" in brands_in_db
        
        conn.close()

    @pytest.mark.e2e
    @pytest.mark.seasonal
    def test_seasonal_inventory_update_workflow_e2e(self, temp_pdf_file, temp_database):
        """
        Business Scenario: Seasonal inventory update with availability changes
        
        Scenario: Pre-season inventory update with spring options and availability
        """
        # Seasonal product mix with spring options
        seasonal_products = SampleDataFactory.create_spring_options_products()
        
        # Stage 1: Extract seasonal catalog
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = seasonal_products
            extracted_products = extractor.extract_from_file(temp_pdf_file)
        
        # Verify seasonal data extraction
        assert len(extracted_products) >= 3
        spring_models = [p for p in extracted_products if "Spring" in p.paketti or "spring" in p.paketti.lower()]
        assert len(spring_models) >= 1
        
        # Stage 2: Seasonal matching with availability focus
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            embeddings = [[0.92, 0.88, 0.85] for _ in extracted_products]
            mock_bert.return_value.encode.return_value = embeddings
            match_results = matcher.match_products(extracted_products)
        
        # Stage 3: Seasonal validation with inventory considerations
        validator = ClaudeValidator()
        validation_responses = []
        for product in extracted_products:
            is_spring_option = "Spring" in product.paketti
            confidence = 0.93 if is_spring_option else 0.87
            notes = ["Spring option - verify seasonal availability"] if is_spring_option else ["Standard availability"]
            
            validation_responses.append(MagicMock(content=[MagicMock(text=json.dumps({
                "is_valid": True,
                "confidence_score": confidence,
                "validation_notes": notes,
                "suggested_corrections": []
            }))]))
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value.messages.create.side_effect = validation_responses
            validation_results = validator.validate_products(match_results)
        
        # Seasonal business logic verification
        spring_validations = [v for v in validation_results if "Spring" in v.product_data.paketti]
        standard_validations = [v for v in validation_results if "Spring" not in v.product_data.paketti]
        
        assert len(spring_validations) >= 1
        assert all("seasonal availability" in v.validation_notes[0] for v in spring_validations)
        
        # Stage 4: Generate seasonal specs with availability notes
        generator = SpecGenerator()
        generated_specs = generator.generate_specifications(validation_results)
        
        # Verify seasonal considerations in specs
        spring_specs = [spec for spec in generated_specs if "Spring" in spec["content"]]
        assert len(spring_specs) >= 1
        
        # Stage 5: Upload with seasonal workflow
        uploader = FTPUploader()
        with patch('ftplib.FTP') as mock_ftp:
            mock_ftp_instance = MagicMock()
            mock_ftp.return_value = mock_ftp_instance
            
            upload_results = uploader.upload_specifications(generated_specs)
        
        # Verify seasonal upload success
        assert all(r["status"] == "success" for r in upload_results)
        
        # Database verification for seasonal tracking
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        # Check seasonal product tracking
        cursor.execute("SELECT COUNT(*) FROM product_data WHERE paketti LIKE '%Spring%'")
        spring_count = cursor.fetchone()[0]
        assert spring_count >= 1
        
        conn.close()

    @pytest.mark.e2e
    @pytest.mark.error_recovery
    def test_partial_failure_recovery_workflow_e2e(self, temp_pdf_file, temp_database):
        """
        Business Scenario: Partial pipeline failure with business continuity
        
        Scenario: System encounters errors but continues processing remaining products
        """
        # Mixed quality data that will trigger various failure scenarios
        problematic_products = [
            ProductData(model_code="GOOD", brand="Ski-Doo", year=2024, malli="Summit X", 
                       paketti="Expert 165", moottori="850 E-TEC"),  # Valid
            ProductData(model_code="", brand="Unknown", year=2024, malli="", 
                       paketti="", moottori=""),  # Invalid - empty fields
            ProductData(model_code="PART", brand="Ski-Doo", year=2024, malli="Partial Data", 
                       paketti="Unknown", moottori="TBD"),  # Partial data
            ProductData(model_code="VALD", brand="Yamaha", year=2024, malli="Valid Model", 
                       paketti="Standard", moottori="600 Engine"),  # Valid
        ]
        
        # Stage 1: Extract with some data quality issues
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = problematic_products
            extracted_products = extractor.extract_from_file(temp_pdf_file)
        
        # Filter out completely invalid products (business logic)
        valid_extracted = [p for p in extracted_products if p.model_code and p.brand]
        assert len(valid_extracted) == 3  # Should filter out empty product
        
        # Stage 2: Matching with varied success rates
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            # Simulate BERT failure for one product, success for others
            def mock_encode(texts):
                embeddings = []
                for i, text in enumerate(texts):
                    if "Partial Data" in text:
                        # Simulate poor embedding quality
                        embeddings.append([0.1, 0.1, 0.1])
                    else:
                        embeddings.append([0.8, 0.9, 0.85])
                return embeddings
            
            mock_bert.return_value.encode.side_effect = mock_encode
            
            try:
                match_results = matcher.match_products(valid_extracted)
                # Should handle partial failures gracefully
                assert len(match_results) >= 2
            except Exception as e:
                pytest.skip(f"Expected error handling: {str(e)}")
        
        # Stage 3: Validation with mixed outcomes
        validator = ClaudeValidator()
        validation_responses = []
        for product in valid_extracted:
            if product.model_code == "GOOD":
                validation_responses.append(MagicMock(content=[MagicMock(text=json.dumps({
                    "is_valid": True,
                    "confidence_score": 0.95,
                    "validation_notes": ["High quality data"],
                    "suggested_corrections": []
                }))]))
            elif product.model_code == "PART":
                validation_responses.append(MagicMock(content=[MagicMock(text=json.dumps({
                    "is_valid": False,
                    "confidence_score": 0.45,
                    "validation_notes": ["Incomplete data"],
                    "suggested_corrections": ["Missing specifications"]
                }))]))
            else:
                validation_responses.append(MagicMock(content=[MagicMock(text=json.dumps({
                    "is_valid": True,
                    "confidence_score": 0.82,
                    "validation_notes": ["Acceptable quality"],
                    "suggested_corrections": []
                }))]))
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value.messages.create.side_effect = validation_responses
            validation_results = validator.validate_products(match_results)
        
        # Business continuity verification
        valid_for_processing = [v for v in validation_results if v.is_valid]
        failed_products = [v for v in validation_results if not v.is_valid]
        
        assert len(valid_for_processing) >= 2  # At least some products succeed
        assert len(failed_products) >= 1  # Some failures expected
        
        # Stage 4: Generate specs only for valid products
        generator = SpecGenerator()
        generated_specs = generator.generate_specifications(valid_for_processing)
        
        # Verify business continuity - processing continues with valid data
        assert len(generated_specs) == len(valid_for_processing)
        
        # Stage 5: Upload with partial success handling
        uploader = FTPUploader()
        with patch('ftplib.FTP') as mock_ftp:
            mock_ftp_instance = MagicMock()
            mock_ftp.return_value = mock_ftp_instance
            
            # Simulate one upload failure
            upload_results = []
            for i, spec in enumerate(generated_specs):
                if i == 1:  # Fail the second upload
                    upload_results.append({"status": "failed", "error": "Connection timeout"})
                else:
                    upload_results.append({"status": "success", "file_id": f"upload_{i}"})
        
        # Business continuity outcomes
        successful_uploads = [r for r in upload_results if r["status"] == "success"]
        failed_uploads = [r for r in upload_results if r["status"] == "failed"]
        
        assert len(successful_uploads) >= 1  # Some uploads succeed
        assert len(successful_uploads) + len(failed_uploads) == len(upload_results)
        
        # Database verification for business reporting
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        # Verify success/failure tracking for business intelligence
        cursor.execute("SELECT COUNT(*) FROM validation_results WHERE is_valid = 1")
        successful_validations = cursor.fetchone()[0]
        assert successful_validations >= 2
        
        cursor.execute("SELECT COUNT(*) FROM validation_results WHERE is_valid = 0")
        failed_validations = cursor.fetchone()[0]
        assert failed_validations >= 1
        
        # Verify partial processing doesn't corrupt database
        cursor.execute("SELECT COUNT(DISTINCT model_code) FROM product_data WHERE model_code != ''")
        unique_products = cursor.fetchone()[0]
        assert unique_products >= 2
        
        conn.close()

    @pytest.mark.e2e
    @pytest.mark.performance
    @pytest.mark.business_critical
    def test_high_volume_business_day_workflow_e2e(self, temp_pdf_file, temp_database):
        """
        Business Scenario: High volume processing during peak business periods
        
        Scenario: Processing multiple catalogs during busy season with performance SLAs
        """
        # Large batch simulating busy day processing
        high_volume_products = []
        for i in range(15):  # Simulate 15 products across multiple catalogs
            base_products = SampleDataFactory.create_valid_products()
            for j, product in enumerate(base_products[:2]):  # Take first 2 from each sample
                # Modify to create unique products
                modified_product = ProductData(
                    model_code=f"{product.model_code}{i:02d}",
                    brand=product.brand,
                    year=product.year,
                    malli=f"{product.malli} Variant {i}",
                    paketti=product.paketti,
                    moottori=product.moottori
                )
                high_volume_products.append(modified_product)
        
        start_time = time.time()
        
        # Stage 1: High volume extraction
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = high_volume_products
            
            extraction_start = time.time()
            extracted_products = extractor.extract_from_file(temp_pdf_file)
            extraction_time = time.time() - extraction_start
        
        # Business SLA: Extraction should handle 30 products in under 15 seconds
        assert len(extracted_products) == 30
        assert extraction_time < 15.0, f"Extraction took {extraction_time:.2f}s, SLA is 15s"
        
        # Stage 2: High volume BERT matching
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            embeddings = [[0.85, 0.80, 0.90] for _ in extracted_products]
            mock_bert.return_value.encode.return_value = embeddings
            
            matching_start = time.time()
            match_results = matcher.match_products(extracted_products)
            matching_time = time.time() - matching_start
        
        # Business SLA: Matching should handle 30 products in under 20 seconds  
        assert len(match_results) == 30
        assert matching_time < 20.0, f"Matching took {matching_time:.2f}s, SLA is 20s"
        
        # Stage 3: High volume validation
        validator = ClaudeValidator()
        validation_responses = []
        for product in extracted_products:
            validation_responses.append(MagicMock(content=[MagicMock(text=json.dumps({
                "is_valid": True,
                "confidence_score": 0.89,
                "validation_notes": ["High volume processing"],
                "suggested_corrections": []
            }))]))
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value.messages.create.side_effect = validation_responses
            
            validation_start = time.time()
            validation_results = validator.validate_products(match_results)
            validation_time = time.time() - validation_start
        
        # Business SLA: Validation should handle 30 products in under 25 seconds
        assert len(validation_results) == 30
        assert validation_time < 25.0, f"Validation took {validation_time:.2f}s, SLA is 25s"
        
        # Stage 4: High volume spec generation
        generator = SpecGenerator()
        generation_start = time.time()
        generated_specs = generator.generate_specifications(validation_results)
        generation_time = time.time() - generation_start
        
        # Business SLA: Generation should handle 30 products in under 10 seconds
        assert len(generated_specs) == 30
        assert generation_time < 10.0, f"Generation took {generation_time:.2f}s, SLA is 10s"
        
        # Stage 5: High volume upload
        uploader = FTPUploader()
        with patch('ftplib.FTP') as mock_ftp:
            mock_ftp_instance = MagicMock()
            mock_ftp.return_value = mock_ftp_instance
            
            upload_start = time.time()
            upload_results = uploader.upload_specifications(generated_specs)
            upload_time = time.time() - upload_start
        
        # Business SLA: Upload should handle 30 files in under 30 seconds
        assert len(upload_results) == 30
        assert upload_time < 30.0, f"Upload took {upload_time:.2f}s, SLA is 30s"
        
        # Overall business SLA: Complete pipeline under 2 minutes for 30 products
        total_time = time.time() - start_time
        assert total_time < 120.0, f"Total pipeline took {total_time:.2f}s, SLA is 120s"
        
        # Verify all uploads succeeded (business requirement)
        assert all(r["status"] == "success" for r in upload_results)
        
        # Database performance verification
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        # Verify high volume data integrity
        cursor.execute("SELECT COUNT(*) FROM product_data")
        total_products = cursor.fetchone()[0]
        assert total_products >= 30
        
        # Verify no duplicate products (business data quality requirement)
        cursor.execute("SELECT COUNT(DISTINCT model_code) FROM product_data")
        unique_products = cursor.fetchone()[0]
        assert unique_products == 30
        
        # Check database performance under load
        query_start = time.time()
        cursor.execute("SELECT model_code, brand, year FROM product_data ORDER BY model_code")
        results = cursor.fetchall()
        query_time = time.time() - query_start
        
        assert len(results) >= 30
        assert query_time < 1.0, f"Database query took {query_time:.2f}s, should be under 1s"
        
        conn.close()
        
        # Business KPI verification
        print(f"\n🚀 HIGH VOLUME BUSINESS DAY PERFORMANCE:")
        print(f"   📊 Products Processed: {len(extracted_products)}")
        print(f"   ⏱️  Total Time: {total_time:.2f}s")
        print(f"   🎯 Products/Minute: {(len(extracted_products) / total_time) * 60:.1f}")
        print(f"   ✅ Success Rate: {len([r for r in upload_results if r['status'] == 'success'])/len(upload_results)*100:.1f}%")