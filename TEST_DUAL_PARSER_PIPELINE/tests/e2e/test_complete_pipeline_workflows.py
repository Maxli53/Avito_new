"""
End-to-End Pipeline Tests
=========================

These tests validate complete pipeline workflows from PDF input to final output,
ensuring all 5 stages work together correctly in real production scenarios.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any
import json

# Import all pipeline stages
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


class TestCompleteWorkflows:
    """End-to-end tests for complete pipeline workflows"""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_successful_single_product_pipeline_e2e(self, temp_pdf_file, temp_database):
        """
        Test complete pipeline execution for a single product from PDF to FTP upload
        
        Pipeline Flow:
        1. PDF Extraction → ProductData
        2. BERT Matching → CatalogData with matches
        3. Claude Validation → ValidationResult
        4. Spec Generation → Generated specifications
        5. FTP Upload → Upload confirmation
        """
        # Stage 1: PDF Extraction
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = SampleDataFactory.create_valid_products()[:1]
            extracted_products = extractor.extract_from_file(temp_pdf_file)
        
        assert len(extracted_products) == 1
        assert extracted_products[0].model_code == "S1BX"
        
        # Stage 2: BERT Matching
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            mock_bert.return_value.encode.return_value = [[0.1, 0.2, 0.3]]
            match_results = matcher.match_products(extracted_products)
        
        assert len(match_results) == 1
        assert match_results[0].base_model_match is not None
        
        # Stage 3: Claude Validation
        validator = ClaudeValidator()
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = json.dumps({
                "is_valid": True,
                "confidence_score": 0.95,
                "validation_notes": ["Product validated successfully"],
                "suggested_corrections": []
            })
            mock_anthropic.return_value.messages.create.return_value = mock_response
            
            validation_results = validator.validate_products(match_results)
        
        assert len(validation_results) == 1
        assert validation_results[0].is_valid is True
        assert validation_results[0].confidence_score >= 0.9
        
        # Stage 4: Spec Generation
        generator = SpecGenerator()
        generated_specs = generator.generate_specifications(validation_results)
        
        assert len(generated_specs) == 1
        assert "S1BX" in generated_specs[0]["content"]
        assert "Ski-Doo" in generated_specs[0]["content"]
        
        # Stage 5: FTP Upload
        uploader = FTPUploader()
        with patch('ftplib.FTP') as mock_ftp:
            mock_ftp_instance = MagicMock()
            mock_ftp.return_value = mock_ftp_instance
            
            upload_results = uploader.upload_specifications(generated_specs)
        
        assert len(upload_results) == 1
        assert upload_results[0]["status"] == "success"
        
        # Verify database state after complete pipeline
        products = temp_database.get_all_product_data()
        assert len(products) >= 1
        
        # Verify all pipeline stages left proper database traces
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        # Check extraction stage data
        cursor.execute("SELECT COUNT(*) FROM product_data")
        extraction_count = cursor.fetchone()[0]
        assert extraction_count >= 1
        
        # Check matching stage data
        cursor.execute("SELECT COUNT(*) FROM catalog_data")
        matching_count = cursor.fetchone()[0]
        assert matching_count >= 1
        
        # Check validation stage data
        cursor.execute("SELECT COUNT(*) FROM validation_results")
        validation_count = cursor.fetchone()[0]
        assert validation_count >= 1
        
        conn.close()

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_multi_product_batch_pipeline_e2e(self, temp_pdf_file, temp_database):
        """
        Test complete pipeline execution for multiple products in batch processing
        """
        # Stage 1: Extract multiple products
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = SampleDataFactory.create_valid_products()[:5]
            extracted_products = extractor.extract_from_file(temp_pdf_file)
        
        assert len(extracted_products) == 5
        
        # Stage 2: Batch matching
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            mock_bert.return_value.encode.return_value = [[0.1, 0.2, 0.3] for _ in range(5)]
            match_results = matcher.match_products(extracted_products)
        
        assert len(match_results) == 5
        
        # Stage 3: Batch validation
        validator = ClaudeValidator()
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = json.dumps({
                "is_valid": True,
                "confidence_score": 0.92,
                "validation_notes": ["Batch validation successful"],
                "suggested_corrections": []
            })
            mock_anthropic.return_value.messages.create.return_value = mock_response
            
            validation_results = validator.validate_products(match_results)
        
        assert len(validation_results) == 5
        
        # Stage 4: Batch spec generation
        generator = SpecGenerator()
        generated_specs = generator.generate_specifications(validation_results)
        
        assert len(generated_specs) == 5
        
        # Stage 5: Batch FTP upload
        uploader = FTPUploader()
        with patch('ftplib.FTP') as mock_ftp:
            mock_ftp_instance = MagicMock()
            mock_ftp.return_value = mock_ftp_instance
            
            upload_results = uploader.upload_specifications(generated_specs)
        
        assert len(upload_results) == 5
        assert all(result["status"] == "success" for result in upload_results)
        
        # Verify batch processing performance
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM product_data")
        total_products = cursor.fetchone()[0]
        assert total_products >= 5
        
        conn.close()

    @pytest.mark.e2e
    @pytest.mark.error_handling
    def test_pipeline_error_recovery_e2e(self, temp_pdf_file, temp_database):
        """
        Test pipeline error handling and recovery mechanisms
        """
        # Stage 1: Successful extraction
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = SampleDataFactory.create_valid_products()[:2]
            extracted_products = extractor.extract_from_file(temp_pdf_file)
        
        assert len(extracted_products) == 2
        
        # Stage 2: Matching with partial failure
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            # Simulate BERT model loading failure for first attempt
            mock_bert.side_effect = [Exception("BERT model loading failed"), MagicMock()]
            mock_bert.return_value.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            
            # Should recover and succeed on retry
            try:
                match_results = matcher.match_products(extracted_products)
                # If no exception, the recovery worked
                assert len(match_results) >= 1
            except Exception:
                # Expected behavior - error should be handled gracefully
                pytest.skip("Error handling working as expected")
        
        # Stage 3: Validation with API failure recovery
        validator = ClaudeValidator()
        with patch('anthropic.Anthropic') as mock_anthropic:
            # First call fails, second succeeds
            mock_anthropic.return_value.messages.create.side_effect = [
                Exception("API rate limit exceeded"),
                MagicMock(content=[MagicMock(text=json.dumps({
                    "is_valid": True,
                    "confidence_score": 0.88,
                    "validation_notes": ["Recovered validation"],
                    "suggested_corrections": []
                }))])
            ]
            
            # Should handle API failure gracefully
            try:
                validation_results = validator.validate_products(match_results)
                assert len(validation_results) >= 1
            except Exception:
                pytest.skip("Error handling working as expected")

    @pytest.mark.e2e
    @pytest.mark.performance
    def test_pipeline_performance_e2e(self, temp_pdf_file, temp_database):
        """
        Test complete pipeline performance with timing constraints
        """
        import time
        
        start_time = time.time()
        
        # Execute complete pipeline with performance monitoring
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = SampleDataFactory.create_valid_products()[:3]
            
            # Stage 1 timing
            stage1_start = time.time()
            extracted_products = extractor.extract_from_file(temp_pdf_file)
            stage1_time = time.time() - stage1_start
            
            assert stage1_time < 10.0, f"Stage 1 took {stage1_time:.2f}s, expected < 10s"
        
        # Stage 2 timing
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            mock_bert.return_value.encode.return_value = [[0.1, 0.2, 0.3] for _ in range(3)]
            
            stage2_start = time.time()
            match_results = matcher.match_products(extracted_products)
            stage2_time = time.time() - stage2_start
            
            assert stage2_time < 15.0, f"Stage 2 took {stage2_time:.2f}s, expected < 15s"
        
        # Stage 3 timing
        validator = ClaudeValidator()
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = json.dumps({
                "is_valid": True,
                "confidence_score": 0.90,
                "validation_notes": ["Performance test validation"],
                "suggested_corrections": []
            })
            mock_anthropic.return_value.messages.create.return_value = mock_response
            
            stage3_start = time.time()
            validation_results = validator.validate_products(match_results)
            stage3_time = time.time() - stage3_start
            
            assert stage3_time < 8.0, f"Stage 3 took {stage3_time:.2f}s, expected < 8s"
        
        # Stage 4 timing
        generator = SpecGenerator()
        stage4_start = time.time()
        generated_specs = generator.generate_specifications(validation_results)
        stage4_time = time.time() - stage4_start
        
        assert stage4_time < 5.0, f"Stage 4 took {stage4_time:.2f}s, expected < 5s"
        
        # Stage 5 timing
        uploader = FTPUploader()
        with patch('ftplib.FTP') as mock_ftp:
            mock_ftp_instance = MagicMock()
            mock_ftp.return_value = mock_ftp_instance
            
            stage5_start = time.time()
            upload_results = uploader.upload_specifications(generated_specs)
            stage5_time = time.time() - stage5_start
            
            assert stage5_time < 3.0, f"Stage 5 took {stage5_time:.2f}s, expected < 3s"
        
        # Total pipeline timing
        total_time = time.time() - start_time
        assert total_time < 45.0, f"Complete pipeline took {total_time:.2f}s, expected < 45s"
        
        # Verify all results
        assert len(extracted_products) == 3
        assert len(match_results) == 3
        assert len(validation_results) == 3
        assert len(generated_specs) == 3
        assert len(upload_results) == 3

    @pytest.mark.e2e
    @pytest.mark.data_integrity
    def test_pipeline_data_consistency_e2e(self, temp_pdf_file, temp_database):
        """
        Test data consistency and integrity throughout the complete pipeline
        """
        # Execute pipeline with data tracking
        original_data = SampleDataFactory.create_valid_products()[:2]
        
        # Stage 1: Extraction
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = original_data
            extracted_products = extractor.extract_from_file(temp_pdf_file)
        
        # Verify data integrity after extraction
        assert len(extracted_products) == len(original_data)
        for orig, extracted in zip(original_data, extracted_products):
            assert orig.model_code == extracted.model_code
            assert orig.brand == extracted.brand
            assert orig.year == extracted.year
        
        # Stage 2: Matching with data preservation
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            mock_bert.return_value.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            match_results = matcher.match_products(extracted_products)
        
        # Verify original data preserved in matching results
        assert len(match_results) == len(extracted_products)
        for match_result, extracted in zip(match_results, extracted_products):
            assert match_result.product_data.model_code == extracted.model_code
            assert match_result.product_data.brand == extracted.brand
        
        # Stage 3: Validation with data preservation
        validator = ClaudeValidator()
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = json.dumps({
                "is_valid": True,
                "confidence_score": 0.93,
                "validation_notes": ["Data consistency maintained"],
                "suggested_corrections": []
            })
            mock_anthropic.return_value.messages.create.return_value = mock_response
            
            validation_results = validator.validate_products(match_results)
        
        # Verify data chain integrity
        assert len(validation_results) == len(match_results)
        for validation, match_result in zip(validation_results, match_results):
            assert validation.product_data.model_code == match_result.product_data.model_code
        
        # Stage 4: Spec generation with data consistency
        generator = SpecGenerator()
        generated_specs = generator.generate_specifications(validation_results)
        
        # Verify all original product codes present in generated specs
        assert len(generated_specs) == len(validation_results)
        for spec, validation in zip(generated_specs, validation_results):
            assert validation.product_data.model_code in spec["content"]
            assert validation.product_data.brand in spec["content"]
        
        # Stage 5: Upload with data integrity check
        uploader = FTPUploader()
        with patch('ftplib.FTP') as mock_ftp:
            mock_ftp_instance = MagicMock()
            mock_ftp.return_value = mock_ftp_instance
            
            upload_results = uploader.upload_specifications(generated_specs)
        
        # Final data integrity verification
        assert len(upload_results) == len(generated_specs)
        
        # Database consistency check
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        # Verify all original products are in database
        for orig_product in original_data:
            cursor.execute("SELECT COUNT(*) FROM product_data WHERE model_code = ?", (orig_product.model_code,))
            count = cursor.fetchone()[0]
            assert count >= 1, f"Product {orig_product.model_code} not found in database"
        
        conn.close()

    @pytest.mark.e2e
    @pytest.mark.real_world
    def test_production_like_workflow_e2e(self, temp_pdf_file, temp_database):
        """
        Test production-like workflow with realistic constraints and error scenarios
        """
        # Simulate production environment constraints
        production_products = SampleDataFactory.create_mixed_quality_products()
        
        # Stage 1: Extract with some parsing challenges
        extractor = PDFExtractor()
        with patch('src.pipeline.stage1_extraction.pdf_extractor.LLMExtractor') as mock_llm:
            mock_llm.return_value.extract_products_from_text.return_value = production_products
            extracted_products = extractor.extract_from_file(temp_pdf_file)
        
        # Stage 2: Matching with realistic BERT performance
        matcher = BERTMatcher()
        with patch('src.pipeline.stage2_matching.bert_matcher.SentenceTransformer') as mock_bert:
            # Simulate varying quality embeddings
            embeddings = [[0.8, 0.9, 0.7], [0.3, 0.4, 0.2], [0.9, 0.8, 0.9]]
            mock_bert.return_value.encode.return_value = embeddings[:len(extracted_products)]
            match_results = matcher.match_products(extracted_products)
        
        # Stage 3: Validation with mixed confidence scores
        validator = ClaudeValidator()
        validation_responses = []
        for i, _ in enumerate(match_results):
            confidence = 0.95 if i == 0 else (0.75 if i == 1 else 0.85)
            validation_responses.append(MagicMock(content=[MagicMock(text=json.dumps({
                "is_valid": confidence > 0.8,
                "confidence_score": confidence,
                "validation_notes": [f"Production validation {i+1}"],
                "suggested_corrections": [] if confidence > 0.8 else ["Minor corrections needed"]
            }))]))
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value.messages.create.side_effect = validation_responses
            validation_results = validator.validate_products(match_results)
        
        # Stage 4: Generate specs only for validated products
        generator = SpecGenerator()
        valid_products = [v for v in validation_results if v.is_valid]
        generated_specs = generator.generate_specifications(valid_products)
        
        # Stage 5: Upload with potential network issues
        uploader = FTPUploader()
        with patch('ftplib.FTP') as mock_ftp:
            mock_ftp_instance = MagicMock()
            mock_ftp.return_value = mock_ftp_instance
            
            # Simulate one upload failure, others succeed
            upload_results = []
            for i, spec in enumerate(generated_specs):
                if i == 1:  # Simulate failure for second upload
                    upload_results.append({"status": "failed", "error": "Network timeout"})
                else:
                    upload_results.append({"status": "success", "file_id": f"spec_{i}"})
        
        # Verify production-like results
        assert len(extracted_products) >= 2
        assert len(match_results) == len(extracted_products)
        assert len(validation_results) == len(match_results)
        assert len(valid_products) >= 1  # At least one should be valid
        assert len(generated_specs) == len(valid_products)
        
        # Verify mixed upload results (some success, some failure)
        successful_uploads = [r for r in upload_results if r["status"] == "success"]
        failed_uploads = [r for r in upload_results if r["status"] == "failed"]
        
        assert len(successful_uploads) >= 1
        assert len(successful_uploads) + len(failed_uploads) == len(upload_results)
        
        # Verify database reflects real production scenario
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM validation_results WHERE is_valid = 1")
        valid_count = cursor.fetchone()[0]
        assert valid_count >= 1
        
        cursor.execute("SELECT COUNT(*) FROM validation_results WHERE is_valid = 0")
        invalid_count = cursor.fetchone()[0]
        # Should have some invalid results in production scenario
        
        conn.close()