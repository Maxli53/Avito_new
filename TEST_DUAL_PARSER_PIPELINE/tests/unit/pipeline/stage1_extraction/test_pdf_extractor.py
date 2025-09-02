"""
Unit tests for PDF extraction functionality
Tests PDFExtractor class and PDF processing capabilities
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import tempfile

from pipeline.stage1_extraction import PDFExtractor
from pipeline.stage1_extraction.base_extractor import BaseExtractor
from core import ProductData, PipelineStats
from core.exceptions import ExtractionError
from tests.utils import file_helpers, FileTestHelpers, performance_timer
from tests.fixtures.sample_data import SampleDataFactory


class TestPDFExtractorInitialization:
    """Test PDFExtractor initialization and configuration"""
    
    def test_pdf_extractor_creation_default_config(self):
        """Test creating PDFExtractor with default configuration"""
        extractor = PDFExtractor()
        
        assert isinstance(extractor, PDFExtractor)
        assert isinstance(extractor, BaseExtractor)
        assert extractor.config is not None
        assert hasattr(extractor, 'stats')
        assert isinstance(extractor.stats, PipelineStats)
    
    def test_pdf_extractor_creation_custom_config(self):
        """Test creating PDFExtractor with custom configuration"""
        custom_config = {
            'use_ocr': True,
            'ocr_language': 'fin',
            'pdf_password': 'testpass',
            'extraction_timeout': 300,
            'use_fallback_extraction': True
        }
        
        extractor = PDFExtractor(config=custom_config)
        
        assert extractor.config['use_ocr'] is True
        assert extractor.config['ocr_language'] == 'fin'
        assert extractor.config['pdf_password'] == 'testpass'
        assert extractor.config['extraction_timeout'] == 300
        assert extractor.config['use_fallback_extraction'] is True
    
    def test_pdf_extractor_inheritance(self):
        """Test that PDFExtractor properly inherits from BaseExtractor"""
        extractor = PDFExtractor()
        
        # Should have BaseExtractor methods
        assert hasattr(extractor, 'extract_from_file')
        assert hasattr(extractor, 'get_stats')
        assert hasattr(extractor, 'reset_stats')
        assert callable(extractor.extract_from_file)


class TestPDFTextExtraction:
    """Test PDF text extraction functionality"""
    
    def test_extract_text_from_valid_pdf(self, temp_pdf_file):
        """Test extracting text from a valid PDF file"""
        extractor = PDFExtractor()
        
        # Mock PyPDF2 extraction
        with patch('PyPDF2.PdfReader') as mock_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Test PDF content with snowmobile data"
            mock_reader.return_value.pages = [mock_page]
            
            extracted_text = extractor._extract_text_pypdf2(temp_pdf_file)
            
            assert "Test PDF content" in extracted_text
            assert "snowmobile data" in extracted_text
    
    def test_extract_text_from_password_protected_pdf(self, temp_pdf_file):
        """Test extracting text from password-protected PDF"""
        config = {'pdf_password': 'testpass'}
        extractor = PDFExtractor(config=config)
        
        with patch('PyPDF2.PdfReader') as mock_reader:
            mock_reader.return_value.is_encrypted = True
            mock_reader.return_value.decrypt.return_value = True
            
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Protected PDF content"
            mock_reader.return_value.pages = [mock_page]
            
            extracted_text = extractor._extract_text_pypdf2(temp_pdf_file)
            
            assert "Protected PDF content" in extracted_text
            mock_reader.return_value.decrypt.assert_called_once_with('testpass')
    
    def test_extract_text_wrong_password(self, temp_pdf_file):
        """Test handling of wrong PDF password"""
        config = {'pdf_password': 'wrongpass'}
        extractor = PDFExtractor(config=config)
        
        with patch('PyPDF2.PdfReader') as mock_reader:
            mock_reader.return_value.is_encrypted = True
            mock_reader.return_value.decrypt.return_value = False  # Wrong password
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor._extract_text_pypdf2(temp_pdf_file)
            
            assert "password" in str(exc_info.value).lower()
            assert exc_info.value.details['file_path'] == str(temp_pdf_file)
    
    def test_extract_text_fallback_to_pdfplumber(self, temp_pdf_file):
        """Test fallback to pdfplumber when PyPDF2 fails"""
        extractor = PDFExtractor(config={'use_fallback_extraction': True})
        
        with patch('PyPDF2.PdfReader') as mock_pypdf2:
            mock_pypdf2.side_effect = Exception("PyPDF2 failed")
            
            with patch('pdfplumber.open') as mock_pdfplumber:
                mock_page = MagicMock()
                mock_page.extract_text.return_value = "Pdfplumber extracted content"
                mock_pdfplumber.return_value.__enter__.return_value.pages = [mock_page]
                
                extracted_text = extractor._extract_text_with_fallback(temp_pdf_file)
                
                assert "Pdfplumber extracted content" in extracted_text
    
    def test_extract_text_with_ocr_fallback(self, temp_pdf_file):
        """Test OCR fallback when text extraction fails"""
        config = {
            'use_ocr': True,
            'ocr_language': 'eng',
            'use_fallback_extraction': True
        }
        extractor = PDFExtractor(config=config)
        
        # Mock both text extraction methods failing
        with patch('PyPDF2.PdfReader') as mock_pypdf2:
            mock_pypdf2.side_effect = Exception("Text extraction failed")
            
            with patch('pdfplumber.open') as mock_pdfplumber:
                mock_pdfplumber.side_effect = Exception("Fallback failed")
                
                with patch('pdf2image.convert_from_path') as mock_pdf2image:
                    mock_image = MagicMock()
                    mock_pdf2image.return_value = [mock_image]
                    
                    with patch('pytesseract.image_to_string') as mock_ocr:
                        mock_ocr.return_value = "OCR extracted snowmobile data"
                        
                        extracted_text = extractor._extract_text_with_ocr(temp_pdf_file)
                        
                        assert "OCR extracted snowmobile data" in extracted_text
                        mock_ocr.assert_called_once()


class TestProductDataExtraction:
    """Test product data extraction from PDF text"""
    
    def test_extract_products_from_text_llm_success(self):
        """Test successful product extraction using LLM"""
        extractor = PDFExtractor(config={'llm_provider': 'claude'})
        
        sample_text = """
        Model: Summit X Expert 165
        Code: S1BX
        Brand: Ski-Doo
        Year: 2024
        Engine: 850 E-TEC Turbo R
        Track: 3.0
        Color: Octane Blue/Black
        """
        
        # Mock LLM extraction
        with patch.object(extractor, '_extract_with_llm') as mock_llm:
            mock_llm.return_value = [
                ProductData(
                    model_code="S1BX",
                    brand="Ski-Doo", 
                    year=2024,
                    malli="Summit X",
                    paketti="Expert 165",
                    moottori="850 E-TEC Turbo R",
                    telamatto="3.0",
                    vari="Octane Blue/Black"
                )
            ]
            
            products = extractor._extract_products_from_text(sample_text)
            
            assert len(products) == 1
            assert products[0].model_code == "S1BX"
            assert products[0].brand == "Ski-Doo"
            assert products[0].year == 2024
    
    def test_extract_products_llm_fallback_to_regex(self):
        """Test fallback to regex when LLM extraction fails"""
        config = {
            'llm_provider': 'claude',
            'use_regex_fallback': True
        }
        extractor = PDFExtractor(config=config)
        
        sample_text = """
        Model Code: LYNX Brand: Lynx Year: 2023
        Model: Ranger Package: RE 600R E-TEC
        """
        
        # Mock LLM failure
        with patch.object(extractor, '_extract_with_llm') as mock_llm:
            mock_llm.side_effect = ExtractionError("LLM failed")
            
            with patch.object(extractor, '_extract_with_regex') as mock_regex:
                mock_regex.return_value = [
                    ProductData(
                        model_code="LYNX",
                        brand="Lynx",
                        year=2023,
                        malli="Ranger",
                        paketti="RE 600R E-TEC"
                    )
                ]
                
                products = extractor._extract_products_from_text(sample_text)
                
                assert len(products) == 1
                assert products[0].model_code == "LYNX"
                mock_regex.assert_called_once()
    
    def test_extract_products_regex_patterns(self):
        """Test regex pattern extraction"""
        extractor = PDFExtractor()
        
        # Text with clear patterns
        sample_text = """
        Model Code: ARCT
        Brand: Arctic Cat
        Year: 2024
        Model: Catalyst
        Package: 9000 Turbo R
        Engine: 998cc Turbo
        Track Width: 3.0
        Starter: Electric
        Color: Team Arctic Green
        """
        
        products = extractor._extract_with_regex(sample_text)
        
        assert len(products) >= 1
        product = products[0]
        assert product.model_code == "ARCT"
        assert product.brand == "Arctic Cat"
        assert product.year == 2024
        assert product.malli == "Catalyst"
    
    def test_extract_products_multiple_products_in_text(self):
        """Test extracting multiple products from single text"""
        extractor = PDFExtractor()
        
        sample_text = """
        Product 1:
        Model Code: PRD1
        Brand: Polaris
        Year: 2024
        Model: RMK
        
        Product 2:
        Model Code: PRD2
        Brand: Yamaha
        Year: 2023  
        Model: Sidewinder
        """
        
        with patch.object(extractor, '_extract_with_regex') as mock_regex:
            mock_regex.return_value = [
                ProductData(model_code="PRD1", brand="Polaris", year=2024, malli="RMK"),
                ProductData(model_code="PRD2", brand="Yamaha", year=2023, malli="Sidewinder")
            ]
            
            products = extractor._extract_products_from_text(sample_text)
            
            assert len(products) == 2
            assert products[0].model_code == "PRD1"
            assert products[1].model_code == "PRD2"


class TestLLMIntegration:
    """Test LLM integration for product extraction"""
    
    def test_llm_extraction_claude_success(self):
        """Test successful Claude LLM extraction"""
        config = {
            'llm_provider': 'claude',
            'claude_model': 'claude-3-sonnet-20240229',
            'max_tokens': 4000
        }
        extractor = PDFExtractor(config=config)
        
        sample_text = "Ski-Doo Summit X 2024 with 850 E-TEC engine"
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.content[0].text = '''[{
                "model_code": "SKDO",
                "brand": "Ski-Doo",
                "year": 2024,
                "malli": "Summit X",
                "moottori": "850 E-TEC"
            }]'''
            
            mock_client.messages.create.return_value = mock_response
            
            products = extractor._extract_with_llm(sample_text, 'claude')
            
            assert len(products) == 1
            assert products[0].brand == "Ski-Doo"
            assert products[0].year == 2024
    
    def test_llm_extraction_gpt_success(self):
        """Test successful GPT LLM extraction"""
        config = {
            'llm_provider': 'gpt',
            'gpt_model': 'gpt-4',
            'max_tokens': 3000
        }
        extractor = PDFExtractor(config=config)
        
        sample_text = "Arctic Cat Catalyst 9000 Turbo R 2024"
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices[0].message.content = '''[{
                "model_code": "ARCT",
                "brand": "Arctic Cat", 
                "year": 2024,
                "malli": "Catalyst",
                "paketti": "9000 Turbo R"
            }]'''
            
            mock_client.chat.completions.create.return_value = mock_response
            
            products = extractor._extract_with_llm(sample_text, 'gpt')
            
            assert len(products) == 1
            assert products[0].brand == "Arctic Cat"
            assert products[0].malli == "Catalyst"
    
    def test_llm_extraction_invalid_json_response(self):
        """Test handling of invalid JSON from LLM"""
        extractor = PDFExtractor(config={'llm_provider': 'claude'})
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.content[0].text = "Invalid JSON response from LLM"
            
            mock_client.messages.create.return_value = mock_response
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor._extract_with_llm("test text", 'claude')
            
            assert "json" in str(exc_info.value).lower()
    
    def test_llm_extraction_api_timeout(self):
        """Test handling of LLM API timeouts"""
        extractor = PDFExtractor(config={'llm_provider': 'claude', 'api_timeout': 5})
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            # Simulate timeout
            import requests
            mock_client.messages.create.side_effect = requests.Timeout("API timeout")
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor._extract_with_llm("test text", 'claude')
            
            assert "timeout" in str(exc_info.value).lower()


class TestPDFExtractorEndToEnd:
    """End-to-end tests for PDF extraction workflow"""
    
    def test_extract_from_file_complete_workflow(self, temp_pdf_file):
        """Test complete extraction workflow from PDF file"""
        extractor = PDFExtractor(config={'llm_provider': 'mock'})
        
        # Mock the entire extraction pipeline
        with patch.object(extractor, '_extract_text_pypdf2') as mock_text:
            mock_text.return_value = "Ski-Doo Summit X 2024 850 E-TEC"
            
            with patch.object(extractor, '_extract_products_from_text') as mock_products:
                mock_products.return_value = [
                    ProductData(
                        model_code="TEST",
                        brand="Ski-Doo",
                        year=2024,
                        malli="Summit X",
                        moottori="850 E-TEC"
                    )
                ]
                
                products = extractor.extract_from_file(temp_pdf_file)
                
                assert len(products) == 1
                assert products[0].model_code == "TEST"
                assert products[0].brand == "Ski-Doo"
                
                # Verify stats were updated
                stats = extractor.get_stats()
                assert stats.successful == 1
                assert stats.total_processed == 1
    
    def test_extract_with_hooks_success(self, temp_pdf_file):
        """Test extraction with hooks (preprocessing and postprocessing)"""
        extractor = PDFExtractor()
        
        # Mock hooks
        def preprocess_hook(file_path):
            return {"validated": True, "file_size": file_path.stat().st_size}
        
        def postprocess_hook(products, metadata):
            for product in products:
                product.extraction_metadata = metadata
            return products
        
        extractor.add_preprocessing_hook(preprocess_hook)
        extractor.add_postprocessing_hook(postprocess_hook)
        
        with patch.object(extractor, 'extract_from_file') as mock_extract:
            mock_product = ProductData(model_code="HOOK", brand="Test", year=2024)
            mock_extract.return_value = [mock_product]
            
            products = extractor.extract_with_hooks(temp_pdf_file)
            
            assert len(products) == 1
            assert hasattr(products[0], 'extraction_metadata')
            assert products[0].extraction_metadata['validated'] is True
    
    def test_extract_from_nonexistent_file(self):
        """Test extraction from nonexistent file"""
        extractor = PDFExtractor()
        nonexistent_file = Path("/path/to/nonexistent/file.pdf")
        
        with pytest.raises(ExtractionError) as exc_info:
            extractor.extract_from_file(nonexistent_file)
        
        assert "not found" in str(exc_info.value).lower() or "does not exist" in str(exc_info.value).lower()
        assert exc_info.value.details['file_path'] == str(nonexistent_file)
    
    def test_extract_from_invalid_pdf(self, temp_pdf_file):
        """Test extraction from invalid/corrupted PDF"""
        extractor = PDFExtractor()
        
        # Write invalid PDF content
        with open(temp_pdf_file, 'wb') as f:
            f.write(b"This is not a valid PDF file")
        
        with pytest.raises(ExtractionError) as exc_info:
            extractor.extract_from_file(temp_pdf_file)
        
        assert "pdf" in str(exc_info.value).lower()
        assert exc_info.value.details['file_path'] == str(temp_pdf_file)


class TestPDFExtractorPerformance:
    """Performance tests for PDF extraction"""
    
    @pytest.mark.performance
    def test_extraction_performance_small_pdf(self, temp_pdf_file):
        """Test extraction performance for small PDF"""
        extractor = PDFExtractor()
        
        with patch.object(extractor, '_extract_text_pypdf2') as mock_text:
            mock_text.return_value = "Small PDF content"
            
            with patch.object(extractor, '_extract_products_from_text') as mock_products:
                mock_products.return_value = [
                    ProductData(model_code="PERF", brand="Performance", year=2024)
                ]
                
                with performance_timer.time_operation("small_pdf_extraction"):
                    products = extractor.extract_from_file(temp_pdf_file)
                
                assert len(products) == 1
                
                # Should complete quickly (less than 1 second)
                performance_timer.assert_performance("small_pdf_extraction", 1.0)
    
    @pytest.mark.performance
    def test_extraction_performance_multiple_pages(self, temp_pdf_file):
        """Test extraction performance for multi-page PDF"""
        extractor = PDFExtractor()
        
        # Simulate multi-page PDF
        with patch.object(extractor, '_extract_text_pypdf2') as mock_text:
            # Simulate larger content from multiple pages
            mock_text.return_value = "Page 1 content\n" * 100 + "Page 2 content\n" * 100
            
            with patch.object(extractor, '_extract_products_from_text') as mock_products:
                mock_products.return_value = [
                    ProductData(model_code=f"P{i:03d}", brand="Test", year=2024) 
                    for i in range(5)  # 5 products
                ]
                
                with performance_timer.time_operation("multipage_pdf_extraction"):
                    products = extractor.extract_from_file(temp_pdf_file)
                
                assert len(products) == 5
                
                # Should handle multi-page efficiently (less than 2 seconds)
                performance_timer.assert_performance("multipage_pdf_extraction", 2.0)


class TestPDFExtractorConfiguration:
    """Test various configuration options"""
    
    def test_extraction_timeout_configuration(self, temp_pdf_file):
        """Test extraction timeout configuration"""
        config = {'extraction_timeout': 0.001}  # Very short timeout
        extractor = PDFExtractor(config=config)
        
        # Mock slow extraction
        with patch.object(extractor, '_extract_text_pypdf2') as mock_text:
            import time
            
            def slow_extraction(*args, **kwargs):
                time.sleep(0.1)  # Longer than timeout
                return "Slow extraction"
            
            mock_text.side_effect = slow_extraction
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_from_file(temp_pdf_file)
            
            assert "timeout" in str(exc_info.value).lower()
    
    def test_ocr_language_configuration(self, temp_pdf_file):
        """Test OCR language configuration"""
        config = {
            'use_ocr': True,
            'ocr_language': 'fin+eng',  # Finnish and English
            'use_fallback_extraction': True
        }
        extractor = PDFExtractor(config=config)
        
        # Mock text extraction failure to trigger OCR
        with patch.object(extractor, '_extract_text_pypdf2') as mock_text:
            mock_text.side_effect = Exception("Text extraction failed")
            
            with patch('pdf2image.convert_from_path') as mock_pdf2image:
                mock_pdf2image.return_value = [MagicMock()]
                
                with patch('pytesseract.image_to_string') as mock_ocr:
                    mock_ocr.return_value = "OCR extracted text"
                    
                    text = extractor._extract_text_with_ocr(temp_pdf_file)
                    
                    assert "OCR extracted text" in text
                    # Verify OCR was called with correct language
                    call_args = mock_ocr.call_args
                    assert 'lang' in call_args.kwargs
                    assert call_args.kwargs['lang'] == 'fin+eng'
    
    def test_llm_provider_switching(self):
        """Test switching between LLM providers"""
        # Test Claude configuration
        claude_config = {
            'llm_provider': 'claude',
            'claude_api_key': 'test_claude_key'
        }
        claude_extractor = PDFExtractor(config=claude_config)
        assert claude_extractor.config['llm_provider'] == 'claude'
        
        # Test GPT configuration  
        gpt_config = {
            'llm_provider': 'gpt',
            'openai_api_key': 'test_gpt_key'
        }
        gpt_extractor = PDFExtractor(config=gpt_config)
        assert gpt_extractor.config['llm_provider'] == 'gpt'
        
        # Test fallback to regex
        no_llm_config = {
            'llm_provider': None,
            'use_regex_fallback': True
        }
        regex_extractor = PDFExtractor(config=no_llm_config)
        assert regex_extractor.config['use_regex_fallback'] is True


class TestPDFExtractorErrorHandling:
    """Test comprehensive error handling scenarios"""
    
    def test_memory_error_handling(self, temp_pdf_file):
        """Test handling of memory errors during extraction"""
        extractor = PDFExtractor()
        
        with patch.object(extractor, '_extract_text_pypdf2') as mock_text:
            mock_text.side_effect = MemoryError("Insufficient memory")
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_from_file(temp_pdf_file)
            
            assert "memory" in str(exc_info.value).lower()
            assert isinstance(exc_info.value.original_exception, MemoryError)
    
    def test_unicode_error_handling(self, temp_pdf_file):
        """Test handling of Unicode decode errors"""
        extractor = PDFExtractor()
        
        with patch.object(extractor, '_extract_text_pypdf2') as mock_text:
            mock_text.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')
            
            with pytest.raises(ExtractionError) as exc_info:
                extractor.extract_from_file(temp_pdf_file)
            
            assert "unicode" in str(exc_info.value).lower() or "encoding" in str(exc_info.value).lower()
    
    def test_permission_error_handling(self):
        """Test handling of file permission errors"""
        extractor = PDFExtractor()
        
        # Try to access a file without permissions
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            
            with patch('builtins.open') as mock_open:
                mock_open.side_effect = PermissionError("Permission denied")
                
                restricted_file = Path("/restricted/file.pdf")
                
                with pytest.raises(ExtractionError) as exc_info:
                    extractor.extract_from_file(restricted_file)
                
                assert "permission" in str(exc_info.value).lower()
                assert exc_info.value.details['file_path'] == str(restricted_file)