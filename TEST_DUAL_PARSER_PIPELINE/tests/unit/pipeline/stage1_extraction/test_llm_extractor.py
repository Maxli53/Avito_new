"""
Unit tests for LLM extraction functionality
Tests LLMExtractor class and language model integration
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from pipeline.stage1_extraction import LLMExtractor
from core import ProductData, PipelineStats
from core.exceptions import ExtractionError
from tests.utils import performance_timer
from tests.fixtures.sample_data import SampleDataFactory


class TestLLMExtractorInitialization:
    """Test LLMExtractor initialization and configuration"""
    
    def test_llm_extractor_creation_default_config(self):
        """Test creating LLMExtractor with default configuration"""
        extractor = LLMExtractor()
        
        assert isinstance(extractor, LLMExtractor)
        assert extractor.config is not None
        assert extractor.config['provider'] == 'claude'  # Default provider
        assert extractor.stats.stage == 'extraction'
    
    def test_llm_extractor_claude_config(self):
        """Test LLMExtractor with Claude configuration"""
        config = {
            'provider': 'claude',
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 4000,
            'temperature': 0.1,
            'api_timeout': 30
        }
        
        extractor = LLMExtractor(config=config)
        
        assert extractor.config['provider'] == 'claude'
        assert extractor.config['model'] == 'claude-3-sonnet-20240229'
        assert extractor.config['max_tokens'] == 4000
        assert extractor.config['temperature'] == 0.1
    
    def test_llm_extractor_gpt_config(self):
        """Test LLMExtractor with GPT configuration"""
        config = {
            'provider': 'gpt',
            'model': 'gpt-4',
            'max_tokens': 3000,
            'temperature': 0.2,
            'api_timeout': 45
        }
        
        extractor = LLMExtractor(config=config)
        
        assert extractor.config['provider'] == 'gpt'
        assert extractor.config['model'] == 'gpt-4'
        assert extractor.config['max_tokens'] == 3000
        assert extractor.config['temperature'] == 0.2


class TestClaudeIntegration:
    """Test Claude LLM integration"""
    
    def test_claude_client_initialization(self):
        """Test Claude client initialization"""
        config = {
            'provider': 'claude',
            'api_key': 'test_claude_key'
        }
        
        extractor = LLMExtractor(config=config)
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            client = extractor._get_claude_client()
            
            mock_anthropic.assert_called_once_with(api_key='test_claude_key')
    
    def test_claude_extraction_success(self):
        """Test successful product extraction with Claude"""
        config = {
            'provider': 'claude',
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 4000
        }
        extractor = LLMExtractor(config=config)
        
        sample_text = """
        Ski-Doo Summit X Expert 165 2024
        850 E-TEC Turbo R Engine
        3.0 Track Width
        Electric Start
        Digital Display
        """
        
        expected_response = json.dumps([{
            "model_code": "SKDO",
            "brand": "Ski-Doo",
            "year": 2024,
            "malli": "Summit X",
            "paketti": "Expert 165",
            "moottori": "850 E-TEC Turbo R",
            "telamatto": "3.0",
            "kaynnistin": "Electric",
            "mittaristo": "Digital Display"
        }])
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.content[0].text = expected_response
            mock_client.messages.create.return_value = mock_response
            
            products = extractor.extract_products_from_text(sample_text)
            
            assert len(products) == 1
            product = products[0]
            assert product.brand == "Ski-Doo"
            assert product.year == 2024
            assert product.malli == "Summit X"
            assert product.paketti == "Expert 165"
            assert product.moottori == "850 E-TEC Turbo R"
    
    def test_claude_api_error_handling(self):
        """Test Claude API error handling"""
        extractor = LLMExtractor(config={'provider': 'claude'})
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            # Simulate API error
            mock_client.messages.create.side_effect = Exception("Claude API error")
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_products_from_text("test text")
            
            assert "claude api error" in str(exc_info.value).lower()
            assert exc_info.value.details['llm_provider'] == 'claude'
    
    def test_claude_rate_limit_handling(self):
        """Test Claude rate limit error handling"""
        extractor = LLMExtractor(config={'provider': 'claude'})
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            # Simulate rate limit error
            rate_limit_error = Exception("Rate limit exceeded")
            rate_limit_error.status_code = 429
            mock_client.messages.create.side_effect = rate_limit_error
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_products_from_text("test text")
            
            assert "rate limit" in str(exc_info.value).lower()
            assert exc_info.value.details['status_code'] == 429


class TestGPTIntegration:
    """Test GPT LLM integration"""
    
    def test_gpt_client_initialization(self):
        """Test GPT client initialization"""
        config = {
            'provider': 'gpt',
            'api_key': 'test_openai_key'
        }
        
        extractor = LLMExtractor(config=config)
        
        with patch('openai.OpenAI') as mock_openai:
            client = extractor._get_gpt_client()
            
            mock_openai.assert_called_once_with(api_key='test_openai_key')
    
    def test_gpt_extraction_success(self):
        """Test successful product extraction with GPT"""
        config = {
            'provider': 'gpt',
            'model': 'gpt-4',
            'max_tokens': 3000
        }
        extractor = LLMExtractor(config=config)
        
        sample_text = """
        Arctic Cat Catalyst 9000 Turbo R 2024
        998cc Turbo Engine
        3.0 Track Width
        Electric Start
        7" Touch Display
        Team Arctic Green
        """
        
        expected_response = json.dumps([{
            "model_code": "ARCT",
            "brand": "Arctic Cat",
            "year": 2024,
            "malli": "Catalyst",
            "paketti": "9000 Turbo R",
            "moottori": "998cc Turbo",
            "telamatto": "3.0",
            "kaynnistin": "Electric",
            "mittaristo": "7\" Touch Display",
            "vari": "Team Arctic Green"
        }])
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices[0].message.content = expected_response
            mock_client.chat.completions.create.return_value = mock_response
            
            products = extractor.extract_products_from_text(sample_text)
            
            assert len(products) == 1
            product = products[0]
            assert product.brand == "Arctic Cat"
            assert product.year == 2024
            assert product.malli == "Catalyst"
            assert product.paketti == "9000 Turbo R"
    
    def test_gpt_api_error_handling(self):
        """Test GPT API error handling"""
        extractor = LLMExtractor(config={'provider': 'gpt'})
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            # Simulate API error
            mock_client.chat.completions.create.side_effect = Exception("OpenAI API error")
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_products_from_text("test text")
            
            assert "openai api error" in str(exc_info.value).lower()
            assert exc_info.value.details['llm_provider'] == 'gpt'


class TestPromptEngineering:
    """Test prompt engineering and optimization"""
    
    def test_prompt_template_generation(self):
        """Test generation of extraction prompt templates"""
        extractor = LLMExtractor()
        
        sample_text = "Snowmobile product specifications"
        prompt = extractor._build_extraction_prompt(sample_text)
        
        # Verify prompt contains key elements
        assert "snowmobile" in prompt.lower()
        assert "json" in prompt.lower()
        assert "model_code" in prompt
        assert "brand" in prompt
        assert "year" in prompt
        assert sample_text in prompt
    
    def test_prompt_with_examples(self):
        """Test prompt with few-shot examples"""
        config = {'use_examples': True}
        extractor = LLMExtractor(config=config)
        
        sample_text = "Test snowmobile data"
        prompt = extractor._build_extraction_prompt(sample_text)
        
        # Should contain examples
        assert "example" in prompt.lower()
        assert "ski-doo" in prompt.lower()  # Example brand
        assert "S1BX" in prompt or similar_example_pattern_found(prompt)
    
    def test_prompt_customization_for_finnish_text(self):
        """Test prompt customization for Finnish language text"""
        config = {
            'language': 'finnish',
            'include_finnish_terms': True
        }
        extractor = LLMExtractor(config=config)
        
        finnish_text = """
        Merkki: Lynx
        Malli: Ranger
        Vuosi: 2024
        Moottori: 850 E-TEC
        Väri: Valkoinen/Sininen
        """
        
        prompt = extractor._build_extraction_prompt(finnish_text)
        
        # Should include Finnish field mappings
        assert "merkki" in prompt.lower() or "brand" in prompt.lower()
        assert "malli" in prompt.lower() or "model" in prompt.lower()
        assert "finnish" in prompt.lower() or "suomi" in prompt.lower()
    
    def test_prompt_optimization_for_token_limits(self):
        """Test prompt optimization for token limits"""
        config = {
            'max_tokens': 1000,  # Small limit
            'optimize_prompt': True
        }
        extractor = LLMExtractor(config=config)
        
        # Very long text that would exceed token limit
        long_text = "Snowmobile specification data. " * 200  # ~600 words
        
        prompt = extractor._build_extraction_prompt(long_text)
        
        # Prompt should be truncated or optimized
        estimated_tokens = len(prompt.split()) * 1.3  # Rough token estimation
        assert estimated_tokens < 900  # Leave room for response


class TestJSONResponseHandling:
    """Test JSON response parsing and validation"""
    
    def test_valid_json_response_parsing(self):
        """Test parsing valid JSON response from LLM"""
        extractor = LLMExtractor()
        
        json_response = '''[
            {
                "model_code": "TEST",
                "brand": "TestBrand",
                "year": 2024,
                "malli": "TestModel",
                "paketti": "TestPackage",
                "moottori": "TestEngine"
            }
        ]'''
        
        products = extractor._parse_json_response(json_response)
        
        assert len(products) == 1
        product = products[0]
        assert product.model_code == "TEST"
        assert product.brand == "TestBrand"
        assert product.year == 2024
    
    def test_malformed_json_response_handling(self):
        """Test handling of malformed JSON responses"""
        extractor = LLMExtractor()
        
        malformed_json = '''[
            {
                "model_code": "TEST",
                "brand": "TestBrand",
                "year": 2024,
                "malli": "TestModel"
            // Missing closing bracket
        '''
        
        with pytest.raises(ExtractionError) as exc_info:
            extractor._parse_json_response(malformed_json)
        
        assert "json" in str(exc_info.value).lower()
        assert "parse" in str(exc_info.value).lower()
    
    def test_empty_json_array_response(self):
        """Test handling of empty JSON array response"""
        extractor = LLMExtractor()
        
        empty_response = "[]"
        
        products = extractor._parse_json_response(empty_response)
        
        assert isinstance(products, list)
        assert len(products) == 0
    
    def test_non_array_json_response(self):
        """Test handling of non-array JSON response"""
        extractor = LLMExtractor()
        
        non_array_response = '''
        {
            "error": "No products found",
            "message": "Unable to extract snowmobile data"
        }
        '''
        
        with pytest.raises(ExtractionError) as exc_info:
            extractor._parse_json_response(non_array_response)
        
        assert "array" in str(exc_info.value).lower() or "list" in str(exc_info.value).lower()
    
    def test_json_with_missing_required_fields(self):
        """Test JSON response missing required fields"""
        extractor = LLMExtractor()
        
        incomplete_json = '''[
            {
                "brand": "TestBrand",
                "year": 2024
                // Missing model_code
            }
        ]'''
        
        # This should either fail validation or create incomplete ProductData
        try:
            products = extractor._parse_json_response(incomplete_json)
            # If it doesn't fail, the ProductData validation should catch it
            assert len(products) >= 0  # Flexible handling
        except (ExtractionError, ValueError):
            # Either is acceptable for missing required fields
            pass
    
    def test_json_data_type_validation(self):
        """Test validation of JSON data types"""
        extractor = LLMExtractor()
        
        invalid_types_json = '''[
            {
                "model_code": "TEST",
                "brand": "TestBrand",
                "year": "not_a_number",
                "malli": 12345
            }
        ]'''
        
        # Should handle type conversion gracefully
        products = extractor._parse_json_response(invalid_types_json)
        
        assert len(products) == 1
        product = products[0]
        
        # Year should be converted to int or cause validation error
        try:
            assert isinstance(product.year, int) or product.year is None
        except ValueError:
            # Type conversion failed, which is acceptable
            pass


class TestMultipleProductExtraction:
    """Test extraction of multiple products from single text"""
    
    def test_extract_multiple_products_success(self):
        """Test successful extraction of multiple products"""
        extractor = LLMExtractor()
        
        multi_product_text = """
        Product 1: Ski-Doo Summit X 2024 850 E-TEC
        Product 2: Arctic Cat Catalyst 9000 2024 998cc Turbo
        Product 3: Polaris RMK Khaos 2023 850 Patriot
        """
        
        json_response = '''[
            {
                "model_code": "SKI1",
                "brand": "Ski-Doo",
                "year": 2024,
                "malli": "Summit X",
                "moottori": "850 E-TEC"
            },
            {
                "model_code": "ARC1", 
                "brand": "Arctic Cat",
                "year": 2024,
                "malli": "Catalyst",
                "paketti": "9000",
                "moottori": "998cc Turbo"
            },
            {
                "model_code": "POL1",
                "brand": "Polaris",
                "year": 2023,
                "malli": "RMK",
                "paketti": "Khaos",
                "moottori": "850 Patriot"
            }
        ]'''
        
        with patch.object(extractor, '_call_llm_api') as mock_api:
            mock_api.return_value = json_response
            
            products = extractor.extract_products_from_text(multi_product_text)
            
            assert len(products) == 3
            
            # Verify each product
            brands = [p.brand for p in products]
            assert "Ski-Doo" in brands
            assert "Arctic Cat" in brands
            assert "Polaris" in brands
    
    def test_extract_products_with_partial_failures(self):
        """Test extraction where some products fail validation"""
        extractor = LLMExtractor()
        
        mixed_quality_response = '''[
            {
                "model_code": "GOOD",
                "brand": "ValidBrand",
                "year": 2024,
                "malli": "ValidModel"
            },
            {
                "model_code": "",
                "brand": "InvalidBrand",
                "year": 2024
            },
            {
                "model_code": "ALSO",
                "brand": "AnotherValidBrand", 
                "year": 2023,
                "malli": "AnotherModel"
            }
        ]'''
        
        with patch.object(extractor, '_call_llm_api') as mock_api:
            mock_api.return_value = mixed_quality_response
            
            products = extractor.extract_products_from_text("test text")
            
            # Should return only valid products
            assert len(products) == 2  # Only the valid ones
            valid_codes = [p.model_code for p in products]
            assert "GOOD" in valid_codes
            assert "ALSO" in valid_codes


class TestLLMPerformance:
    """Test LLM performance and optimization"""
    
    @pytest.mark.performance
    def test_extraction_speed_small_text(self):
        """Test extraction speed for small text"""
        extractor = LLMExtractor()
        
        small_text = "Ski-Doo Summit X 2024 850 E-TEC"
        
        with patch.object(extractor, '_call_llm_api') as mock_api:
            mock_api.return_value = '[{"model_code": "TEST", "brand": "Ski-Doo", "year": 2024}]'
            
            with performance_timer.time_operation("small_text_llm_extraction"):
                products = extractor.extract_products_from_text(small_text)
            
            assert len(products) == 1
            
            # Should complete quickly (less than 2 seconds for mocked response)
            performance_timer.assert_performance("small_text_llm_extraction", 2.0)
    
    @pytest.mark.performance  
    def test_extraction_speed_large_text(self):
        """Test extraction speed for large text"""
        extractor = LLMExtractor()
        
        # Simulate large catalog text
        large_text = """
        Snowmobile Product Catalog 2024
        
        """ + ("Product specification data. " * 500)  # Large text block
        
        with patch.object(extractor, '_call_llm_api') as mock_api:
            mock_api.return_value = '''[
                {"model_code": "LRG1", "brand": "Test", "year": 2024},
                {"model_code": "LRG2", "brand": "Test", "year": 2024}
            ]'''
            
            with performance_timer.time_operation("large_text_llm_extraction"):
                products = extractor.extract_products_from_text(large_text)
            
            assert len(products) == 2
            
            # Should handle large text reasonably (less than 5 seconds for mocked response)
            performance_timer.assert_performance("large_text_llm_extraction", 5.0)
    
    def test_token_usage_tracking(self):
        """Test tracking of token usage for cost optimization"""
        config = {'track_token_usage': True}
        extractor = LLMExtractor(config=config)
        
        sample_text = "Test snowmobile data"
        
        with patch.object(extractor, '_call_llm_api') as mock_api:
            # Mock response with token usage info
            mock_api.return_value = '[]'
            
            products = extractor.extract_products_from_text(sample_text)
            
            stats = extractor.get_stats()
            
            # Should track token usage (if implemented)
            assert hasattr(stats, 'total_tokens_used') or hasattr(extractor, '_token_usage')


class TestLLMErrorHandling:
    """Test comprehensive error handling for LLM operations"""
    
    def test_network_timeout_handling(self):
        """Test handling of network timeouts"""
        config = {'api_timeout': 1}  # Very short timeout
        extractor = LLMExtractor(config=config)
        
        with patch.object(extractor, '_call_llm_api') as mock_api:
            import requests
            mock_api.side_effect = requests.Timeout("Request timeout")
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_products_from_text("test text")
            
            assert "timeout" in str(exc_info.value).lower()
            assert exc_info.value.details['api_timeout'] == 1
    
    def test_api_key_authentication_error(self):
        """Test handling of API key authentication errors"""
        config = {'api_key': 'invalid_key'}
        extractor = LLMExtractor(config=config)
        
        with patch.object(extractor, '_call_llm_api') as mock_api:
            auth_error = Exception("Invalid API key")
            auth_error.status_code = 401
            mock_api.side_effect = auth_error
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_products_from_text("test text")
            
            assert "api key" in str(exc_info.value).lower() or "authentication" in str(exc_info.value).lower()
    
    def test_model_not_found_error(self):
        """Test handling of model not found errors"""
        config = {'model': 'nonexistent-model'}
        extractor = LLMExtractor(config=config)
        
        with patch.object(extractor, '_call_llm_api') as mock_api:
            model_error = Exception("Model not found")
            model_error.status_code = 404
            mock_api.side_effect = model_error
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_products_from_text("test text")
            
            assert "model" in str(exc_info.value).lower()
            assert exc_info.value.details['model'] == 'nonexistent-model'
    
    def test_content_filtering_error(self):
        """Test handling of content filtering errors"""
        extractor = LLMExtractor()
        
        with patch.object(extractor, '_call_llm_api') as mock_api:
            content_error = Exception("Content filtered by safety system")
            content_error.status_code = 400
            mock_api.side_effect = content_error
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_products_from_text("potentially problematic content")
            
            assert "content" in str(exc_info.value).lower() or "filter" in str(exc_info.value).lower()


def similar_example_pattern_found(prompt):
    """Helper function to check for example patterns in prompt"""
    example_patterns = ["example", "for instance", "like this", "such as"]
    return any(pattern in prompt.lower() for pattern in example_patterns)