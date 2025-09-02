"""
Unit tests for Avito XML generation functionality
Tests AvitoXMLGenerator class and XML template rendering
"""

import pytest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime

from pipeline.stage4_generation import AvitoXMLGenerator
from core import ProductData, CatalogData, AvitoXMLData, ValidationResult, PipelineStats
from core.exceptions import GenerationError
from tests.utils import performance_timer, file_helpers
from tests.fixtures.sample_data import SampleDataFactory


class TestAvitoXMLGeneratorInitialization:
    """Test AvitoXMLGenerator initialization and configuration"""
    
    def test_avito_xml_generator_creation_default(self):
        """Test creating AvitoXMLGenerator with default configuration"""
        generator = AvitoXMLGenerator()
        
        assert isinstance(generator, AvitoXMLGenerator)
        assert generator.config is not None
        assert generator.stats.stage == 'generation'
        assert 'template_path' in generator.config
        assert 'output_encoding' in generator.config
    
    def test_avito_xml_generator_custom_config(self):
        """Test AvitoXMLGenerator with custom configuration"""
        custom_config = {
            'template_path': '/custom/templates',
            'output_encoding': 'utf-8',
            'validate_xml': True,
            'format_xml': True,
            'include_metadata': True,
            'price_currency': 'RUB',
            'default_location': 'Moscow'
        }
        
        generator = AvitoXMLGenerator(config=custom_config)
        
        assert generator.config['template_path'] == '/custom/templates'
        assert generator.config['output_encoding'] == 'utf-8'
        assert generator.config['validate_xml'] is True
        assert generator.config['format_xml'] is True
        assert generator.config['price_currency'] == 'RUB'
    
    def test_template_loading_success(self):
        """Test successful template loading"""
        generator = AvitoXMLGenerator()
        
        mock_template_content = """<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>{{ title }}</title>
    <brand>{{ brand }}</brand>
    <year>{{ year }}</year>
    <price>{{ price }}</price>
</item>"""
        
        with patch('builtins.open', mock_open(read_data=mock_template_content)):
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = True
                
                generator.load_templates()
                
                assert 'avito_snowmobile' in generator.templates
                assert '{{ title }}' in generator.templates['avito_snowmobile']
    
    def test_template_loading_failure(self):
        """Test template loading failure handling"""
        generator = AvitoXMLGenerator()
        
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False
            
            with pytest.raises(GenerationError) as exc_info:
                generator.load_templates()
            
            assert "template" in str(exc_info.value).lower()
            assert "not found" in str(exc_info.value).lower()


