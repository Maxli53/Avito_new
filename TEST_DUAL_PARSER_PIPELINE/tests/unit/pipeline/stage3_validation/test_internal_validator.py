"""
Unit tests for internal validation functionality
Tests InternalValidator class and 4-layer validation system
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from pipeline.stage3_validation import InternalValidator
from core import ProductData, ValidationResult, PipelineStats
from core.exceptions import ValidationError
from tests.utils import performance_timer, data_validator
from tests.fixtures.sample_data import SampleDataFactory


class TestInternalValidatorInitialization:
    """Test InternalValidator initialization and configuration"""
    
    def test_internal_validator_creation_default_config(self):
        """Test creating InternalValidator with default configuration"""
        validator = InternalValidator()
        
        assert isinstance(validator, InternalValidator)
        assert validator.config is not None
        assert validator.config['strict_mode'] is False
        assert validator.config['confidence_threshold'] == 0.7
        assert validator.stats.stage == 'validation'
    
    def test_internal_validator_custom_config(self):
        """Test InternalValidator with custom configuration"""
        custom_config = {
            'strict_mode': True,
            'confidence_threshold': 0.85,
            'enable_brp_database': True,
            'brp_database_path': 'custom_brp.db',
            'field_validation_rules': {'model_code': {'min_length': 4, 'max_length': 4}},
            'price_validation': {
                'min_price': 5000,
                'max_price': 500000,
                'currency': 'EUR'
            }
        }
        
        validator = InternalValidator(config=custom_config)
        
        assert validator.config['strict_mode'] is True
        assert validator.config['confidence_threshold'] == 0.85
        assert validator.config['enable_brp_database'] is True
        assert validator.config['brp_database_path'] == 'custom_brp.db'
    
    def test_brp_database_loading(self):
        """Test BRP model database loading"""
        config = {'enable_brp_database': True}
        validator = InternalValidator(config=config)
        
        with patch.object(validator, '_load_brp_database') as mock_load:
            mock_load.return_value = True
            
            result = validator._initialize_brp_database()
            
            assert result is True
            mock_load.assert_called_once()


class TestFieldValidation:
    """Test Layer 1: Field-level validation"""
    
    def test_validate_model_code_valid(self):
        """Test valid model code validation"""
        validator = InternalValidator()
        
        valid_codes = ["SKDO", "ARCT", "POLA", "YAMA", "LYNX"]
        
        for code in valid_codes:
            result = validator._validate_model_code(code)
            assert result.success is True
            assert result.confidence_score == 1.0
    
    def test_validate_model_code_invalid_length(self):
        """Test model code validation with invalid length"""
        validator = InternalValidator()
        
        invalid_codes = ["", "AB", "TOOLONG", "12345678"]
        
        for code in invalid_codes:
            result = validator._validate_model_code(code)
            assert result.success is False
            assert any("length" in error.lower() for error in result.errors)
    
    def test_validate_model_code_invalid_format(self):
        """Test model code validation with invalid format"""
        validator = InternalValidator()
        
        invalid_formats = ["12AB", "AB12", "!@#$", "   "]
        
        for code in invalid_formats:
            result = validator._validate_model_code(code)
            # Should either fail format validation or pass with low confidence
            if not result.success:
                assert any("format" in error.lower() for error in result.errors)
            else:
                assert result.confidence_score < 0.8
    
    def test_validate_brand_valid(self):
        """Test valid brand name validation"""
        validator = InternalValidator()
        
        valid_brands = [
            "Ski-Doo", "Arctic Cat", "Polaris", "Yamaha", "Lynx",
            "BRP", "Bombardier", "Can-Am"
        ]
        
        for brand in valid_brands:
            result = validator._validate_brand(brand)
            assert result.success is True
            assert result.confidence_score >= 0.9
    
    def test_validate_brand_unknown(self):
        """Test validation of unknown brand names"""
        validator = InternalValidator()
        
        unknown_brands = ["UnknownBrand", "FakeBrand", "TestBrand"]
        
        for brand in unknown_brands:
            result = validator._validate_brand(brand)
            # Should pass but with lower confidence
            assert result.success is True
            assert result.confidence_score < 0.8
            assert any("unknown brand" in warning.lower() for warning in result.warnings)
    
    def test_validate_year_valid_range(self):
        """Test valid year range validation"""
        validator = InternalValidator()
        
        valid_years = [2020, 2021, 2022, 2023, 2024, 2025]
        
        for year in valid_years:
            result = validator._validate_year(year)
            assert result.success is True
            assert result.confidence_score == 1.0
    
    def test_validate_year_invalid_range(self):
        """Test year validation outside valid range"""
        validator = InternalValidator()
        
        invalid_years = [1999, 2000, 2030, 2050]
        
        for year in invalid_years:
            result = validator._validate_year(year)
            assert result.success is False
            assert any("year" in error.lower() and "range" in error.lower() for error in result.errors)
    
    def test_validate_price_valid_ranges(self):
        """Test price validation within valid ranges"""
        validator = InternalValidator()
        
        valid_prices = [5000, 15000, 25000, 50000, 75000]
        
        for price in valid_prices:
            result = validator._validate_price(price)
            assert result.success is True
            assert result.confidence_score >= 0.9
    
    def test_validate_price_invalid_ranges(self):
        """Test price validation outside reasonable ranges"""
        validator = InternalValidator()
        
        # Too low
        result_low = validator._validate_price(100)
        assert result_low.success is False
        assert any("too low" in error.lower() for error in result_low.errors)
        
        # Too high
        result_high = validator._validate_price(1000000)
        assert result_high.success is False
        assert any("too high" in error.lower() for error in result_high.errors)
        
        # Negative
        result_negative = validator._validate_price(-5000)
        assert result_negative.success is False
        assert any("negative" in error.lower() for error in result_negative.errors)
    
    def test_validate_text_fields(self):
        """Test text field validation (malli, paketti, etc.)"""
        validator = InternalValidator()
        
        # Valid text fields
        valid_texts = ["Summit X", "Expert 165", "850 E-TEC", "Team Arctic Green"]
        
        for text in valid_texts:
            result = validator._validate_text_field(text, "malli")
            assert result.success is True
            assert result.confidence_score >= 0.8
        
        # Invalid text fields
        invalid_texts = ["", "   ", "a", "x" * 200]  # Empty, whitespace, too short, too long
        
        for text in invalid_texts:
            result = validator._validate_text_field(text, "malli")
            if not result.success:
                assert len(result.errors) > 0
            else:
                assert result.confidence_score < 0.7


class TestBRPModelValidation:
    """Test Layer 2: BRP model database validation"""
    
    def test_brp_database_exact_match(self):
        """Test exact match in BRP model database"""
        validator = InternalValidator()
        validator.brp_models = {
            "SKDO": {"brand": "Ski-Doo", "model_family": "Summit", "years": [2023, 2024]},
            "ARCT": {"brand": "Arctic Cat", "model_family": "Catalyst", "years": [2024, 2025]}
        }
        
        product = ProductData(
            model_code="SKDO",
            brand="Ski-Doo", 
            year=2024,
            malli="Summit X"
        )
        
        result = validator._validate_against_brp_database(product)
        
        assert result.success is True
        assert result.confidence_score >= 0.95
        assert "exact match" in result.validation_notes.lower()
    
    def test_brp_database_partial_match(self):
        """Test partial match in BRP model database"""
        validator = InternalValidator()
        validator.brp_models = {
            "SKDO": {"brand": "Ski-Doo", "model_family": "Summit", "years": [2022, 2023]}
        }
        
        product = ProductData(
            model_code="SKDO",
            brand="Ski-Doo",
            year=2024,  # Year not in database
            malli="Summit X"
        )
        
        result = validator._validate_against_brp_database(product)
        
        assert result.success is True  # Partial match still passes
        assert result.confidence_score < 0.95
        assert any("year mismatch" in warning.lower() for warning in result.warnings)
    
    def test_brp_database_no_match(self):
        """Test no match in BRP model database"""
        validator = InternalValidator()
        validator.brp_models = {
            "SKDO": {"brand": "Ski-Doo", "model_family": "Summit", "years": [2024]}
        }
        
        product = ProductData(
            model_code="UNKN",  # Unknown model code
            brand="Unknown Brand",
            year=2024
        )
        
        result = validator._validate_against_brp_database(product)
        
        assert result.success is False
        assert result.confidence_score < 0.5
        assert any("not found" in error.lower() for error in result.errors)
    
    def test_brp_database_fuzzy_matching(self):
        """Test fuzzy matching in BRP database for close matches"""
        validator = InternalValidator()
        validator.brp_models = {
            "SKDO": {"brand": "Ski-Doo", "model_family": "Summit", "years": [2024]},
            "SKID": {"brand": "Ski-Doo", "model_family": "Summit", "years": [2024]}
        }
        
        product = ProductData(
            model_code="SKDI",  # Close to SKDO/SKID but not exact
            brand="Ski-Doo",
            year=2024
        )
        
        result = validator._validate_against_brp_database(product)
        
        # Should find close matches and suggest corrections
        if result.success:
            assert result.confidence_score < 0.9
            assert any("similar" in warning.lower() for warning in result.warnings)
        else:
            assert any("similar models found" in error.lower() for error in result.errors)
    
    def test_brp_database_brand_mismatch(self):
        """Test BRP database validation with brand mismatch"""
        validator = InternalValidator()
        validator.brp_models = {
            "TEST": {"brand": "Ski-Doo", "model_family": "Summit", "years": [2024]}
        }
        
        product = ProductData(
            model_code="TEST",
            brand="Arctic Cat",  # Wrong brand
            year=2024
        )
        
        result = validator._validate_against_brp_database(product)
        
        assert result.success is False
        assert any("brand mismatch" in error.lower() for error in result.errors)
        assert result.confidence_score < 0.5


class TestSpecificationValidation:
    """Test Layer 3: Technical specification validation"""
    
    def test_validate_engine_specifications(self):
        """Test engine specification validation"""
        validator = InternalValidator()
        
        # Valid engine specifications
        valid_engines = [
            "850 E-TEC", "600R E-TEC", "998cc Turbo", "4-TEC 1049cc",
            "850 Patriot", "998 Turbo", "Rotax 600"
        ]
        
        for engine in valid_engines:
            result = validator._validate_engine_specification(engine)
            assert result.success is True
            assert result.confidence_score >= 0.8
        
        # Invalid engine specifications
        invalid_engines = ["Unknown Engine", "1000000cc", "InvalidSpec"]
        
        for engine in invalid_engines:
            result = validator._validate_engine_specification(engine)
            if not result.success:
                assert len(result.errors) > 0
            else:
                assert result.confidence_score < 0.7
    
    def test_validate_track_specifications(self):
        """Test track width specification validation"""
        validator = InternalValidator()
        
        # Valid track widths
        valid_tracks = ["2.0", "2.25", "2.5", "2.6", "2.75", "3.0"]
        
        for track in valid_tracks:
            result = validator._validate_track_specification(track)
            assert result.success is True
            assert result.confidence_score >= 0.9
        
        # Invalid track widths
        invalid_tracks = ["1.0", "5.0", "invalid", ""]
        
        for track in invalid_tracks:
            result = validator._validate_track_specification(track)
            assert result.success is False
            assert any("track width" in error.lower() for error in result.errors)
    
    def test_validate_starter_types(self):
        """Test starter type validation"""
        validator = InternalValidator()
        
        # Valid starter types
        valid_starters = ["Electric", "Pull", "Manual", "E-Start", "Recoil"]
        
        for starter in valid_starters:
            result = validator._validate_starter_type(starter)
            assert result.success is True
            assert result.confidence_score >= 0.9
        
        # Invalid starter types
        invalid_starters = ["InvalidStarter", "UnknownType", ""]
        
        for starter in invalid_starters:
            result = validator._validate_starter_type(starter)
            if not result.success:
                assert any("starter" in error.lower() for error in result.errors)
            else:
                assert result.confidence_score < 0.8
    
    def test_validate_gauge_types(self):
        """Test gauge/display type validation"""
        validator = InternalValidator()
        
        # Valid gauge types
        valid_gauges = [
            "Digital", "Analog", "LCD", "7\" Touch", "10.25\" Digital",
            "Multi-Information", "TFT Display"
        ]
        
        for gauge in valid_gauges:
            result = validator._validate_gauge_type(gauge)
            assert result.success is True
            assert result.confidence_score >= 0.8
    
    def test_validate_color_specifications(self):
        """Test color specification validation"""
        validator = InternalValidator()
        
        # Valid colors
        valid_colors = [
            "White", "Black", "Red", "Blue", "Green", "Yellow",
            "White/Black", "Team Arctic Green", "Lime Squeeze",
            "Octane Blue/Black", "Team Yamaha Blue"
        ]
        
        for color in valid_colors:
            result = validator._validate_color_specification(color)
            assert result.success is True
            assert result.confidence_score >= 0.8


class TestCrossFieldValidation:
    """Test Layer 4: Cross-field validation and business logic"""
    
    def test_validate_brand_model_consistency(self):
        """Test brand and model consistency validation"""
        validator = InternalValidator()
        
        # Valid brand-model combinations
        valid_combinations = [
            ("Ski-Doo", "Summit X"),
            ("Arctic Cat", "Catalyst"),
            ("Polaris", "RMK"),
            ("Yamaha", "Sidewinder"),
            ("Lynx", "Ranger")
        ]
        
        for brand, model in valid_combinations:
            product = ProductData(model_code="TEST", brand=brand, year=2024, malli=model)
            result = validator._validate_brand_model_consistency(product)
            assert result.success is True
            assert result.confidence_score >= 0.9
        
        # Invalid brand-model combinations
        invalid_combinations = [
            ("Ski-Doo", "Catalyst"),  # Arctic Cat model
            ("Polaris", "Sidewinder"),  # Yamaha model
            ("Yamaha", "Summit X")  # Ski-Doo model
        ]
        
        for brand, model in invalid_combinations:
            product = ProductData(model_code="TEST", brand=brand, year=2024, malli=model)
            result = validator._validate_brand_model_consistency(product)
            assert result.success is False
            assert any("inconsistent" in error.lower() for error in result.errors)
    
    def test_validate_year_model_compatibility(self):
        """Test year and model compatibility"""
        validator = InternalValidator()
        validator.model_year_matrix = {
            "Summit X": [2020, 2021, 2022, 2023, 2024],
            "Catalyst": [2024, 2025],  # New model
            "Legacy Model": [2018, 2019, 2020]  # Discontinued
        }
        
        # Valid year-model combinations
        product_valid = ProductData(
            model_code="TEST", brand="Ski-Doo", year=2024, malli="Summit X"
        )
        result = validator._validate_year_model_compatibility(product_valid)
        assert result.success is True
        
        # Invalid: New model with old year
        product_invalid = ProductData(
            model_code="TEST", brand="Arctic Cat", year=2020, malli="Catalyst"
        )
        result = validator._validate_year_model_compatibility(product_invalid)
        assert result.success is False
        assert any("not available" in error.lower() for error in result.errors)
    
    def test_validate_engine_track_compatibility(self):
        """Test engine and track width compatibility"""
        validator = InternalValidator()
        
        # Valid engine-track combinations
        valid_combo = ProductData(
            model_code="TEST", brand="Test", year=2024,
            moottori="850 E-TEC", telamatto="3.0"  # High power with wide track
        )
        result = validator._validate_engine_track_compatibility(valid_combo)
        assert result.success is True
        
        # Invalid: High power engine with narrow track
        invalid_combo = ProductData(
            model_code="TEST", brand="Test", year=2024,
            moottori="998 Turbo", telamatto="2.0"  # Very powerful with narrow track
        )
        result = validator._validate_engine_track_compatibility(invalid_combo)
        if not result.success:
            assert any("compatibility" in error.lower() for error in result.errors)
        else:
            assert result.confidence_score < 0.8  # Lower confidence
    
    def test_validate_price_specification_alignment(self):
        """Test price and specification alignment"""
        validator = InternalValidator()
        
        # High-spec product with appropriate high price
        high_spec_product = ProductData(
            model_code="TEST", brand="Test", year=2024,
            malli="Premium Model", moottori="998 Turbo",
            telamatto="3.0", kaynnistin="Electric"
        )
        
        # Should accept higher price for premium specs
        result = validator._validate_price_specification_alignment(high_spec_product, 45000)
        assert result.success is True
        assert result.confidence_score >= 0.8
        
        # Basic product with very high price (suspicious)
        basic_product = ProductData(
            model_code="TEST", brand="Test", year=2020,
            malli="Basic Model", moottori="600cc",
            telamatto="2.0"
        )
        
        result = validator._validate_price_specification_alignment(basic_product, 50000)
        if not result.success:
            assert any("price too high" in error.lower() for error in result.errors)
        else:
            assert result.confidence_score < 0.7


class TestValidationRuleEngine:
    """Test configurable validation rule engine"""
    
    def test_custom_validation_rules(self):
        """Test custom validation rules configuration"""
        custom_rules = {
            'model_code': {
                'required': True,
                'min_length': 3,
                'max_length': 5,
                'pattern': r'^[A-Z]{3,5}$'
            },
            'year': {
                'required': True,
                'min_value': 2015,
                'max_value': 2026
            },
            'price': {
                'min_value': 3000,
                'max_value': 100000,
                'currency': 'EUR'
            }
        }
        
        config = {'field_validation_rules': custom_rules}
        validator = InternalValidator(config=config)
        
        # Test custom model code rule
        valid_product = ProductData(model_code="CUST", brand="Test", year=2024)
        result = validator._validate_with_custom_rules(valid_product)
        
        assert result.success is True
        
        # Test rule violation
        invalid_product = ProductData(model_code="TOOLONG", brand="Test", year=2024)
        result = validator._validate_with_custom_rules(invalid_product)
        
        assert result.success is False
        assert any("max_length" in error.lower() for error in result.errors)
    
    def test_conditional_validation_rules(self):
        """Test conditional validation rules"""
        conditional_rules = {
            'if_brand_skidoo': {
                'condition': {'brand': 'Ski-Doo'},
                'then_validate': {
                    'malli': {'required': True, 'must_contain': 'Summit|MXZ|GTX'}
                }
            }
        }
        
        config = {'conditional_rules': conditional_rules}
        validator = InternalValidator(config=config)
        
        # Ski-Doo with valid model
        skidoo_valid = ProductData(
            model_code="TEST", brand="Ski-Doo", year=2024, malli="Summit X"
        )
        result = validator._validate_conditional_rules(skidoo_valid)
        assert result.success is True
        
        # Ski-Doo with invalid model
        skidoo_invalid = ProductData(
            model_code="TEST", brand="Ski-Doo", year=2024, malli="Catalyst"  # Arctic Cat model
        )
        result = validator._validate_conditional_rules(skidoo_invalid)
        assert result.success is False


class TestProductValidationWorkflow:
    """Test complete product validation workflow"""
    
    def test_validate_single_product_success(self):
        """Test successful validation of single product"""
        validator = InternalValidator()
        
        valid_product = ProductData(
            model_code="SKDO",
            brand="Ski-Doo",
            year=2024,
            malli="Summit X",
            paketti="Expert 165",
            moottori="850 E-TEC",
            telamatto="3.0",
            kaynnistin="Electric",
            mittaristo="Digital",
            vari="White/Black"
        )
        
        with patch.object(validator, '_load_brp_database') as mock_brp:
            mock_brp.return_value = True
            validator.brp_models = {
                "SKDO": {"brand": "Ski-Doo", "model_family": "Summit", "years": [2024]}
            }
            
            result = validator.validate_single_product(valid_product)
            
            assert result.success is True
            assert result.confidence_score >= 0.9
            assert len(result.errors) == 0
            
            # Verify all validation layers were applied
            assert 'field_validation' in result.validation_layers
            assert 'brp_database' in result.validation_layers
            assert 'specification_validation' in result.validation_layers
            assert 'cross_field_validation' in result.validation_layers
    
    def test_validate_single_product_partial_failure(self):
        """Test product validation with some issues"""
        validator = InternalValidator()
        
        problematic_product = ProductData(
            model_code="UNKN",  # Unknown model code
            brand="Unknown Brand",
            year=2024,
            malli="Unknown Model",
            moottori="Unknown Engine",  # Invalid engine
            telamatto="10.0"  # Invalid track width
        )
        
        result = validator.validate_single_product(problematic_product)
        
        assert result.success is False
        assert result.confidence_score < 0.7
        assert len(result.errors) > 0
        assert len(result.warnings) > 0
    
    def test_validate_multiple_products(self):
        """Test validation of multiple products in batch"""
        validator = InternalValidator()
        
        products = [
            ProductData(model_code="GOOD", brand="Ski-Doo", year=2024, malli="Summit"),
            ProductData(model_code="BAD1", brand="Unknown", year=1999),  # Bad year
            ProductData(model_code="OK", brand="Polaris", year=2023, malli="RMK"),
            ProductData(model_code="BAD2", brand="Test", year=2024, telamatto="99.0")  # Bad track
        ]
        
        with patch.object(validator, '_load_brp_database'):
            validator.brp_models = {
                "GOOD": {"brand": "Ski-Doo", "years": [2024]},
                "OK": {"brand": "Polaris", "years": [2023]}
            }
            
            results = validator.validate_products(products)
            
            assert len(results) == 4
            
            # Check individual results
            assert results[0].success is True  # GOOD product
            assert results[1].success is False  # Bad year
            assert results[2].success is True  # OK product  
            assert results[3].success is False  # Bad track
            
            # Check statistics
            stats = validator.get_stats()
            assert stats.successful == 2
            assert stats.failed == 2
            assert stats.total_processed == 4
            assert stats.success_rate == 50.0


class TestStrictModeValidation:
    """Test strict mode validation behavior"""
    
    def test_strict_mode_enabled(self):
        """Test validation behavior in strict mode"""
        config = {
            'strict_mode': True,
            'confidence_threshold': 0.95  # Very high threshold
        }
        validator = InternalValidator(config=config)
        
        # Product that would pass in normal mode but not strict mode
        borderline_product = ProductData(
            model_code="BRDR",  # Not in BRP database
            brand="Ski-Doo",
            year=2024,
            malli="Summit X"
        )
        
        result = validator.validate_single_product(borderline_product)
        
        # Should fail in strict mode due to unknown model code
        assert result.success is False
        assert result.confidence_score < 0.95
    
    def test_strict_mode_disabled(self):
        """Test validation behavior with strict mode disabled"""
        config = {
            'strict_mode': False,
            'confidence_threshold': 0.6  # Lower threshold
        }
        validator = InternalValidator(config=config)
        
        # Same borderline product
        borderline_product = ProductData(
            model_code="BRDR",
            brand="Ski-Doo", 
            year=2024,
            malli="Summit X"
        )
        
        result = validator.validate_single_product(borderline_product)
        
        # Should pass in lenient mode
        assert result.success is True
        assert result.confidence_score >= 0.6


class TestValidationPerformance:
    """Test validation performance characteristics"""
    
    @pytest.mark.performance
    def test_single_product_validation_speed(self):
        """Test speed of single product validation"""
        validator = InternalValidator()
        
        product = ProductData(
            model_code="PERF", brand="Test", year=2024, malli="Performance Test"
        )
        
        with patch.object(validator, '_load_brp_database'):
            validator.brp_models = {"PERF": {"brand": "Test", "years": [2024]}}
            
            with performance_timer.time_operation("single_product_validation"):
                result = validator.validate_single_product(product)
            
            assert result is not None
            
            # Should complete quickly (less than 0.5 seconds)
            performance_timer.assert_performance("single_product_validation", 0.5)
    
    @pytest.mark.performance
    def test_batch_validation_performance(self):
        """Test performance of batch product validation"""
        validator = InternalValidator()
        
        # Create batch of products
        products = [
            ProductData(model_code=f"P{i:03d}", brand="Test", year=2024, malli=f"Model {i}")
            for i in range(50)  # 50 products
        ]
        
        with patch.object(validator, '_load_brp_database'):
            # Mock BRP database with all products
            validator.brp_models = {
                f"P{i:03d}": {"brand": "Test", "years": [2024]}
                for i in range(50)
            }
            
            with performance_timer.time_operation("batch_product_validation"):
                results = validator.validate_products(products)
            
            assert len(results) == 50
            
            # Should complete efficiently (less than 3 seconds for 50 products)
            performance_timer.assert_performance("batch_product_validation", 3.0)
    
    def test_brp_database_lookup_caching(self):
        """Test that BRP database lookups are cached for performance"""
        validator = InternalValidator()
        
        with patch.object(validator, '_query_brp_database') as mock_query:
            mock_query.return_value = {"brand": "Test", "years": [2024]}
            
            product = ProductData(model_code="CACHE", brand="Test", year=2024)
            
            # First validation should query database
            result1 = validator._validate_against_brp_database(product)
            assert mock_query.call_count == 1
            
            # Second validation should use cache
            result2 = validator._validate_against_brp_database(product)
            assert mock_query.call_count == 1  # No additional calls
            
            assert result1.success == result2.success


class TestValidationErrorHandling:
    """Test comprehensive error handling in validation"""
    
    def test_brp_database_loading_failure(self):
        """Test handling of BRP database loading failures"""
        validator = InternalValidator()
        
        with patch.object(validator, '_load_brp_database') as mock_load:
            mock_load.side_effect = Exception("Database connection failed")
            
            # Should handle gracefully and continue with other validation layers
            product = ProductData(model_code="TEST", brand="Test", year=2024)
            result = validator.validate_single_product(product)
            
            # Should still validate using other layers
            assert isinstance(result, ValidationResult)
            assert any("brp database unavailable" in warning.lower() for warning in result.warnings)
    
    def test_validation_rule_parsing_error(self):
        """Test handling of invalid validation rule configuration"""
        invalid_config = {
            'field_validation_rules': {
                'model_code': {
                    'pattern': '[invalid regex('  # Invalid regex pattern
                }
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validator = InternalValidator(config=invalid_config)
            validator._compile_validation_rules()
        
        assert "regex" in str(exc_info.value).lower() or "pattern" in str(exc_info.value).lower()
    
    def test_memory_error_during_batch_validation(self):
        """Test handling of memory errors during large batch validation"""
        validator = InternalValidator()
        
        # Create very large product list
        products = [
            ProductData(model_code=f"M{i:04d}", brand="Test", year=2024)
            for i in range(1000)  # Large batch
        ]
        
        with patch.object(validator, '_validate_against_brp_database') as mock_validate:
            mock_validate.side_effect = MemoryError("Insufficient memory")
            
            with pytest.raises(ValidationError) as exc_info:
                validator.validate_products(products)
            
            assert "memory" in str(exc_info.value).lower()
            assert isinstance(exc_info.value.original_exception, MemoryError)
    
    def test_corrupted_brp_database_handling(self):
        """Test handling of corrupted BRP database"""
        validator = InternalValidator()
        
        with patch.object(validator, '_load_brp_database') as mock_load:
            mock_load.side_effect = Exception("Database file is corrupted")
            
            # Should fall back to other validation methods
            result = validator._initialize_brp_database()
            assert result is False  # BRP database unavailable
            
            # Validation should still work without BRP database
            product = ProductData(model_code="TEST", brand="Test", year=2024)
            validation_result = validator.validate_single_product(product)
            
            assert isinstance(validation_result, ValidationResult)
            assert validation_result.confidence_score < 1.0  # Lower confidence without BRP


class TestValidationIntegration:
    """Integration tests for validation with other pipeline components"""
    
    def test_integration_with_extracted_products(self):
        """Test validation of products from extraction stage"""
        validator = InternalValidator()
        
        # Products as they might come from extraction (with varying quality)
        extracted_products = [
            ProductData(  # High quality extraction
                model_code="SKDO", brand="Ski-Doo", year=2024,
                malli="Summit X", moottori="850 E-TEC", telamatto="3.0"
            ),
            ProductData(  # Partial extraction
                model_code="ARCT", brand="Arctic Cat", year=2024,
                malli="Catalyst"  # Missing some fields
            ),
            ProductData(  # Poor quality extraction
                model_code="UNKN", brand="", year=2024  # Missing brand
            )
        ]
        
        with patch.object(validator, '_load_brp_database'):
            validator.brp_models = {
                "SKDO": {"brand": "Ski-Doo", "years": [2024]},
                "ARCT": {"brand": "Arctic Cat", "years": [2024]}
            }
            
            results = validator.validate_products(extracted_products)
            
            assert len(results) == 3
            assert results[0].success is True  # High quality
            assert results[1].success is True  # Partial but valid
            assert results[2].success is False  # Poor quality
    
    def test_integration_with_matching_results(self):
        """Test validation considering matching results from previous stage"""
        validator = InternalValidator()
        
        product = ProductData(
            model_code="MTCH",
            brand="Ski-Doo",
            year=2024,
            malli="Summit X"
        )
        
        # Add matching metadata
        product.matching_confidence = 0.95
        product.matched_catalog_entry = "Summit X Expert 165"
        
        result = validator.validate_single_product(product)
        
        # Should consider matching confidence in validation
        if hasattr(result, 'matching_considered'):
            assert result.matching_considered is True
        
        # High matching confidence should boost validation confidence
        assert result.confidence_score >= 0.8