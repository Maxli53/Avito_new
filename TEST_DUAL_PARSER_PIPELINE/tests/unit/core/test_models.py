"""
Unit tests for core data models
Tests ProductData, CatalogData, ValidationResult, MatchResult, PipelineStats, AvitoXMLData
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from core import (
    ProductData, CatalogData, ValidationResult, MatchResult, 
    PipelineStats, AvitoXMLData, PipelineStage
)
from tests.utils import data_validator, DataValidator


class TestProductData:
    """Test ProductData data model"""
    
    def test_product_data_creation_valid(self):
        """Test creating valid ProductData instance"""
        product = ProductData(
            model_code="TEST",
            brand="TestBrand",
            year=2024,
            malli="TestModel",
            paketti="TestPackage"
        )
        
        assert product.model_code == "TEST"
        assert product.brand == "TestBrand"
        assert product.year == 2024
        assert product.malli == "TestModel"
        assert product.paketti == "TestPackage"
        
        # Validate using our test utility
        data_validator.assert_valid_product_data(product)
    
    def test_product_data_minimal_valid(self):
        """Test creating ProductData with minimal required fields"""
        product = ProductData(
            model_code="MIN1",
            brand="Minimal",
            year=2024
        )
        
        assert product.model_code == "MIN1"
        assert product.brand == "Minimal"  
        assert product.year == 2024
        assert product.malli is None
        assert product.paketti is None
    
    def test_product_data_invalid_model_code_empty(self):
        """Test ProductData validation with empty model code"""
        with pytest.raises(ValueError, match="model_code must be 4 characters"):
            ProductData(
                model_code="",
                brand="Test",
                year=2024
            )
    
    def test_product_data_invalid_model_code_wrong_length(self):
        """Test ProductData validation with wrong model code length"""
        with pytest.raises(ValueError, match="model_code must be 4 characters"):
            ProductData(
                model_code="TOOLONG",
                brand="Test", 
                year=2024
            )
        
        with pytest.raises(ValueError, match="model_code must be 4 characters"):
            ProductData(
                model_code="SH",
                brand="Test",
                year=2024
            )
    
    def test_product_data_invalid_year_range(self):
        """Test ProductData validation with invalid year"""
        with pytest.raises(ValueError, match="Year must be between"):
            ProductData(
                model_code="OLD1",
                brand="Test",
                year=1999  # Too old
            )
        
        with pytest.raises(ValueError, match="Year must be between"):
            ProductData(
                model_code="FUT1", 
                brand="Test",
                year=2031  # Too far in future
            )
    
    def test_product_data_normalization(self):
        """Test that ProductData normalizes input data"""
        product = ProductData(
            model_code="test",  # Should be uppercased
            brand="  Test Brand  ",  # Should be stripped
            year=2024,
            malli="test model",  # Should be title cased
            vari="RED/blue"  # Should be normalized
        )
        
        assert product.model_code == "TEST"
        assert product.brand == "Test Brand"
        assert product.malli == "Test Model"
        assert product.vari == "Red/Blue"
    
    def test_product_data_serialization(self):
        """Test ProductData can be serialized to dict"""
        product = ProductData(
            model_code="SER1",
            brand="Serializable",
            year=2024,
            moottori="Test Engine"
        )
        
        as_dict = product.to_dict()
        
        assert isinstance(as_dict, dict)
        assert as_dict["model_code"] == "SER1"
        assert as_dict["brand"] == "Serializable"
        assert as_dict["year"] == 2024
        assert as_dict["moottori"] == "Test Engine"
    
    def test_product_data_from_dict(self):
        """Test creating ProductData from dictionary"""
        data = {
            "model_code": "DIC1",
            "brand": "Dictionary",
            "year": 2024,
            "malli": "From Dict"
        }
        
        product = ProductData.from_dict(data)
        
        assert product.model_code == "DIC1"
        assert product.brand == "Dictionary" 
        assert product.year == 2024
        assert product.malli == "From Dict"
    
    def test_product_data_equality(self):
        """Test ProductData equality comparison"""
        product1 = ProductData(model_code="EQU1", brand="Equal", year=2024)
        product2 = ProductData(model_code="EQU1", brand="Equal", year=2024)
        product3 = ProductData(model_code="DIF1", brand="Different", year=2024)
        
        assert product1 == product2
        assert product1 != product3
        assert hash(product1) == hash(product2)
        assert hash(product1) != hash(product3)


class TestCatalogData:
    """Test CatalogData data model"""
    
    def test_catalog_data_creation(self):
        """Test creating CatalogData instance"""
        catalog = CatalogData(
            model_family="TestFamily",
            brand="TestBrand",
            specifications={"engine": "Test Engine", "track": "3.0"},
            features=["Feature 1", "Feature 2", "Feature 3"]
        )
        
        assert catalog.model_family == "TestFamily"
        assert catalog.brand == "TestBrand"
        assert catalog.specifications["engine"] == "Test Engine"
        assert "Feature 1" in catalog.features
        assert len(catalog.features) == 3
    
    def test_catalog_data_minimal(self):
        """Test CatalogData with minimal required fields"""
        catalog = CatalogData(
            model_family="Minimal",
            brand="Test"
        )
        
        assert catalog.model_family == "Minimal"
        assert catalog.brand == "Test"
        assert catalog.specifications == {}
        assert catalog.features == []
    
    def test_catalog_data_matches_product(self):
        """Test CatalogData.matches_product method"""
        catalog = CatalogData(
            model_family="Summit",
            brand="Ski-Doo"
        )
        
        matching_product = ProductData(
            model_code="SUM1",
            brand="Ski-Doo",
            year=2024,
            malli="Summit X"
        )
        
        non_matching_product = ProductData(
            model_code="CAT1", 
            brand="Arctic Cat",
            year=2024,
            malli="Catalyst"
        )
        
        assert catalog.matches_product(matching_product) is True
        assert catalog.matches_product(non_matching_product) is False
    
    def test_catalog_data_get_specification(self):
        """Test getting specifications from catalog"""
        catalog = CatalogData(
            model_family="Test",
            brand="Test",
            specifications={
                "engine_type": "2-stroke",
                "displacement": "850cc",
                "track_width": "3.0"
            }
        )
        
        assert catalog.get_specification("engine_type") == "2-stroke"
        assert catalog.get_specification("displacement") == "850cc"
        assert catalog.get_specification("nonexistent") is None
        assert catalog.get_specification("nonexistent", "default") == "default"


class TestValidationResult:
    """Test ValidationResult data model"""
    
    def test_validation_result_success(self):
        """Test successful validation result"""
        result = ValidationResult(
            success=True,
            confidence_score=0.95,
            field_validations={"model_code": True, "brand": True}
        )
        
        assert result.success is True
        assert result.confidence_score == 0.95
        assert result.errors == []
        assert result.warnings == []
        assert result.field_validations["model_code"] is True
        
        data_validator.assert_valid_validation_result(result)
    
    def test_validation_result_failure(self):
        """Test failed validation result"""
        result = ValidationResult(
            success=False,
            confidence_score=0.3,
            errors=["Invalid model code", "Missing required field"]
        )
        
        assert result.success is False
        assert result.confidence_score == 0.3
        assert len(result.errors) == 2
        assert "Invalid model code" in result.errors
        
        data_validator.assert_valid_validation_result(result)
    
    def test_validation_result_add_error(self):
        """Test adding errors to validation result"""
        result = ValidationResult(success=True)
        
        result.add_error("Test error")
        
        assert result.success is False  # Should automatically set to False
        assert "Test error" in result.errors
    
    def test_validation_result_add_warning(self):
        """Test adding warnings to validation result"""
        result = ValidationResult(success=True)
        
        result.add_warning("Test warning")
        
        assert result.success is True  # Should remain True for warnings
        assert "Test warning" in result.warnings
    
    def test_validation_result_invalid_confidence_score(self):
        """Test ValidationResult with invalid confidence score"""
        with pytest.raises(ValueError, match="Confidence score must be between 0 and 1"):
            ValidationResult(success=True, confidence_score=1.5)
        
        with pytest.raises(ValueError, match="Confidence score must be between 0 and 1"):
            ValidationResult(success=True, confidence_score=-0.1)


class TestMatchResult:
    """Test MatchResult data model"""
    
    def test_match_result_successful(self):
        """Test successful match result"""
        result = MatchResult(
            success=True,
            confidence_score=0.94,
            matched_model="Summit X Expert 165",
            similarity_score=0.96,
            match_method="bert_semantic"
        )
        
        assert result.success is True
        assert result.confidence_score == 0.94
        assert result.matched_model == "Summit X Expert 165"
        assert result.similarity_score == 0.96
        assert result.match_method == "bert_semantic"
    
    def test_match_result_failed(self):
        """Test failed match result"""
        result = MatchResult(
            success=False,
            confidence_score=0.2,
            match_method="fuzzy_string"
        )
        
        assert result.success is False
        assert result.confidence_score == 0.2
        assert result.matched_model is None
        assert result.similarity_score is None
    
    def test_match_result_validation(self):
        """Test MatchResult validation"""
        with pytest.raises(ValueError, match="Confidence score must be between 0 and 1"):
            MatchResult(success=True, confidence_score=2.0)
        
        with pytest.raises(ValueError, match="Similarity score must be between 0 and 1"):
            MatchResult(success=True, confidence_score=0.9, similarity_score=1.5)


class TestPipelineStats:
    """Test PipelineStats data model"""
    
    def test_pipeline_stats_creation(self):
        """Test creating PipelineStats"""
        stats = PipelineStats(
            stage=PipelineStage.EXTRACTION,
            successful=8,
            failed=2,
            total_processed=10
        )
        
        assert stats.stage == PipelineStage.EXTRACTION
        assert stats.successful == 8
        assert stats.failed == 2
        assert stats.total_processed == 10
        assert stats.success_rate == 80.0
        
        data_validator.assert_valid_pipeline_stats(stats)
    
    def test_pipeline_stats_automatic_total(self):
        """Test PipelineStats automatically calculates total"""
        stats = PipelineStats(
            stage=PipelineStage.MATCHING,
            successful=5,
            failed=3
        )
        
        assert stats.total_processed == 8  # Should auto-calculate
        assert stats.success_rate == 62.5
    
    def test_pipeline_stats_timing(self):
        """Test PipelineStats timing functionality"""
        stats = PipelineStats(stage=PipelineStage.VALIDATION)
        
        # Start timing
        stats.start_time = datetime.now()
        
        # Simulate processing
        import time
        time.sleep(0.01)  # 10ms
        
        # End timing
        stats.end_time = datetime.now()
        
        assert stats.processing_time > 0
        assert stats.processing_time < 1.0  # Should be less than 1 second
    
    def test_pipeline_stats_zero_division(self):
        """Test PipelineStats handles zero division"""
        stats = PipelineStats(
            stage=PipelineStage.GENERATION,
            successful=0,
            failed=0,
            total_processed=0
        )
        
        assert stats.success_rate == 0.0
        data_validator.assert_valid_pipeline_stats(stats)


class TestAvitoXMLData:
    """Test AvitoXMLData data model"""
    
    def test_avito_xml_data_creation(self):
        """Test creating AvitoXMLData instance"""
        xml_data = AvitoXMLData(
            title="Test Snowmobile 2024",
            model_code="XML1",
            brand="TestBrand",
            year=2024,
            price=150000,
            description="Test snowmobile description",
            specifications={"engine": "Test Engine", "track": "3.0"}
        )
        
        assert xml_data.title == "Test Snowmobile 2024"
        assert xml_data.model_code == "XML1"
        assert xml_data.brand == "TestBrand"
        assert xml_data.year == 2024
        assert xml_data.price == 150000
        assert xml_data.description == "Test snowmobile description"
        assert xml_data.specifications["engine"] == "Test Engine"
    
    def test_avito_xml_data_validation_success(self):
        """Test AvitoXMLData validation with valid data"""
        xml_data = AvitoXMLData(
            title="Valid Snowmobile",
            model_code="VAL1",
            brand="Valid",
            year=2024,
            price=100000,
            description="Valid description"
        )
        
        result = xml_data.validate_required_fields()
        
        assert result.success is True
        assert len(result.errors) == 0
    
    def test_avito_xml_data_validation_failure(self):
        """Test AvitoXMLData validation with missing required fields"""
        xml_data = AvitoXMLData(
            title="",  # Empty title
            model_code="FAIL",
            brand="Test",
            year=2024
            # Missing price and description
        )
        
        result = xml_data.validate_required_fields()
        
        assert result.success is False
        assert len(result.errors) > 0
        assert any("title" in error.lower() for error in result.errors)
    
    def test_avito_xml_data_price_validation(self):
        """Test AvitoXMLData price validation"""
        # Valid price
        xml_data_valid = AvitoXMLData(
            title="Test",
            model_code="PRC1",
            brand="Test", 
            year=2024,
            price=50000,
            description="Test"
        )
        
        result_valid = xml_data_valid.validate_required_fields()
        assert result_valid.success is True
        
        # Invalid price (too low)
        xml_data_invalid = AvitoXMLData(
            title="Test",
            model_code="PRC2", 
            brand="Test",
            year=2024,
            price=0,  # Invalid price
            description="Test"
        )
        
        result_invalid = xml_data_invalid.validate_required_fields()
        assert result_invalid.success is False
        assert any("price" in error.lower() for error in result_invalid.errors)
    
    def test_avito_xml_data_to_dict(self):
        """Test AvitoXMLData serialization to dictionary"""
        xml_data = AvitoXMLData(
            title="Serializable Snowmobile",
            model_code="SER1",
            brand="Test",
            year=2024,
            price=75000,
            description="Test description"
        )
        
        as_dict = xml_data.to_dict()
        
        assert isinstance(as_dict, dict)
        assert as_dict["title"] == "Serializable Snowmobile"
        assert as_dict["model_code"] == "SER1" 
        assert as_dict["brand"] == "Test"
        assert as_dict["year"] == 2024
        assert as_dict["price"] == 75000


class TestDataModelIntegration:
    """Integration tests for data model interactions"""
    
    def test_product_to_xml_data_conversion(self):
        """Test converting ProductData to AvitoXMLData"""
        product = ProductData(
            model_code="CON1",
            brand="Conversion",
            year=2024,
            malli="Test Model",
            paketti="Test Package",
            moottori="Test Engine",
            vari="Test Color"
        )
        
        xml_data = AvitoXMLData.from_product_data(product)
        
        assert xml_data.model_code == product.model_code
        assert xml_data.brand == product.brand
        assert xml_data.year == product.year
        assert product.malli in xml_data.title
        assert product.moottori in xml_data.description
    
    def test_validation_result_aggregation(self):
        """Test aggregating multiple validation results"""
        results = [
            ValidationResult(success=True, confidence_score=0.95),
            ValidationResult(success=True, confidence_score=0.87),
            ValidationResult(success=False, confidence_score=0.3, errors=["Error 1"]),
            ValidationResult(success=True, confidence_score=0.91)
        ]
        
        aggregated = ValidationResult.aggregate_results(results)
        
        assert aggregated.success is False  # Should fail if any individual fails
        assert len(aggregated.errors) == 1
        assert aggregated.confidence_score == (0.95 + 0.87 + 0.3 + 0.91) / 4  # Average
    
    def test_pipeline_stats_accumulation(self):
        """Test accumulating pipeline statistics"""
        stats1 = PipelineStats(stage=PipelineStage.EXTRACTION, successful=5, failed=1)
        stats2 = PipelineStats(stage=PipelineStage.EXTRACTION, successful=3, failed=2) 
        
        combined = stats1 + stats2
        
        assert combined.successful == 8
        assert combined.failed == 3
        assert combined.total_processed == 11
        assert combined.success_rate == (8/11) * 100