class TestProductToXMLDataConversion:
    """Test conversion from ProductData to AvitoXMLData"""
    
    def test_convert_complete_product_data(self):
        """Test conversion of complete ProductData to AvitoXMLData"""
        generator = AvitoXMLGenerator()
        
        product = ProductData(
            model_code="SKDO",
            brand="Ski-Doo",
            year=2024,
            malli="Summit X",
            paketti="Expert 165",
            moottori="850 E-TEC Turbo R",
            telamatto="3.0",
            kaynnistin="Electric",
            mittaristo="10.25\" Digital",
            vari="Octane Blue/Black"
        )
        
        catalog_data = CatalogData(
            model_family="Summit X",
            brand="Ski-Doo",
            specifications={"fuel_capacity": "40L", "dry_weight": "250kg"},
            features=["Mountain Strap", "Premium Sound", "Heated Seat"]
        )
        
        xml_data = generator.generate_xml_data(product, catalog_data)
        
        assert isinstance(xml_data, AvitoXMLData)
        assert xml_data.model_code == "SKDO"
        assert xml_data.brand == "Ski-Doo"
        assert xml_data.year == 2024
        assert "Summit X" in xml_data.title
        assert "Expert 165" in xml_data.title
        assert "850 E-TEC Turbo R" in xml_data.description
        assert "Electric" in xml_data.description
        assert "Mountain Strap" in xml_data.description
    
    def test_convert_minimal_product_data(self):
        """Test conversion of minimal ProductData"""
        generator = AvitoXMLGenerator()
        
        minimal_product = ProductData(
            model_code="MIN1",
            brand="TestBrand",
            year=2024
        )
        
        xml_data = generator.generate_xml_data(minimal_product)
        
        assert isinstance(xml_data, AvitoXMLData)
        assert xml_data.model_code == "MIN1"
        assert xml_data.brand == "TestBrand"
        assert xml_data.year == 2024
        assert xml_data.title is not None
        assert len(xml_data.title) > 0
        assert xml_data.description is not None
    
    def test_price_formatting_euros_to_rubles(self):
        """Test price conversion from EUR to RUB"""
        config = {'price_currency': 'RUB', 'eur_to_rub_rate': 100}
        generator = AvitoXMLGenerator(config=config)
        
        # Test various price formats
        test_prices = [15000, 25000.50, 45000]
        expected_rub = [1500000, 2500050, 4500000]  # EUR * 100
        
        for eur_price, expected in zip(test_prices, expected_rub):
            formatted_price = generator.format_price(eur_price, 'EUR')
            assert formatted_price == expected
    
    def test_title_generation_logic(self):
        """Test product title generation logic"""
        generator = AvitoXMLGenerator()
        
        product = ProductData(
            model_code="TITLE",
            brand="Yamaha",
            year=2024,
            malli="Sidewinder",
            paketti="L-TX GT"
        )
        
        title = generator.generate_product_title(product)
        
        assert "Yamaha" in title
        assert "Sidewinder" in title
        assert "2024" in title
        assert "L-TX GT" in title
        
        # Title should be reasonable length (not too long)
        assert len(title) <= 100
    
    def test_description_generation_with_catalog(self):
        """Test description generation with catalog enhancement"""
        generator = AvitoXMLGenerator()
        
        product = ProductData(
            model_code="DESC",
            brand="Arctic Cat",
            year=2024,
            malli="Catalyst",
            moottori="998cc Turbo",
            telamatto="3.0"
        )
        
        catalog_data = CatalogData(
            model_family="Catalyst",
            brand="Arctic Cat",
            specifications={"suspension": "QS3", "fuel_capacity": "41L"},
            features=["Electronic Power Steering", "7\" Touchscreen", "Heated Grips"]
        )
        
        description = generator.generate_product_description(product, catalog_data)
        
        assert "DESC" in description  # Model code
        assert "998cc Turbo" in description  # Engine
        assert "3.0" in description  # Track width
        assert "Electronic Power Steering" in description  # Feature
        assert "QS3" in description  # Specification
        assert len(description) > 50  # Reasonable length


