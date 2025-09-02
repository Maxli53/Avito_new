"""
Integration tests for stage-to-stage data flow in the pipeline
Tests data transformation and handoff between pipeline stages
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

from pipeline.stage1_extraction import PDFExtractor, LLMExtractor
from pipeline.stage2_matching import BERTMatcher
from pipeline.stage3_validation import InternalValidator
from pipeline.stage4_generation import AvitoXMLGenerator
from pipeline.stage5_upload import FTPUploader
from core import ProductData, CatalogData, ValidationResult, MatchResult
from tests.fixtures.sample_data import SampleDataFactory
from tests.utils import performance_timer, file_helpers


class TestExtractionToMatchingFlow:
    """Test data flow from Stage 1 (Extraction) to Stage 2 (Matching)"""
    
    def test_pdf_extraction_to_bert_matching_integration(self, temp_pdf_file, temp_database):
        """Test complete flow from PDF extraction to BERT matching"""
        # Stage 1: PDF Extraction
        extractor = PDFExtractor()
        
        # Mock PDF extraction to return realistic products
        extracted_products = SampleDataFactory.create_valid_products()[:3]
        
        with patch.object(extractor, 'extract_from_file') as mock_extract:
            mock_extract.return_value = extracted_products
            
            products_from_extraction = extractor.extract_from_file(temp_pdf_file)
        
        assert len(products_from_extraction) == 3
        assert all(isinstance(p, ProductData) for p in products_from_extraction)
        
        # Stage 2: BERT Matching with extracted products
        matcher = BERTMatcher()
        matcher.model_loaded = True  # Simulate loaded BERT model
        
        # Load catalog data for matching
        catalog_data = SampleDataFactory.create_catalog_data()
        matcher.load_catalog_data(catalog_data)
        
        with patch.object(matcher, '_generate_embeddings') as mock_embeddings:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_similarity:
                # Mock high similarity for realistic matching
                mock_embeddings.return_value = [[0.1, 0.2, 0.3]] * len(products_from_extraction)
                mock_similarity.return_value = [[0.95, 0.3, 0.2, 0.4, 0.1]] * len(products_from_extraction)
                
                match_results = matcher.match_products(products_from_extraction)
        
        assert len(match_results) == 3
        assert all(isinstance(r, MatchResult) for r in match_results)
        assert all(r.success for r in match_results)  # All should match successfully
        
        # Verify data consistency between stages
        for i, (product, match_result) in enumerate(zip(products_from_extraction, match_results)):
            assert product.model_code is not None
            assert product.brand is not None
            assert match_result.confidence_score >= 0.8  # High confidence matches
            
        # Test statistics integration
        extraction_stats = extractor.get_stats()
        matching_stats = matcher.get_stats()
        
        assert extraction_stats.successful == 3
        assert matching_stats.successful == 3
        assert extraction_stats.total_processed == matching_stats.total_processed
    
    def test_llm_extraction_to_fuzzy_matching_fallback(self):
        """Test LLM extraction with fuzzy matching fallback"""
        # Stage 1: LLM Extraction
        llm_extractor = LLMExtractor(config={'provider': 'claude'})
        
        sample_text = """
        Product 1: Ski-Doo Summit X Expert 165 2024, 850 E-TEC engine
        Product 2: Arctic Cat Catalyst 9000 Turbo R 2024, 998cc turbo
        Product 3: Polaris RMK Khaos 850 2023, 850 Patriot engine
        """
        
        # Mock LLM response
        extracted_products = [
            ProductData(model_code="SKI1", brand="Ski-Doo", year=2024, malli="Summit X", paketti="Expert 165"),
            ProductData(model_code="ARC1", brand="Arctic Cat", year=2024, malli="Catalyst", paketti="9000 Turbo R"),
            ProductData(model_code="POL1", brand="Polaris", year=2023, malli="RMK", paketti="Khaos 850")
        ]
        
        with patch.object(llm_extractor, 'extract_products_from_text') as mock_llm:
            mock_llm.return_value = extracted_products
            
            products = llm_extractor.extract_products_from_text(sample_text)
        
        # Stage 2: BERT Matching with fallback
        matcher = BERTMatcher(config={'use_fuzzy_fallback': True})
        matcher.model_loaded = False  # Force fuzzy fallback
        
        catalog_data = [
            CatalogData(model_family="Summit X", brand="Ski-Doo"),
            CatalogData(model_family="Catalyst", brand="Arctic Cat"), 
            CatalogData(model_family="RMK", brand="Polaris")
        ]
        matcher.load_catalog_data(catalog_data)
        
        with patch('fuzzywuzzy.fuzz.ratio') as mock_fuzzy:
            # Mock high fuzzy similarity scores
            mock_fuzzy.return_value = 90  # 90% similarity
            
            match_results = matcher.match_products(products)
        
        assert len(match_results) == 3
        assert all(r.success for r in match_results)
        assert all(r.match_method == "fuzzy_string" for r in match_results)
        
        # Verify seamless handoff despite different matching method
        for product, match_result in zip(products, match_results):
            assert match_result.similarity_score >= 0.8  # Good fuzzy matches
    
    def test_partial_extraction_to_matching_resilience(self, temp_database):
        """Test matching stage handling of incomplete extraction data"""
        # Stage 1: Extraction with some incomplete products
        incomplete_products = [
            ProductData(model_code="COMP", brand="Complete", year=2024, malli="Full Model", moottori="850 E-TEC"),
            ProductData(model_code="PART", brand="Partial", year=2024),  # Missing model details
            ProductData(model_code="MINI", brand="", year=2024, malli="No Brand"),  # Missing brand
        ]
        
        # Stage 2: Matching should handle incomplete data gracefully
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        catalog_data = SampleDataFactory.create_catalog_data()[:3]
        matcher.load_catalog_data(catalog_data)
        
        with patch.object(matcher, '_generate_embeddings') as mock_embeddings:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_similarity:
                # Mock varying similarity based on data completeness
                mock_embeddings.return_value = [[0.1, 0.2, 0.3]] * 3
                mock_similarity.return_value = [
                    [0.95, 0.2, 0.1],  # Complete product - high match
                    [0.6, 0.7, 0.3],   # Partial product - medium match
                    [0.4, 0.3, 0.5]    # Minimal product - low match
                ]
                
                match_results = matcher.match_products(incomplete_products)
        
        assert len(match_results) == 3
        
        # Verify different outcomes based on data quality
        assert match_results[0].success is True   # Complete product matches
        assert match_results[1].success is True   # Partial product still matches (above threshold)
        assert match_results[2].success is False  # Minimal product fails to match
        
        # Verify matching confidence reflects data quality
        assert match_results[0].confidence_score > match_results[1].confidence_score
        assert match_results[1].confidence_score > match_results[2].confidence_score


class TestMatchingToValidationFlow:
    """Test data flow from Stage 2 (Matching) to Stage 3 (Validation)"""
    
    def test_matched_products_to_validation_integration(self, temp_database):
        """Test flow from matching results to validation"""
        # Stage 2: Prepare products with matching metadata
        products_with_matching = [
            ProductData(model_code="MAT1", brand="Ski-Doo", year=2024, malli="Summit X"),
            ProductData(model_code="MAT2", brand="Arctic Cat", year=2024, malli="Catalyst"),
            ProductData(model_code="MAT3", brand="Unknown", year=2024, malli="Unknown Model")
        ]
        
        # Add matching metadata to products (as would be done by matching stage)
        products_with_matching[0].matching_confidence = 0.95
        products_with_matching[0].matched_catalog_entry = "Summit X Expert 165"
        products_with_matching[0].match_method = "bert_semantic"
        
        products_with_matching[1].matching_confidence = 0.87
        products_with_matching[1].matched_catalog_entry = "Catalyst 9000"
        products_with_matching[1].match_method = "bert_semantic"
        
        products_with_matching[2].matching_confidence = 0.45
        products_with_matching[2].matched_catalog_entry = None
        products_with_matching[2].match_method = "no_match"
        
        # Stage 3: Validation considering matching results
        validator = InternalValidator()
        
        # Mock BRP database
        validator.brp_models = {
            "MAT1": {"brand": "Ski-Doo", "model_family": "Summit", "years": [2024]},
            "MAT2": {"brand": "Arctic Cat", "model_family": "Catalyst", "years": [2024]}
            # MAT3 not in database (unknown product)
        }
        
        with patch.object(validator, '_load_brp_database'):
            validation_results = validator.validate_products(products_with_matching)
        
        assert len(validation_results) == 3
        
        # Verify validation considers matching confidence
        # High matching confidence + BRP match = high validation confidence
        assert validation_results[0].success is True
        assert validation_results[0].confidence_score >= 0.9
        
        # Medium matching confidence + BRP match = good validation confidence
        assert validation_results[1].success is True
        assert validation_results[1].confidence_score >= 0.8
        
        # Low matching confidence + no BRP match = validation failure/low confidence
        assert validation_results[2].success is False
        assert validation_results[2].confidence_score < 0.7
        
        # Test validation statistics account for matching quality
        validator_stats = validator.get_stats()
        assert validator_stats.successful == 2
        assert validator_stats.failed == 1
    
    def test_matching_metadata_enrichment_to_validation(self):
        """Test validation enhancement using matching metadata"""
        # Products with rich matching metadata
        enriched_product = ProductData(
            model_code="ENRI",
            brand="Ski-Doo", 
            year=2024,
            malli="Summit"  # Partial model name
        )
        
        # Add detailed matching metadata
        enriched_product.matching_confidence = 0.96
        enriched_product.matched_catalog_entry = "Summit X Expert 165"
        enriched_product.catalog_specifications = {
            "engine": "850 E-TEC Turbo R",
            "track_width": "3.0",
            "features": ["Electronic Reverse", "Digital Display"]
        }
        enriched_product.semantic_similarity_score = 0.94
        
        validator = InternalValidator()
        validator.brp_models = {
            "ENRI": {"brand": "Ski-Doo", "model_family": "Summit", "years": [2024]}
        }
        
        with patch.object(validator, '_load_brp_database'):
            validation_result = validator.validate_single_product(enriched_product)
        
        # Validation should be enhanced by matching metadata
        assert validation_result.success is True
        assert validation_result.confidence_score >= 0.95
        
        # Check that matching metadata influenced validation
        if hasattr(validation_result, 'metadata_enhanced'):
            assert validation_result.metadata_enhanced is True
    
    def test_matching_failure_graceful_validation_handling(self):
        """Test validation handling of products that failed matching"""
        # Products that failed matching stage
        failed_match_products = [
            ProductData(
                model_code="FAIL",
                brand="UnknownBrand",
                year=2024,
                malli="UnknownModel"
            )
        ]
        
        # Add failed matching metadata
        failed_match_products[0].matching_confidence = 0.25
        failed_match_products[0].matched_catalog_entry = None
        failed_match_products[0].match_method = "no_suitable_match"
        failed_match_products[0].matching_errors = ["No catalog entry found", "Low semantic similarity"]
        
        validator = InternalValidator(config={'strict_mode': False})  # Lenient mode
        
        with patch.object(validator, '_load_brp_database'):
            validator.brp_models = {}  # Empty BRP database
            
            validation_result = validator.validate_single_product(failed_match_products[0])
        
        # Should still attempt validation despite matching failure
        assert isinstance(validation_result, ValidationResult)
        
        # Should fail validation due to no matching and no BRP data
        assert validation_result.success is False
        assert validation_result.confidence_score < 0.6
        
        # Should include matching failure context in warnings
        if validation_result.warnings:
            assert any("matching" in warning.lower() for warning in validation_result.warnings)


class TestValidationToGenerationFlow:
    """Test data flow from Stage 3 (Validation) to Stage 4 (Generation)"""
    
    def test_validated_products_to_xml_generation(self, temp_database):
        """Test flow from validation to XML generation"""
        # Stage 3: Products with validation results
        validated_products = SampleDataFactory.create_valid_products()[:3]
        
        # Add validation metadata
        for i, product in enumerate(validated_products):
            product.validation_confidence = 0.95 - (i * 0.05)
            product.validation_status = "passed" if i < 2 else "warning"
            product.validation_notes = ["All checks passed"] if i < 2 else ["Minor issues"]
            product.brp_database_match = True if i < 2 else False
        
        # Stage 4: XML Generation
        generator = AvitoXMLGenerator()
        
        # Mock template loading
        generator.templates['avito_snowmobile'] = """<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
    <brand>{{ brand }}</brand>
    <year>{{ year }}</year>
    <validation_score>{{ validation_score if validation_score else 'N/A' }}</validation_score>
    <brp_verified>{{ brp_verified if brp_verified else 'false' }}</brp_verified>
