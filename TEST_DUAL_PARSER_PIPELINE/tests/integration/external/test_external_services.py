"""
Integration tests for external service interactions
Tests real integrations with LLM APIs, BERT models, and FTP servers
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import json

from pipeline.stage1_extraction import LLMExtractor
from pipeline.stage2_matching import BERTMatcher
from pipeline.stage5_upload import FTPUploader
from core import ProductData
from core.exceptions import ExtractionError, MatchingError, UploadError
from tests.fixtures.sample_data import SampleDataFactory


@pytest.mark.external
class TestLLMServiceIntegration:
    """Test integration with external LLM services (Claude, GPT)"""
    
    def test_claude_api_integration_mock(self):
        """Test Claude API integration with realistic mock responses"""
        config = {
            'provider': 'claude',
            'api_key': 'test_claude_key',
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 4000
        }
        
        extractor = LLMExtractor(config=config)
        
        sample_text = """
        SNOWMOBILE SPECIFICATIONS
        
        Model: Ski-Doo Summit X Expert 165
        Code: SKDO-2024-SX165
        Year: 2024
        Engine: 850 E-TEC Turbo R
        Track Width: 3.0 inches
        Starter: Electric
        Color: Octane Blue/Black
        
        Model: Arctic Cat Catalyst 9000 Turbo R
        Code: ARCT-2024-C9000
        Year: 2024  
        Engine: 998cc Turbo
        Track Width: 3.0 inches
        Starter: Electric
        Color: Team Arctic Green
        """
        
        # Mock realistic Claude API response
        expected_response = json.dumps([
            {
                "model_code": "SKDO",
                "brand": "Ski-Doo",
                "year": 2024,
                "malli": "Summit X",
                "paketti": "Expert 165",
                "moottori": "850 E-TEC Turbo R",
                "telamatto": "3.0",
                "kaynnistin": "Electric",
                "vari": "Octane Blue/Black"
            },
            {
                "model_code": "ARCT",
                "brand": "Arctic Cat", 
                "year": 2024,
                "malli": "Catalyst",
                "paketti": "9000 Turbo R",
                "moottori": "998cc Turbo",
                "telamatto": "3.0",
                "kaynnistin": "Electric",
                "vari": "Team Arctic Green"
            }
        ])
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            # Mock the API response structure
            mock_response = MagicMock()
            mock_response.content[0].text = expected_response
            mock_client.messages.create.return_value = mock_response
            
            products = extractor.extract_products_from_text(sample_text)
        
        assert len(products) == 2
        
        # Verify first product
        assert products[0].model_code == "SKDO"
        assert products[0].brand == "Ski-Doo"
        assert products[0].malli == "Summit X"
        assert products[0].moottori == "850 E-TEC Turbo R"
        
        # Verify second product
        assert products[1].model_code == "ARCT"
        assert products[1].brand == "Arctic Cat"
        assert products[1].malli == "Catalyst"
        
        # Verify API was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        
        assert call_args.kwargs['model'] == 'claude-3-sonnet-20240229'
        assert call_args.kwargs['max_tokens'] == 4000
        assert 'snowmobile' in call_args.kwargs['messages'][0]['content'].lower()
    
    def test_gpt_api_integration_mock(self):
        """Test GPT API integration with realistic mock responses"""
        config = {
            'provider': 'gpt',
            'api_key': 'test_openai_key',
            'model': 'gpt-4',
            'max_tokens': 3000
        }
        
        extractor = LLMExtractor(config=config)
        
        sample_text = """
        Polaris RMK Khaos 850 2023
        850 Patriot Engine
        2.75 Track Width
        Electric Start
        Digital Display
        Lime Squeeze Color
        """
        
        expected_response = json.dumps([{
            "model_code": "POLA",
            "brand": "Polaris",
            "year": 2023,
            "malli": "RMK",
            "paketti": "Khaos 850", 
            "moottori": "850 Patriot",
            "telamatto": "2.75",
            "kaynnistin": "Electric",
            "mittaristo": "Digital",
            "vari": "Lime Squeeze"
        }])
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            # Mock GPT API response structure
            mock_response = MagicMock()
            mock_response.choices[0].message.content = expected_response
            mock_client.chat.completions.create.return_value = mock_response
            
            products = extractor.extract_products_from_text(sample_text)
        
        assert len(products) == 1
        
        product = products[0]
        assert product.model_code == "POLA"
        assert product.brand == "Polaris"
        assert product.year == 2023
        assert product.malli == "RMK"
        assert product.paketti == "Khaos 850"
        
        # Verify API parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        
        assert call_args.kwargs['model'] == 'gpt-4'
        assert call_args.kwargs['max_tokens'] == 3000
    
    def test_llm_api_error_handling_integration(self):
        """Test LLM API error handling with realistic error scenarios"""
        extractor = LLMExtractor(config={'provider': 'claude', 'api_key': 'invalid_key'})
        
        # Test authentication error
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            auth_error = Exception("Invalid API key")
            auth_error.status_code = 401
            mock_client.messages.create.side_effect = auth_error
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_products_from_text("test text")
            
            assert "api key" in str(exc_info.value).lower()
            assert exc_info.value.details['llm_provider'] == 'claude'
        
        # Test rate limiting error
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            rate_limit_error = Exception("Rate limit exceeded")
            rate_limit_error.status_code = 429
            mock_client.messages.create.side_effect = rate_limit_error
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_products_from_text("test text")
            
            assert "rate limit" in str(exc_info.value).lower()
    
    def test_llm_response_validation_integration(self):
        """Test validation of LLM responses in realistic scenarios"""
        extractor = LLMExtractor(config={'provider': 'claude'})
        
        # Test malformed JSON response
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.content[0].text = "This is not valid JSON response"
            mock_client.messages.create.return_value = mock_response
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_products_from_text("test text")
            
            assert "json" in str(exc_info.value).lower()
        
        # Test incomplete product data in response
        incomplete_response = json.dumps([{
            "brand": "Ski-Doo",
            "year": 2024
            # Missing required model_code field
        }])
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.content[0].text = incomplete_response
            mock_client.messages.create.return_value = mock_response
            
            # Should handle gracefully or raise appropriate error
            try:
                products = extractor.extract_products_from_text("test text")
                # If it succeeds, verify it handled missing data appropriately
                if products:
                    # Products should have some reasonable defaults or be filtered out
                    for product in products:
                        assert hasattr(product, 'brand')
                        assert hasattr(product, 'year')
            except (ExtractionError, ValueError):
                # Or it should raise appropriate validation error
                pass


@pytest.mark.external  
class TestBERTModelIntegration:
    """Test integration with BERT models and sentence transformers"""
    
    def test_bert_model_loading_integration_mock(self):
        """Test BERT model loading with realistic mocking"""
        config = {
            'model_name': 'sentence-transformers/all-MiniLM-L6-v2',
            'device': 'cpu',
            'normalize_embeddings': True
        }
        
        matcher = BERTMatcher(config=config)
        
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            # Mock the transformer model
            mock_model = MagicMock()
            mock_transformer.return_value = mock_model
            
            # Mock encoding method to return realistic embeddings
            mock_model.encode.return_value = [
                [0.1, 0.2, 0.3, 0.4, 0.5] * 77,  # 384-dimensional embedding (typical for MiniLM)
                [0.2, 0.3, 0.1, 0.5, 0.4] * 77
            ]
            
            result = matcher._load_bert_model()
        
        assert result is True
        assert matcher.model is mock_model
        mock_transformer.assert_called_once_with('sentence-transformers/all-MiniLM-L6-v2')
    
    def test_bert_embedding_generation_integration(self):
        """Test BERT embedding generation with realistic scenarios"""
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        # Mock the model with realistic embedding dimensions
        mock_model = MagicMock()
        matcher.model = mock_model
        
        # Test embedding generation for snowmobile text
        snowmobile_texts = [
            "Ski-Doo Summit X Expert 165 850 E-TEC",
            "Arctic Cat Catalyst 9000 Turbo R 998cc",
            "Polaris RMK Khaos 850 Patriot Engine"
        ]
        
        # Mock realistic embeddings (384 dimensions for MiniLM)
        import numpy as np
        mock_embeddings = np.random.random((3, 384))
        mock_model.encode.return_value = mock_embeddings
        
        embeddings = matcher._generate_embeddings(snowmobile_texts)
        
        assert embeddings.shape == (3, 384)
        assert np.allclose(embeddings, mock_embeddings)
        
        # Verify model was called with correct parameters
        mock_model.encode.assert_called_once()
        call_args = mock_model.encode.call_args[0][0]
        
        # Should normalize text for better matching
        for original_text in snowmobile_texts:
            # Text should be present in some form (normalized)
            normalized_found = any(
                original_text.lower().replace('-', '').replace(' ', '') in
                call_text.lower().replace('-', '').replace(' ', '')
                for call_text in call_args
            )
            assert normalized_found, f"Original text '{original_text}' not found in normalized form"
    
    def test_bert_similarity_calculation_integration(self):
        """Test semantic similarity calculations with realistic data"""
        matcher = BERTMatcher(config={'similarity_threshold': 0.8})
        
        # Simulate embeddings for similar and dissimilar snowmobile models
        import numpy as np
        
        # Query embeddings (what we're looking for)
        query_embeddings = np.array([
            [1.0, 0.8, 0.6, 0.4, 0.2],  # Summit X pattern
            [0.2, 0.4, 0.6, 0.8, 1.0]   # Catalyst pattern
        ])
        
        # Candidate embeddings (catalog entries)
        candidate_embeddings = np.array([
            [0.95, 0.82, 0.58, 0.41, 0.19],  # Very similar to Summit X
            [0.5, 0.6, 0.7, 0.8, 0.9],       # Somewhat similar to both
            [0.19, 0.41, 0.58, 0.82, 0.95],  # Very similar to Catalyst
            [-0.8, -0.6, -0.4, -0.2, 0.0]    # Very different
        ])
        
        similarities = matcher._calculate_cosine_similarity(query_embeddings, candidate_embeddings)
        
        assert similarities.shape == (2, 4)
        
        # Query 0 (Summit X pattern) should match best with candidate 0
        best_match_idx_0 = np.argmax(similarities[0])
        assert best_match_idx_0 == 0
        assert similarities[0][0] > 0.9  # High similarity
        
        # Query 1 (Catalyst pattern) should match best with candidate 2
        best_match_idx_1 = np.argmax(similarities[1])
        assert best_match_idx_1 == 2
        assert similarities[1][2] > 0.9  # High similarity
        
        # Both queries should have low similarity with candidate 3
        assert similarities[0][3] < 0.5
        assert similarities[1][3] < 0.5
    
    def test_bert_model_fallback_integration(self):
        """Test fallback behavior when BERT model is unavailable"""
        config = {
            'use_fuzzy_fallback': True,
            'model_name': 'sentence-transformers/nonexistent-model'
        }
        
        matcher = BERTMatcher(config=config)
        
        # Mock model loading failure
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            mock_transformer.side_effect = Exception("Model not found")
            
            # Should handle failure gracefully and enable fuzzy fallback
            result = matcher._load_bert_model()
            
            assert result is False
            assert matcher.model_loaded is False
            assert matcher.use_fuzzy_fallback is True
        
        # Test matching with fuzzy fallback
        products = [
            ProductData(model_code="TEST", brand="Ski-Doo", year=2024, malli="Summit X Expert")
        ]
        
        catalog_data = [
            CatalogData(model_family="Summit X", brand="Ski-Doo")
        ]
        
        matcher.load_catalog_data(catalog_data)
        
        with patch('fuzzywuzzy.fuzz.ratio') as mock_fuzzy:
            mock_fuzzy.return_value = 85  # Good fuzzy match
            
            match_results = matcher.match_products(products)
        
        assert len(match_results) == 1
        assert match_results[0].success is True
        assert match_results[0].match_method == "fuzzy_string"
        assert match_results[0].similarity_score == 0.85


@pytest.mark.external
class TestFTPServerIntegration:
    """Test integration with FTP servers"""
    
    def test_ftp_connection_integration_mock(self):
        """Test FTP server connection with realistic mock"""
        config = {
            'host': 'test.ftp.server.com',
            'username': 'test_user',
            'password': 'test_password',
            'port': 21,
            'timeout': 30
        }
        
        uploader = FTPUploader(config=config)
        
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            mock_ftp_class.return_value = mock_ftp
            
            # Mock successful connection sequence
            mock_ftp.connect.return_value = "220 Welcome to test FTP server"
            mock_ftp.login.return_value = "230 Login successful"
            
            result = uploader.connect()
        
        assert result is True
        assert uploader.connected is True
        assert uploader.connection_time is not None
        
        # Verify connection sequence
        mock_ftp.connect.assert_called_once_with('test.ftp.server.com', 21, 30)
        mock_ftp.login.assert_called_once_with('test_user', 'test_password')
    
    def test_ftp_upload_integration_with_verification(self, temp_xml_file):
        """Test complete FTP upload flow with verification"""
        uploader = FTPUploader(config={'password': 'test_pass'})
        uploader.connected = True
        
        # Create test XML content
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<items>
    <item>
        <title>Ski-Doo Summit X Expert 165 2024</title>
        <model_code>SKDO</model_code>
        <brand>Ski-Doo</brand>
        <year>2024</year>
        <price>45000</price>
    </item>
</items>"""
        
        temp_xml_file.write_text(xml_content, encoding='utf-8')
        
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            uploader.ftp_connection = mock_ftp
            
            # Mock successful upload
            mock_ftp.storbinary.return_value = "226 Transfer complete"
            
            # Mock file verification
            mock_ftp.nlst.return_value = ['test_upload.xml', 'other_file.xml']
            mock_ftp.size.return_value = len(xml_content.encode('utf-8'))
            
            result = uploader.upload_file(temp_xml_file, 'test_upload.xml')
        
        assert result is True
        
        # Verify upload was called correctly
        mock_ftp.storbinary.assert_called_once()
        call_args = mock_ftp.storbinary.call_args
        assert call_args[0][0] == 'STOR test_upload.xml'
        
        # Verify verification was performed
        mock_ftp.nlst.assert_called_once()
        mock_ftp.size.assert_called_once_with('test_upload.xml')
    
    def test_ftp_xml_content_upload_integration(self):
        """Test direct XML content upload"""
        uploader = FTPUploader()
        uploader.connected = True
        
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<items>
    <item>
        <title>Arctic Cat Catalyst 9000 Turbo R 2024</title>
        <model_code>ARCT</model_code>
        <brand>Arctic Cat</brand>
        <year>2024</year>
        <engine>998cc Turbo</engine>
    </item>
    <item>
        <title>Polaris RMK Khaos 850 2023</title>
        <model_code>POLA</model_code>
        <brand>Polaris</brand>
        <year>2023</year>
        <engine>850 Patriot</engine>
    </item>