class TestXMLRendering:
    """Test XML string rendering from AvitoXMLData"""
    
    def test_render_xml_basic_template(self):
        """Test basic XML rendering with template"""
        generator = AvitoXMLGenerator()
        
        # Mock template
        generator.templates['avito_snowmobile'] = """<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
    <brand>{{ brand }}</brand>
    <year>{{ year }}</year>
    <price>{{ price }}</price>
    <description>{{ description }}</description>
</item>"""
        
        xml_data = AvitoXMLData(
            title="Test Snowmobile 2024",
            model_code="TEST",
            brand="TestBrand",
            year=2024,
            price=25000,
            description="Test snowmobile description"
        )
        
        xml_string = generator.render_xml(xml_data)
        
        # Verify XML structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml_string
        assert '<title>Test Snowmobile 2024</title>' in xml_string
        assert '<model_code>TEST</model_code>' in xml_string
        assert '<brand>TestBrand</brand>' in xml_string
        assert '<year>2024</year>' in xml_string
        assert '<price>25000</price>' in xml_string
        
        # Verify XML is well-formed
        try:
            ET.fromstring(xml_string)
        except ET.ParseError:
            pytest.fail("Generated XML is not well-formed")
    
    def test_render_xml_with_special_characters(self):
        """Test XML rendering with special characters that need escaping"""
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <description>{{ description }}</description>
</item>"""
        
        xml_data = AvitoXMLData(
            title="Test & Special <Characters>",
            description="Description with \"quotes\" and 'apostrophes' & ampersands"
        )
        
        xml_string = generator.render_xml(xml_data)
        
        # Special characters should be escaped
        assert "&amp;" in xml_string  # & escaped
        assert "&lt;" in xml_string   # < escaped
        assert "&gt;" in xml_string   # > escaped
        assert "&quot;" in xml_string  # " escaped
        
        # Verify XML is still well-formed after escaping
        try:
            ET.fromstring(xml_string)
        except ET.ParseError:
            pytest.fail("XML with special characters is not well-formed")
    
    def test_render_xml_with_optional_fields(self):
        """Test XML rendering handling of optional/missing fields"""
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <brand>{{ brand or 'Unknown' }}</brand>
    <price>{{ price if price else 'Contact for price' }}</price>
    <color>{{ color if color else 'Not specified' }}</color>
</item>"""
        
        xml_data = AvitoXMLData(
            title="Test Product",
            brand=None,  # Missing brand
            price=None,  # Missing price
            color="Red"  # Has color
        )
        
        xml_string = generator.render_xml(xml_data)
        
        assert "<brand>Unknown</brand>" in xml_string
        assert "<price>Contact for price</price>" in xml_string
        assert "<color>Red</color>" in xml_string
    
    def test_render_xml_formatting(self):
        """Test XML formatting options"""
        config = {'format_xml': True}
        generator = AvitoXMLGenerator(config=config)
        
        generator.templates['avito_snowmobile'] = "<item><title>{{ title }}</title><brand>{{ brand }}</brand></item>"
        
        xml_data = AvitoXMLData(title="Test", brand="Test")
        
        formatted_xml = generator.render_xml(xml_data)
        
        # Should have proper indentation and line breaks when formatted
        lines = formatted_xml.split('\n')
        assert len(lines) > 1  # Multiple lines due to formatting


class TestXMLValidation:
    """Test XML validation functionality"""
    
    def test_xml_syntax_validation_valid(self):
        """Test validation of syntactically correct XML"""
        generator = AvitoXMLGenerator()
        
        valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>Valid XML</title>
    <brand>TestBrand</brand>
    <year>2024</year>
</item>"""
        
        result = generator.validate_xml_syntax(valid_xml)
        
        assert result.success is True
        assert len(result.errors) == 0
    
    def test_xml_syntax_validation_invalid(self):
        """Test validation of syntactically incorrect XML"""
        generator = AvitoXMLGenerator()
        
        invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>Invalid XML</title>
    <brand>TestBrand
    <year>2024</year>
</item>"""  # Missing closing tag for <brand>
        
        result = generator.validate_xml_syntax(invalid_xml)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert any("xml" in error.lower() for error in result.errors)
    
    def test_xml_content_validation(self):
        """Test validation of XML content against Avito requirements"""
        generator = AvitoXMLGenerator()
        
        # XML with all required fields
        complete_xml = """<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>Complete Snowmobile Listing</title>
    <model_code>COMP</model_code>
    <brand>TestBrand</brand>
    <year>2024</year>
    <price>25000</price>
    <description>Complete description</description>
</item>"""
        
        result = generator.validate_xml_content(complete_xml)
        assert result.success is True
        
        # XML missing required fields
        incomplete_xml = """<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>Incomplete Listing</title>
</item>"""
        
        result = generator.validate_xml_content(incomplete_xml)
        assert result.success is False
        assert any("required" in error.lower() for error in result.errors)
    
    def test_xml_schema_validation(self):
        """Test XML schema validation if schema is available"""
        config = {'validate_against_schema': True, 'schema_path': 'avito_schema.xsd'}
        generator = AvitoXMLGenerator(config=config)
        
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>Schema Test</title>
    <brand>TestBrand</brand>