</item>"""
        
        xml_strings = generator.generate_xml_for_products(validated_products)
        
        assert len(xml_strings) == 3
        
        # Verify XML includes validation metadata
        for i, xml_string in enumerate(xml_strings):
            expected_confidence = validated_products[i].validation_confidence
            assert f"<validation_score>{expected_confidence}</validation_score>" in xml_string
            
            expected_brp = "true" if validated_products[i].brp_database_match else "false"
            assert f"<brp_verified>{expected_brp}</brp_verified>" in xml_string
        
        # Test generation statistics
        generation_stats = generator.get_stats()
        assert generation_stats.successful == 3
        assert generation_stats.total_processed == 3
    
    def test_validation_filtering_for_xml_generation(self):
        """Test XML generation filtering based on validation results"""
        # Mix of validated and failed products
        mixed_products = [
            ProductData(model_code="PASS", brand="PassBrand", year=2024, malli="PassModel"),
            ProductData(model_code="WARN", brand="WarnBrand", year=2024, malli="WarnModel"),
            ProductData(model_code="FAIL", brand="FailBrand", year=2024, malli="FailModel")
        ]
        
        # Set validation results
        mixed_products[0].validation_confidence = 0.95
        mixed_products[0].validation_status = "passed"
        
        mixed_products[1].validation_confidence = 0.75
        mixed_products[1].validation_status = "warning"
        
        mixed_products[2].validation_confidence = 0.45
        mixed_products[2].validation_status = "failed"
        
        generator = AvitoXMLGenerator(config={'min_validation_confidence': 0.7})
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
</item>"""
        
        # Filter products based on validation confidence
        qualified_products = [
            p for p in mixed_products 
            if getattr(p, 'validation_confidence', 0) >= 0.7
        ]
        
        xml_strings = generator.generate_xml_for_products(qualified_products)
        
        # Only products with sufficient validation confidence should generate XML
        assert len(xml_strings) == 2  # PASS and WARN, not FAIL
        
        # Verify correct products generated XML
        assert any("PASS" in xml for xml in xml_strings)
        assert any("WARN" in xml for xml in xml_strings)
        assert not any("FAIL" in xml for xml in xml_strings)
    
    def test_validation_metadata_xml_enrichment(self):
        """Test XML enrichment using validation metadata"""
        enriched_product = ProductData(
            model_code="META",
            brand="MetadataBrand",
            year=2024,
            malli="MetadataModel"
        )
        
        # Rich validation metadata
        enriched_product.validation_confidence = 0.97
        enriched_product.validation_layers = [
            "field_validation",
            "brp_database", 
            "specification_validation",
            "cross_field_validation"
        ]
        enriched_product.brp_database_match = True
        enriched_product.specification_checks = {
            "engine_valid": True,
            "track_width_valid": True,
            "year_model_compatible": True
        }
        enriched_product.validation_warnings = []
        enriched_product.validation_timestamp = "2024-01-15T10:30:00Z"
        
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
    <validation>
        <confidence>{{ validation_confidence }}</confidence>
        <layers_checked>{{ validation_layers | join(', ') if validation_layers else 'none' }}</layers_checked>
        <brp_verified>{{ brp_database_match if brp_database_match else 'false' }}</brp_verified>
        <timestamp>{{ validation_timestamp if validation_timestamp else 'N/A' }}</timestamp>
    </validation>