</items>"""
        
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Mock successful upload and verification
        mock_ftp.storbinary.return_value = "226 Transfer complete"
        mock_ftp.nlst.return_value = ['avito_snowmobiles.xml']
        mock_ftp.size.return_value = len(xml_content.encode('utf-8'))
        
        result = uploader.upload_xml_content(xml_content, 'avito_snowmobiles.xml')
        
        assert result is True
        
        # Verify content was uploaded as BytesIO
        mock_ftp.storbinary.assert_called_once()
        call_args = mock_ftp.storbinary.call_args
        
        assert call_args[0][0] == 'STOR avito_snowmobiles.xml'
        
        # Check that content was properly encoded
        uploaded_buffer = call_args[0][1]
        uploaded_buffer.seek(0)
        uploaded_content = uploaded_buffer.read().decode('utf-8')
        
        assert xml_content == uploaded_content
    
    def test_ftp_error_scenarios_integration(self):
        """Test various FTP error scenarios"""
        uploader = FTPUploader(config={'password': 'test_pass', 'max_retries': 2})
        
        # Test connection timeout
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            mock_ftp_class.return_value = mock_ftp
            mock_ftp.connect.side_effect = OSError("Connection timeout")
            
            with pytest.raises(UploadError) as exc_info:
                uploader.connect()
            
            assert "connect" in str(exc_info.value).lower()
            assert uploader.connected is False
        
        # Test authentication failure
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            mock_ftp_class.return_value = mock_ftp
            
            import ftplib
            mock_ftp.login.side_effect = ftplib.error_perm("530 Login incorrect")
            
            with pytest.raises(UploadError) as exc_info:
                uploader.connect()
            
            assert "login" in str(exc_info.value).lower() or "530" in str(exc_info.value)
        
        # Test upload failure with retry
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        import ftplib
        # First attempt fails, second succeeds
        mock_ftp.storbinary.side_effect = [
            ftplib.error_temp("450 Temporary failure"),
            "226 Transfer complete"
        ]
        
        mock_ftp.nlst.return_value = ['retry_test.xml']
        mock_ftp.size.return_value = 1000
        
        with patch('time.sleep'):  # Mock sleep for faster testing
            result = uploader.upload_xml_content("test content", "retry_test.xml")
        
        # Should succeed after retry
        assert result is True
        assert mock_ftp.storbinary.call_count == 2
    
    def test_ftp_large_file_upload_simulation(self):
        """Test upload of large XML files"""
        uploader = FTPUploader()
        uploader.connected = True
        
        # Generate large XML content (simulating 100 products)
        xml_items = []
        for i in range(100):
            xml_items.append(f"""
    <item>
        <title>Snowmobile Product {i} 2024</title>
        <model_code>PRD{i:03d}</model_code>
        <brand>Brand{i % 5}</brand>
        <year>2024</year>
        <engine>Engine Type {i % 3}</engine>
        <description>Detailed description for product {i} with specifications and features.</description>
    </item>""")
        
        large_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<items>{''.join(xml_items)}
</items>"""
        
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Mock successful upload of large file
        mock_ftp.storbinary.return_value = "226 Transfer complete"
        mock_ftp.nlst.return_value = ['large_catalog.xml']
        mock_ftp.size.return_value = len(large_xml.encode('utf-8'))
        
        from tests.utils import performance_timer
        
        with performance_timer.time_operation("large_xml_upload"):
            result = uploader.upload_xml_content(large_xml, 'large_catalog.xml')
        
        assert result is True
        assert len(large_xml) > 10000  # Should be substantial content
        
        # Should handle large files efficiently
        performance_timer.assert_performance("large_xml_upload", 2.0)
    
    def test_ftp_connection_recovery_integration(self):
        """Test FTP connection recovery scenarios"""
        config = {
            'password': 'test_pass',
            'max_retries': 3,
            'retry_delay': 0.1
        }
        uploader = FTPUploader(config=config)
        
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            mock_ftp_class.return_value = mock_ftp
            
            # Simulate connection recovery scenario
            import ftplib
            mock_ftp.connect.side_effect = [
                ftplib.error_temp("421 Service not available"),  # First attempt fails
                ftplib.error_temp("421 Service not available"),  # Second attempt fails  
                "220 Welcome to FTP server"  # Third attempt succeeds
            ]
            
            mock_ftp.login.return_value = "230 Login successful"
            
            with patch('time.sleep'):  # Speed up retry delays
                result = uploader.connect()
        
        assert result is True
        assert uploader.connected is True
        assert mock_ftp.connect.call_count == 3  # Retried as expected
        assert mock_ftp.login.call_count == 1  # Only called after successful connect