</item>"""
        
        with patch('lxml.etree.XMLSchema') as mock_schema:
            mock_schema_instance = MagicMock()
            mock_schema.return_value = mock_schema_instance
            mock_schema_instance.validate.return_value = True
            
            result = generator.validate_xml_against_schema(xml_content)
            
            assert result.success is True


class TestBatchXMLGeneration:
    """Test batch XML generation for multiple products"""
    
    def test_generate_xml_for_multiple_products(self):
        """Test generating XML for multiple products"""
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
    <brand>{{ brand }}</brand>
</item>"""
        
        products = [
            ProductData(model_code="PRD1", brand="Brand1", year=2024, malli="Model1"),
            ProductData(model_code="PRD2", brand="Brand2", year=2024, malli="Model2"),
            ProductData(model_code="PRD3", brand="Brand3", year=2024, malli="Model3")
        ]
        
        xml_strings = generator.generate_xml_for_products(products)
        
        assert len(xml_strings) == 3
        
        # Verify each XML contains correct product data
        for i, xml_string in enumerate(xml_strings):
            assert f"<model_code>PRD{i+1}</model_code>" in xml_string
            assert f"<brand>Brand{i+1}</brand>" in xml_string
            
            # Verify each XML is well-formed
            try:
                ET.fromstring(xml_string)
            except ET.ParseError:
                pytest.fail(f"Generated XML {i+1} is not well-formed")
    
    def test_generate_xml_with_failures(self):
        """Test batch XML generation with some product failures"""
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
</item>"""
        
        products = [
            ProductData(model_code="GOOD", brand="Good", year=2024, malli="Model"),
            ProductData(model_code="", brand="Bad", year=2024),  # Invalid model code
            ProductData(model_code="ALSO", brand="AlsoGood", year=2024, malli="Model")
        ]
        
        # Mock validation to fail for empty model code
        with patch.object(generator, 'generate_xml_data') as mock_generate:
            def mock_generate_side_effect(product, catalog=None):
                if product.model_code == "":
                    raise GenerationError("Invalid model code")
                return AvitoXMLData(
                    title=f"{product.brand} {product.malli}",
                    model_code=product.model_code,
                    brand=product.brand
                )
            
            mock_generate.side_effect = mock_generate_side_effect
            
            xml_strings = generator.generate_xml_for_products(products)
            
            # Should return only successful generations
            assert len(xml_strings) == 2  # Only valid products
            
            # Verify statistics
            stats = generator.get_stats()
            assert stats.successful == 2
            assert stats.failed == 1
            assert stats.total_processed == 3
    
    def test_combine_xml_strings_to_document(self):
        """Test combining individual XML strings into complete document"""
        generator = AvitoXMLGenerator()
        
        individual_xml_strings = [
            "<item><title>Product 1</title><brand>Brand1</brand></item>",
            "<item><title>Product 2</title><brand>Brand2</brand></item>",
            "<item><title>Product 3</title><brand>Brand3</brand></item>"
        ]
        
        combined_xml = generator._combine_xml_strings(individual_xml_strings)
        
        # Should have XML declaration and root element
        assert '<?xml version="1.0" encoding="UTF-8"?>' in combined_xml
        assert '<items>' in combined_xml
        assert '</items>' in combined_xml
        
        # Should contain all individual items
        for xml_string in individual_xml_strings:
            assert xml_string in combined_xml
        
        # Verify combined XML is well-formed
        try:
            ET.fromstring(combined_xml)
        except ET.ParseError:
            pytest.fail("Combined XML document is not well-formed")


class TestFileOperations:
    """Test XML file saving and management"""
    
    def test_save_xml_file_success(self, temp_xml_file):
        """Test successful XML file saving"""
        generator = AvitoXMLGenerator()
        
        xml_strings = [
            "<item><title>Product 1</title></item>",
            "<item><title>Product 2</title></item>"
        ]
        
        result = generator.save_xml_file(xml_strings, temp_xml_file)
        
        assert result is True
        
        # Verify file was created and contains expected content
        assert temp_xml_file.exists()
        content = temp_xml_file.read_text(encoding='utf-8')
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert '<items>' in content
        assert 'Product 1' in content
        assert 'Product 2' in content
    
    def test_save_xml_file_directory_creation(self):
        """Test XML file saving with directory creation"""
        generator = AvitoXMLGenerator()
        
        # Non-existent directory path
        output_path = Path("/tmp/test_avito_pipeline/output/test.xml")
        
        xml_strings = ["<item><title>Test</title></item>"]
        
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            with patch('builtins.open', mock_open()) as mock_file:
                result = generator.save_xml_file(xml_strings, output_path)
                
                assert result is True
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
                mock_file.assert_called_once()
    
    def test_save_xml_file_permission_error(self):
        """Test XML file saving with permission errors"""
        generator = AvitoXMLGenerator()
        
        xml_strings = ["<item><title>Test</title></item>"]
        output_path = Path("/readonly/test.xml")
        
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(GenerationError) as exc_info:
                generator.save_xml_file(xml_strings, output_path)
            
            assert "permission" in str(exc_info.value).lower()
            assert isinstance(exc_info.value.original_exception, PermissionError)


class TestAvitoXMLGeneratorPerformance:
    """Test XML generation performance characteristics"""
    
    @pytest.mark.performance
    def test_single_product_generation_speed(self):
        """Test speed of single product XML generation"""
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
    <brand>{{ brand }}</brand>
    <description>{{ description }}</description>
</item>"""
        
        product = ProductData(
            model_code="PERF",
            brand="Performance",
            year=2024,
            malli="Speed Test"
        )
        
        with performance_timer.time_operation("single_xml_generation"):
            xml_data = generator.generate_xml_data(product)
            xml_string = generator.render_xml(xml_data)
        
        assert xml_string is not None
        assert len(xml_string) > 0
        
        # Should complete quickly (less than 0.1 seconds)
        performance_timer.assert_performance("single_xml_generation", 0.1)
    
    @pytest.mark.performance
    def test_batch_generation_performance(self):
        """Test performance of batch XML generation"""
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
</item>"""
        
        # Create batch of products
        products = [
            ProductData(model_code=f"B{i:03d}", brand="Batch", year=2024, malli=f"Model {i}")
            for i in range(100)  # 100 products
        ]
        
        with performance_timer.time_operation("batch_xml_generation"):
            xml_strings = generator.generate_xml_for_products(products)
        
        assert len(xml_strings) == 100
        
        # Should complete efficiently (less than 2 seconds for 100 products)
        performance_timer.assert_performance("batch_xml_generation", 2.0)
    
    def test_template_caching_performance(self):
        """Test that templates are cached for performance"""
        generator = AvitoXMLGenerator()
        
        template_content = "<item><title>{{ title }}</title></item>"
        
        with patch('builtins.open', mock_open(read_data=template_content)) as mock_file:
            with patch('pathlib.Path.exists', return_value=True):
                # First load should read file
                generator.load_templates()
                assert mock_file.call_count == 1
                
                # Second load should use cache
                generator.load_templates()
                assert mock_file.call_count == 1  # No additional file reads


class TestAvitoXMLGeneratorErrorHandling:
    """Test comprehensive error handling"""
    
    def test_template_rendering_error(self):
        """Test handling of template rendering errors"""
        generator = AvitoXMLGenerator()
        
        # Template with invalid Jinja2 syntax
        generator.templates['avito_snowmobile'] = "{{ invalid_syntax }"
        
        xml_data = AvitoXMLData(title="Test", brand="Test")
        
        with pytest.raises(GenerationError) as exc_info:
            generator.render_xml(xml_data)
        
        assert "template" in str(exc_info.value).lower()
        assert "render" in str(exc_info.value).lower()
    
    def test_xml_data_validation_error(self):
        """Test handling of invalid XML data"""
        generator = AvitoXMLGenerator()
        
        # XML data missing required fields
        invalid_xml_data = AvitoXMLData(
            title="",  # Empty title
            model_code=None,  # Missing model code
            brand=None  # Missing brand
        )
        
        with pytest.raises(GenerationError) as exc_info:
            generator.generate_xml_data_internal(invalid_xml_data)
        
        assert "validation" in str(exc_info.value).lower()
    
    def test_memory_error_during_batch_generation(self):
        """Test handling of memory errors during batch generation"""
        generator = AvitoXMLGenerator()
        
        # Create very large product list
        products = [
            ProductData(model_code=f"M{i:04d}", brand="Memory", year=2024)
            for i in range(10000)  # Very large batch
        ]
        
        with patch.object(generator, 'render_xml') as mock_render:
            mock_render.side_effect = MemoryError("Insufficient memory")
            
            with pytest.raises(GenerationError) as exc_info:
                generator.generate_xml_for_products(products)
            
            assert "memory" in str(exc_info.value).lower()
            assert isinstance(exc_info.value.original_exception, MemoryError)
    
    def test_template_not_found_error(self):
        """Test handling of missing template files"""
        config = {'template_path': '/nonexistent/path'}
        generator = AvitoXMLGenerator(config=config)
        
        with pytest.raises(GenerationError) as exc_info:
            generator.load_templates()
        
        assert "template" in str(exc_info.value).lower()
        assert "not found" in str(exc_info.value).lower()


class TestAvitoXMLGeneratorIntegration:
    """Integration tests for XML generator with other components"""
    
    def test_integration_with_validated_products(self):
        """Test XML generation from validated products"""
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <model_code>{{ model_code }}</model_code>
    <validation_score>{{ validation_score or 'N/A' }}</validation_score>
</item>"""
        
        # Product with validation metadata
        validated_product = ProductData(
            model_code="VALID",
            brand="Validated",
            year=2024,
            malli="Test Model"
        )
        validated_product.validation_score = 0.95  # From validation stage
        validated_product.validation_notes = ["Passed all checks"]
        
        xml_strings = generator.generate_xml_for_products([validated_product])
        
        assert len(xml_strings) == 1
        assert "<validation_score>0.95</validation_score>" in xml_strings[0]
    
    def test_integration_with_catalog_enrichment(self):
        """Test XML generation with catalog data enrichment"""
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <features>{{ features | join(', ') if features else 'No features listed' }}</features>
    <specifications>{{ specifications }}</specifications>