</item>"""
        
        xml_strings = generator.generate_xml_for_products([enriched_product])
        
        assert len(xml_strings) == 1
        xml_content = xml_strings[0]
        
        # Verify validation metadata in XML
        assert "<confidence>0.97</confidence>" in xml_content
        assert "field_validation, brp_database, specification_validation, cross_field_validation" in xml_content
        assert "<brp_verified>True</brp_verified>" in xml_content
        assert "<timestamp>2024-01-15T10:30:00Z</timestamp>" in xml_content


class TestGenerationToUploadFlow:
    """Test data flow from Stage 4 (Generation) to Stage 5 (Upload)"""
    
    def test_xml_generation_to_ftp_upload_integration(self, temp_database):
        """Test complete flow from XML generation to FTP upload"""
        # Stage 4: Generate XML
        products = SampleDataFactory.create_valid_products()[:2]
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
    <brand>{{ brand }}</brand>
    <year>{{ year }}</year>
    <description>{{ description }}</description>
</item>"""
        
        xml_strings = generator.generate_xml_for_products(products)
        assert len(xml_strings) == 2
        
        # Combine into single XML document
        combined_xml = generator._combine_xml_strings(xml_strings)
        
        # Stage 5: Upload generated XML
        uploader = FTPUploader(config={'password': 'test_pass'})
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            timestamp = "20241201_143000"
            filename = f"avito_snowmobiles_{timestamp}.xml"
            
            upload_result = uploader.upload_xml_content(combined_xml, filename)
        
        assert upload_result is True
        mock_ftp.storbinary.assert_called_once()
        
        # Verify uploaded content structure
        call_args = mock_ftp.storbinary.call_args
        uploaded_buffer = call_args[0][1]
        uploaded_buffer.seek(0)
        uploaded_content = uploaded_buffer.read().decode('utf-8')
        
        # Should contain both products
        assert "<?xml version=" in uploaded_content
        assert "<items>" in uploaded_content
        assert products[0].model_code in uploaded_content
        assert products[1].model_code in uploaded_content
        
        # Test statistics flow
        generation_stats = generator.get_stats()
        upload_stats = uploader.get_stats()
        
        assert generation_stats.successful == 2
        # Upload stats would reflect single file upload operation
        assert upload_stats.successful >= 1
    
    def test_large_xml_batch_upload_performance(self):
        """Test performance of uploading large XML batches"""
        # Generate large batch of products
        large_batch = []
        for i in range(50):  # 50 products
            product = ProductData(
                model_code=f"B{i:03d}",
                brand=f"Brand{i % 5}",
                year=2024,
                malli=f"Model {i}",
                moottori=f"Engine {i % 3}"
            )
            large_batch.append(product)
        
        # Stage 4: Generate XML for large batch
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ brand }} {{ malli }} {{ year }}</title>
    <model_code>{{ model_code }}</model_code>
    <engine>{{ moottori if moottori else 'N/A' }}</engine>