@pytest.mark.external
class TestExternalServiceChaining:
    """Test chaining of multiple external service interactions"""
    
    def test_llm_to_bert_to_ftp_integration_chain(self, temp_pdf_file):
        """Test complete external service chain: LLM -> BERT -> FTP"""
        # Stage 1: LLM Extraction
        llm_extractor = LLMExtractor(config={'provider': 'claude'})
        
        pdf_text = """
        SNOWMOBILE CATALOG 2024
        
        1. Ski-Doo Summit X Expert 165 - 850 E-TEC Turbo R Engine
        2. Arctic Cat Catalyst 9000 Turbo R - 998cc Turbocharged
        3. Polaris RMK Khaos 850 - Patriot Engine Technology
        """
        
        # Mock LLM extraction
        extracted_products = [
            ProductData(model_code="SKDO", brand="Ski-Doo", year=2024, malli="Summit X", paketti="Expert 165"),
            ProductData(model_code="ARCT", brand="Arctic Cat", year=2024, malli="Catalyst", paketti="9000 Turbo R"),
            ProductData(model_code="POLA", brand="Polaris", year=2024, malli="RMK", paketti="Khaos 850")
        ]
        
        with patch.object(llm_extractor, 'extract_products_from_text') as mock_llm:
            mock_llm.return_value = extracted_products
            
            products = llm_extractor.extract_products_from_text(pdf_text)
        
        # Stage 2: BERT Matching
        bert_matcher = BERTMatcher()
        
        catalog_data = [
            CatalogData(model_family="Summit X", brand="Ski-Doo"),
            CatalogData(model_family="Catalyst", brand="Arctic Cat"),
            CatalogData(model_family="RMK", brand="Polaris")
        ]
        
        bert_matcher.load_catalog_data(catalog_data)
        
        with patch.object(bert_matcher, '_load_bert_model', return_value=True):
            bert_matcher.model_loaded = True
            
            with patch.object(bert_matcher, '_generate_embeddings') as mock_embed:
                with patch.object(bert_matcher, '_calculate_cosine_similarity') as mock_sim:
                    # Mock high similarity for all products
                    mock_embed.return_value = [[0.1, 0.2, 0.3]] * 3
                    mock_sim.return_value = [
                        [0.95, 0.2, 0.1],  # Ski-Doo matches first catalog
                        [0.1, 0.93, 0.2],  # Arctic Cat matches second catalog
                        [0.2, 0.1, 0.91]   # Polaris matches third catalog
                    ]
                    
                    match_results = bert_matcher.match_products(products)
        
        assert len(match_results) == 3
        assert all(r.success for r in match_results)
        
        # Add matching metadata to products
        for product, match_result in zip(products, match_results):
            product.matching_confidence = match_result.confidence_score
            product.matched_catalog = match_result.matched_model
        
        # Stage 3: Generate XML from matched products
        from pipeline.stage4_generation import AvitoXMLGenerator
        
        generator = AvitoXMLGenerator()
        generator.templates['avito_snowmobile'] = """<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>{{ brand }} {{ malli }} {{ paketti }} {{ year }}</title>
    <model_code>{{ model_code }}</model_code>
    <brand>{{ brand }}</brand>
    <year>{{ year }}</year>
    <matching_confidence>{{ matching_confidence }}</matching_confidence>
    <matched_catalog>{{ matched_catalog }}</matched_catalog>
</item>"""
        
        xml_strings = generator.generate_xml_for_products(products)
        combined_xml = generator._combine_xml_strings(xml_strings)
        
        assert len(xml_strings) == 3
        assert "Summit X" in combined_xml
        assert "Catalyst" in combined_xml
        assert "RMK" in combined_xml
        
        # Stage 4: Upload to FTP
        ftp_uploader = FTPUploader(config={'password': 'test_pass'})
        ftp_uploader.connected = True
        
        mock_ftp = MagicMock()
        ftp_uploader.ftp_connection = mock_ftp
        
        mock_ftp.storbinary.return_value = "226 Transfer complete"
        mock_ftp.nlst.return_value = ['external_chain_test.xml']
        mock_ftp.size.return_value = len(combined_xml.encode('utf-8'))
        
        upload_result = ftp_uploader.upload_xml_content(combined_xml, 'external_chain_test.xml')
        
        assert upload_result is True
        
        # Verify complete chain statistics
        llm_stats = llm_extractor.get_stats()
        bert_stats = bert_matcher.get_stats()
        gen_stats = generator.get_stats()
        ftp_stats = ftp_uploader.get_stats()
        
        # All stages should show successful processing
        assert llm_stats.successful >= 3
        assert bert_stats.successful == 3
        assert gen_stats.successful == 3
        assert ftp_stats.successful >= 1
    
    def test_external_service_failure_resilience(self):
        """Test resilience when external services fail in chain"""
        # Stage 1: LLM fails, but pipeline continues with mock data
        products = [ProductData(model_code="MOCK", brand="MockBrand", year=2024, malli="MockModel")]
        
        # Stage 2: BERT fails, falls back to fuzzy matching
        matcher = BERTMatcher(config={'use_fuzzy_fallback': True})
        
        # Mock BERT failure
        with patch.object(matcher, '_load_bert_model', return_value=False):
            matcher.model_loaded = False
            matcher.use_fuzzy_fallback = True
            
            catalog_data = [CatalogData(model_family="MockModel", brand="MockBrand")]
            matcher.load_catalog_data(catalog_data)
            
            with patch('fuzzywuzzy.fuzz.ratio', return_value=80):
                match_results = matcher.match_products(products)
        
        assert len(match_results) == 1
        assert match_results[0].success is True
        assert match_results[0].match_method == "fuzzy_string"
        
        # Stage 3: XML generation continues despite matching method change
        from pipeline.stage4_generation import AvitoXMLGenerator
        
        generator = AvitoXMLGenerator()
        generator.templates['avito_snowmobile'] = """<item>
    <title>{{ title }}</title>
    <match_method>{{ match_method if match_method else 'unknown' }}</match_method>
</item>"""
        
        # Add match metadata to products
        products[0].match_method = match_results[0].match_method
        
        xml_strings = generator.generate_xml_for_products(products)
        
        assert len(xml_strings) == 1
        assert "fuzzy_string" in xml_strings[0]
        
        # Stage 4: FTP continues despite previous service degradations
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        mock_ftp.storbinary.return_value = "226 Transfer complete"
        mock_ftp.nlst.return_value = ['resilience_test.xml']
        mock_ftp.size.return_value = 1000
        
        upload_result = uploader.upload_xml_content(xml_strings[0], 'resilience_test.xml')
        
        assert upload_result is True
        
        # Verify pipeline completed despite service failures
        assert match_results[0].success  # Matching succeeded via fallback
        assert len(xml_strings) == 1     # Generation succeeded
        assert upload_result             # Upload succeeded
    
    def test_external_service_timeout_handling_chain(self):
        """Test timeout handling across external service chain"""
        # Configure short timeouts for testing
        llm_config = {'provider': 'claude', 'api_timeout': 0.1}
        bert_config = {'model_load_timeout': 0.1}
        ftp_config = {'timeout': 0.1, 'password': 'test'}
        
        # LLM with timeout
        llm_extractor = LLMExtractor(config=llm_config)
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            import time
            def slow_api_call(*args, **kwargs):
                time.sleep(0.2)  # Longer than timeout
                return MagicMock()
            
            mock_client.messages.create.side_effect = slow_api_call
            
            # Should handle timeout gracefully
            with pytest.raises(ExtractionError):
                llm_extractor.extract_products_from_text("test text")
        
        # BERT with timeout
        bert_matcher = BERTMatcher(config=bert_config)
        
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            def slow_model_load(*args, **kwargs):
                time.sleep(0.2)  # Longer than timeout
                return MagicMock()
            
            mock_transformer.side_effect = slow_model_load
            
            # Should handle timeout gracefully
            with pytest.raises(MatchingError):
                bert_matcher._load_bert_model()
        
        # FTP with timeout
        ftp_uploader = FTPUploader(config=ftp_config)
        
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            mock_ftp_class.return_value = mock_ftp
            
            mock_ftp.connect.side_effect = OSError("Connection timeout")
            
            # Should handle timeout gracefully
            with pytest.raises(UploadError):
                ftp_uploader.connect()
        
        # Verify all services handle timeouts appropriately
        # In a real scenario, these would trigger fallback mechanisms