</item>"""
        
        product = ProductData(model_code="ENRICH", brand="Test", year=2024, malli="Model")
        
        catalog_data = CatalogData(
            model_family="Model",
            brand="Test",
            features=["Feature 1", "Feature 2", "Feature 3"],
            specifications={"engine": "Test Engine", "track": "3.0"}
        )
        
        xml_strings = generator.generate_xml_for_products([product], [catalog_data])
        
        assert len(xml_strings) == 1
        assert "Feature 1, Feature 2, Feature 3" in xml_strings[0]
        assert "Test Engine" in xml_strings[0]
    
    def test_integration_with_price_data(self):
        """Test XML generation with price information"""
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <price currency="{{ currency }}">{{ price }}</price>
    <price_note>{{ price_note }}</price_note>
</item>"""
        
        # Product with price information
        product = ProductData(
            model_code="PRICE",
            brand="Priced",
            year=2024,
            malli="Expensive Model"
        )
        product.price = 35000
        product.price_currency = "EUR"
        product.price_note = "Price negotiable"
        
        xml_strings = generator.generate_xml_for_products([product])
        
        assert len(xml_strings) == 1
        xml_content = xml_strings[0]
        assert 'currency="EUR"' in xml_content
        assert "<price_note>Price negotiable</price_note>" in xml_content
    
    def test_integration_statistics_tracking(self):
        """Test integration with pipeline statistics"""
        generator = AvitoXMLGenerator()
        
        generator.templates['avito_snowmobile'] = "<item><title>{{ title }}</title></item>"
        
        products = [
            ProductData(model_code="ST1", brand="Stats", year=2024, malli="Model 1"),
            ProductData(model_code="ST2", brand="Stats", year=2024, malli="Model 2"),
            ProductData(model_code="", brand="Invalid", year=2024)  # Should fail
        ]
        
        # Mock failure for invalid product
        with patch.object(generator, 'generate_xml_data') as mock_generate:
            def mock_side_effect(product, catalog=None):
                if product.model_code == "":
                    raise GenerationError("Invalid model code")
                return AvitoXMLData(title=f"{product.brand} {product.malli}", 
                                  model_code=product.model_code, brand=product.brand)
            
            mock_generate.side_effect = mock_side_effect
            
            xml_strings = generator.generate_xml_for_products(products)
            
            # Verify statistics
            stats = generator.get_stats()
            assert stats.total_processed == 3
            assert stats.successful == 2
            assert stats.failed == 1
            assert stats.success_rate == (2/3) * 100
            assert stats.processing_time is not None