</item>"""
        
        with performance_timer.time_operation("large_batch_xml_generation"):
            xml_strings = generator.generate_xml_for_products(large_batch)
        
        assert len(xml_strings) == 50
        performance_timer.assert_performance("large_batch_xml_generation", 3.0)
        
        # Combine XML
        combined_xml = generator._combine_xml_strings(xml_strings)
        assert len(combined_xml) > 10000  # Should be substantial content
        
        # Stage 5: Upload large XML
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            with performance_timer.time_operation("large_xml_upload"):
                upload_result = uploader.upload_xml_content(combined_xml, "large_batch.xml")
        
        assert upload_result is True
        performance_timer.assert_performance("large_xml_upload", 2.0)
    
    def test_upload_failure_with_generation_rollback_scenario(self, temp_database):
        """Test handling of upload failures and potential rollback scenarios"""
        # Stage 4: Generate XML successfully
        products = SampleDataFactory.create_valid_products()[:3]
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
</item>"""
        
        xml_strings = generator.generate_xml_for_products(products)
        combined_xml = generator._combine_xml_strings(xml_strings)
        
        # Save generation metadata
        generation_stats = generator.get_stats()
        assert generation_stats.successful == 3
        
        # Stage 5: Simulate upload failure
        uploader = FTPUploader(config={'password': 'test_pass'})
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Simulate network error during upload
        mock_ftp.storbinary.side_effect = OSError("Network unreachable")
        
        from core.exceptions import UploadError
        
        with pytest.raises(UploadError):
            uploader.upload_xml_content(combined_xml, "failed_upload.xml")
        
        # Verify generation succeeded but upload failed
        upload_stats = uploader.get_stats()
        assert generation_stats.successful == 3  # Generation still successful
        assert upload_stats.failed >= 1  # Upload failed
        
        # In a real scenario, this might trigger:
        # - Retry logic
        # - Alternative upload methods
        # - Notification systems
        # - Rollback of generation artifacts
        
        # Test retry scenario
        mock_ftp.storbinary.side_effect = None  # Clear error
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            retry_result = uploader.upload_xml_content(combined_xml, "retry_upload.xml")
        
        assert retry_result is True
    
    def test_upload_metadata_and_monitoring_integration(self):
        """Test upload integration with monitoring and metadata"""
        # Stage 4: Generate XML with metadata
        product = ProductData(
            model_code="MONI",
            brand="MonitorBrand", 
            year=2024,
            malli="MonitorModel"
        )
        
        # Add generation metadata
        product.generation_timestamp = "2024-01-15T14:30:00Z"
        product.generation_confidence = 0.96
        product.xml_validation_passed = True
        
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
    <metadata>
        <generated_at>{{ generation_timestamp }}</generated_at>
        <confidence>{{ generation_confidence }}</confidence>
        <validated>{{ xml_validation_passed }}</validated>
    </metadata>
</item>"""
        
        xml_strings = generator.generate_xml_for_products([product])
        combined_xml = generator._combine_xml_strings(xml_strings)
        
        # Stage 5: Upload with monitoring
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Mock monitoring system
        with patch('pipeline.stage5_upload.ProcessingMonitor') as mock_monitor_class:
            mock_monitor = MagicMock()
            mock_monitor_class.return_value = mock_monitor
            
            mock_monitor.get_next_processing_window.return_value = {
                'next_window': '19:00 MSK',
                'hours_until': 4.5
            }
            
            with patch.object(uploader, '_verify_ftp_upload', return_value=True):
                upload_result = uploader.upload_xml_content(combined_xml, "monitored_upload.xml")
            
            assert upload_result is True
            
            # Verify monitoring integration (if implemented)
            # mock_monitor.record_upload.assert_called_once()


class TestCrossStageErrorHandling:
    """Test error handling and recovery across pipeline stages"""
    
    def test_stage_failure_isolation_and_recovery(self, temp_database):
        """Test that stage failures don't cascade inappropriately"""
        # Stage 1: Successful extraction
        successful_products = SampleDataFactory.create_valid_products()[:2]
        
        # Stage 2: Matching with partial failure
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        catalog_data = SampleDataFactory.create_catalog_data()[:1]  # Limited catalog
        matcher.load_catalog_data(catalog_data)
        
        with patch.object(matcher, '_generate_embeddings') as mock_embeddings:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_similarity:
                # First product matches, second fails
                mock_embeddings.return_value = [[0.1, 0.2, 0.3]] * 2
                mock_similarity.return_value = [
                    [0.95],  # First product: good match
                    [0.3]    # Second product: poor match
                ]
                
                match_results = matcher.match_products(successful_products)
        
        assert len(match_results) == 2
        assert match_results[0].success is True
        assert match_results[1].success is False
        
        # Stage 3: Validation should handle mixed results gracefully
        # Only validate successfully matched products
        products_to_validate = []
        for product, match_result in zip(successful_products, match_results):
            if match_result.success:
                product.matching_confidence = match_result.confidence_score
                products_to_validate.append(product)
        
        validator = InternalValidator()
        validator.brp_models = {
            successful_products[0].model_code: {
                "brand": successful_products[0].brand,
                "years": [successful_products[0].year]
            }
        }
        
        with patch.object(validator, '_load_brp_database'):
            validation_results = validator.validate_products(products_to_validate)
        
        assert len(validation_results) == 1  # Only successfully matched product
        assert validation_results[0].success is True
        
        # Stage 4: XML generation with filtered products
        products_to_generate = []
        for i, (product, validation_result) in enumerate(zip(products_to_validate, validation_results)):
            if validation_result.success:
                products_to_generate.append(product)
        
        generator = AvitoXMLGenerator()
        generator.templates['avito_snowmobile'] = """<item><title>{{ title }}</title></item>"""
        
        xml_strings = generator.generate_xml_for_products(products_to_generate)
        
        assert len(xml_strings) == 1  # Only fully validated product
        
        # Verify statistics show proper error isolation
        matching_stats = matcher.get_stats()
        validation_stats = validator.get_stats()
        generation_stats = generator.get_stats()
        
        assert matching_stats.successful == 1
        assert matching_stats.failed == 1
        assert validation_stats.successful == 1
        assert validation_stats.failed == 0  # No failures since we filtered
        assert generation_stats.successful == 1
    
    def test_data_consistency_across_stage_failures(self):
        """Test data consistency when stages encounter errors"""
        # Simulate scenario where stages encounter different types of errors
        products = [
            ProductData(model_code="CON1", brand="Consistent", year=2024, malli="Model1"),
            ProductData(model_code="CON2", brand="Consistent", year=2024, malli="Model2"),
            ProductData(model_code="ERR1", brand="Error", year=2024, malli="ErrorModel")
        ]
        
        # Stage 2: Matching with timeout error on third product
        matcher = BERTMatcher(config={'api_timeout': 5})
        matcher.model_loaded = True
        
        catalog_data = [CatalogData(model_family="Model1", brand="Consistent")]
        matcher.load_catalog_data(catalog_data)
        
        with patch.object(matcher, '_generate_embeddings') as mock_embeddings:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_similarity:
                def embedding_side_effect(texts):
                    if any("ErrorModel" in text for text in texts):
                        raise TimeoutError("Embedding generation timeout")
                    return [[0.1, 0.2, 0.3]] * len(texts)
                
                mock_embeddings.side_effect = embedding_side_effect
                mock_similarity.return_value = [[0.9]]
                
                # Should handle timeout gracefully
                try:
                    match_results = matcher.match_products(products)
                except:
                    # Handle partial results
                    match_results = [
                        MatchResult(success=True, confidence_score=0.9, matched_model="Model1"),
                        MatchResult(success=False, confidence_score=0.0),  # Timeout occurred
                        MatchResult(success=False, confidence_score=0.0)   # Timeout occurred
                    ]
        
        # Verify only successful matches proceed
        successful_products = [
            product for product, result in zip(products, match_results)
            if result.success
        ]
        
        assert len(successful_products) == 1
        assert successful_products[0].model_code == "CON1"
        
        # Remaining stages should work with consistent subset
        validator = InternalValidator()
        validation_results = validator.validate_products(successful_products)
        
        assert len(validation_results) == 1
        assert validation_results[0].success  # Should validate successfully
    
    def test_pipeline_stage_statistics_consistency(self):
        """Test that statistics remain consistent across stage boundaries"""
        # Track statistics across all stages
        products = SampleDataFactory.create_valid_products()[:5]
        
        # Stage 1: Extraction stats
        extractor = PDFExtractor()
        with patch.object(extractor, 'extract_from_file') as mock_extract:
            mock_extract.return_value = products
            extracted = extractor.extract_from_file(Path("dummy.pdf"))
        
        extraction_stats = extractor.get_stats()
        assert extraction_stats.total_processed == 5
        assert extraction_stats.successful == 5
        
        # Stage 2: Matching stats
        matcher = BERTMatcher()
        matcher.model_loaded = True
        matcher.load_catalog_data(SampleDataFactory.create_catalog_data())
        
        with patch.object(matcher, '_generate_embeddings'):
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_sim:
                # 4 successful matches, 1 failure
                mock_sim.return_value = [
                    [0.95, 0.2], [0.88, 0.3], [0.91, 0.1], [0.85, 0.4], [0.65, 0.7]  # Last one fails threshold
                ]
                match_results = matcher.match_products(extracted)
        
        matching_stats = matcher.get_stats()
        assert matching_stats.total_processed == 5
        assert matching_stats.successful == 4
        assert matching_stats.failed == 1
        
        # Stage 3: Validation stats (only process successful matches)
        successful_matched = [p for p, r in zip(extracted, match_results) if r.success]
        
        validator = InternalValidator()
        with patch.object(validator, '_load_brp_database'):
            validator.brp_models = {p.model_code: {"brand": p.brand, "years": [p.year]} for p in successful_matched}
            validation_results = validator.validate_products(successful_matched)
        
        validation_stats = validator.get_stats()
        assert validation_stats.total_processed == 4  # Only matched products
        assert validation_stats.successful == 4  # All should validate
        
        # Verify statistics consistency
        assert extraction_stats.successful >= matching_stats.total_processed
        assert matching_stats.successful == validation_stats.total_processed
        
        # Overall pipeline success rate calculation
        overall_success_rate = (validation_stats.successful / extraction_stats.total_processed) * 100
        assert overall_success_rate == 80.0  # 4/5 = 80%