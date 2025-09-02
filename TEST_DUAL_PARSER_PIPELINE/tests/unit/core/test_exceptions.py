"""
Unit tests for core exception classes
Tests PipelineError and all stage-specific exceptions
"""

import pytest
from pathlib import Path

from core.exceptions import (
    PipelineError, ExtractionError, MatchingError, ValidationError, 
    GenerationError, UploadError, DatabaseError
)


class TestPipelineError:
    """Test base PipelineError class"""
    
    def test_basic_pipeline_error(self):
        """Test basic PipelineError creation"""
        error = PipelineError(
            message="Test pipeline error",
            stage="test_stage"
        )
        
        assert str(error) == "Test pipeline error"
        assert error.stage == "test_stage"
        assert error.details == {}
        assert error.original_exception is None
    
    def test_pipeline_error_with_details(self):
        """Test PipelineError with additional details"""
        details = {
            "file_path": "/test/path.pdf", 
            "line_number": 42,
            "context": "test_context"
        }
        
        error = PipelineError(
            message="Detailed error",
            stage="test",
            details=details
        )
        
        assert error.details == details
        assert error.details["file_path"] == "/test/path.pdf"
        assert error.details["line_number"] == 42
    
    def test_pipeline_error_with_original_exception(self):
        """Test PipelineError wrapping another exception"""
        original = ValueError("Original error message")
        
        error = PipelineError(
            message="Wrapped error",
            stage="test",
            original_exception=original
        )
        
        assert error.original_exception is original
        assert "Original error message" in str(error.original_exception)
    
    def test_pipeline_error_repr(self):
        """Test PipelineError string representation"""
        error = PipelineError(
            message="Test error",
            stage="test_stage",
            details={"key": "value"}
        )
        
        repr_str = repr(error)
        assert "PipelineError" in repr_str
        assert "test_stage" in repr_str
        assert "Test error" in repr_str


class TestExtractionError:
    """Test ExtractionError class"""
    
    def test_extraction_error_basic(self):
        """Test basic ExtractionError creation"""
        error = ExtractionError(
            message="PDF extraction failed"
        )
        
        assert str(error) == "PDF extraction failed"
        assert error.stage == "extraction"
        assert isinstance(error, PipelineError)
    
    def test_extraction_error_with_file_info(self):
        """Test ExtractionError with file information"""
        error = ExtractionError(
            message="Failed to extract from PDF", 
            file_path="/test/document.pdf",
            page_number=5,
            extraction_method="llm_claude"
        )
        
        assert error.details["file_path"] == "/test/document.pdf"
        assert error.details["page_number"] == 5
        assert error.details["extraction_method"] == "llm_claude"
    
    def test_extraction_error_with_llm_details(self):
        """Test ExtractionError with LLM-specific details"""
        error = ExtractionError(
            message="LLM extraction timeout",
            llm_provider="claude",
            prompt_tokens=1500,
            response_tokens=0,
            extraction_method="llm_claude"
        )
        
        assert error.details["llm_provider"] == "claude"
        assert error.details["prompt_tokens"] == 1500
        assert error.details["response_tokens"] == 0
    
    def test_extraction_error_chaining(self):
        """Test ExtractionError exception chaining"""
        original = ConnectionError("API connection failed")
        
        error = ExtractionError(
            message="Extraction failed due to API error",
            llm_provider="gpt",
            original_exception=original
        )
        
        assert error.original_exception is original
        assert isinstance(error.original_exception, ConnectionError)


class TestMatchingError:
    """Test MatchingError class"""
    
    def test_matching_error_basic(self):
        """Test basic MatchingError creation"""
        error = MatchingError(
            message="Semantic matching failed"
        )
        
        assert str(error) == "Semantic matching failed"
        assert error.stage == "matching"
    
    def test_matching_error_with_model_info(self):
        """Test MatchingError with model details"""
        error = MatchingError(
            message="BERT model loading failed",
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            similarity_threshold=0.8,
            matching_method="bert_semantic"
        )
        
        assert error.details["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert error.details["similarity_threshold"] == 0.8
        assert error.details["matching_method"] == "bert_semantic"
    
    def test_matching_error_with_product_info(self):
        """Test MatchingError with product context"""
        error = MatchingError(
            message="No suitable matches found",
            query_text="Summit X Expert 165",
            candidate_count=147,
            best_score=0.65,
            similarity_threshold=0.8
        )
        
        assert error.details["query_text"] == "Summit X Expert 165"
        assert error.details["candidate_count"] == 147
        assert error.details["best_score"] == 0.65
        assert error.details["similarity_threshold"] == 0.8


class TestValidationError:
    """Test ValidationError class"""
    
    def test_validation_error_basic(self):
        """Test basic ValidationError creation"""
        error = ValidationError(
            message="Product validation failed"
        )
        
        assert str(error) == "Product validation failed"
        assert error.stage == "validation"
    
    def test_validation_error_with_field_details(self):
        """Test ValidationError with field validation details"""
        error = ValidationError(
            message="Multiple field validation failures",
            failed_fields=["model_code", "year", "price"],
            validation_rules=["format_check", "range_check", "type_check"],
            model_code="INVALID_CODE"
        )
        
        assert error.details["failed_fields"] == ["model_code", "year", "price"]
        assert error.details["validation_rules"] == ["format_check", "range_check", "type_check"]
        assert error.details["model_code"] == "INVALID_CODE"
    
    def test_validation_error_with_brp_context(self):
        """Test ValidationError with BRP model validation context"""
        error = ValidationError(
            message="BRP model validation failed",
            model_code="UNKN",
            brp_database_count=267,
            matched_models=[],
            confidence_threshold=0.7
        )
        
        assert error.details["model_code"] == "UNKN"
        assert error.details["brp_database_count"] == 267
        assert error.details["matched_models"] == []
        assert error.details["confidence_threshold"] == 0.7


class TestGenerationError:
    """Test GenerationError class"""
    
    def test_generation_error_basic(self):
        """Test basic GenerationError creation"""
        error = GenerationError(
            message="XML generation failed"
        )
        
        assert str(error) == "XML generation failed"
        assert error.stage == "generation"
    
    def test_generation_error_with_template_info(self):
        """Test GenerationError with template details"""
        error = GenerationError(
            message="Template rendering failed",
            template_name="avito_snowmobile.xml.j2",
            template_path="/templates/avito_snowmobile.xml.j2",
            product_count=5
        )
        
        assert error.details["template_name"] == "avito_snowmobile.xml.j2"
        assert error.details["template_path"] == "/templates/avito_snowmobile.xml.j2"
        assert error.details["product_count"] == 5
    
    def test_generation_error_with_xml_validation(self):
        """Test GenerationError with XML validation details"""
        error = GenerationError(
            message="Generated XML is invalid",
            template_name="test.xml.j2", 
            xml_length=1024,
            validation_errors=["Missing required element", "Invalid attribute"]
        )
        
        assert error.details["xml_length"] == 1024
        assert error.details["validation_errors"] == ["Missing required element", "Invalid attribute"]


class TestUploadError:
    """Test UploadError class"""
    
    def test_upload_error_basic(self):
        """Test basic UploadError creation"""
        error = UploadError(
            message="FTP upload failed"
        )
        
        assert str(error) == "FTP upload failed"
        assert error.stage == "upload"
    
    def test_upload_error_with_server_info(self):
        """Test UploadError with server connection details"""
        error = UploadError(
            message="Connection to FTP server failed",
            server_host="ftp.avito.ru",
            server_port=21,
            username="user123456",
            connection_timeout=30
        )
        
        assert error.details["server_host"] == "ftp.avito.ru"
        assert error.details["server_port"] == 21
        assert error.details["username"] == "user123456" 
        assert error.details["connection_timeout"] == 30
    
    def test_upload_error_with_file_info(self):
        """Test UploadError with file upload details"""
        error = UploadError(
            message="File upload failed",
            server_host="test.ftp.com",
            upload_path="/remote/path/file.xml",
            file_size=2048,
            bytes_transferred=1024
        )
        
        assert error.details["server_host"] == "test.ftp.com"
        assert error.details["upload_path"] == "/remote/path/file.xml"
        assert error.details["file_size"] == 2048
        assert error.details["bytes_transferred"] == 1024
    
    def test_upload_error_authentication(self):
        """Test UploadError with authentication details"""
        error = UploadError(
            message="Authentication failed",
            server_host="secure.ftp.com",
            username="user123",
            auth_method="password",
            retry_count=3
        )
        
        assert error.details["server_host"] == "secure.ftp.com"
        assert error.details["username"] == "user123"
        assert error.details["auth_method"] == "password"
        assert error.details["retry_count"] == 3


class TestDatabaseError:
    """Test DatabaseError class"""
    
    def test_database_error_basic(self):
        """Test basic DatabaseError creation"""
        error = DatabaseError(
            message="Database connection failed"
        )
        
        assert str(error) == "Database connection failed"
        assert error.stage == "database"
    
    def test_database_error_with_connection_info(self):
        """Test DatabaseError with connection details"""
        error = DatabaseError(
            message="SQLite connection failed",
            database_path="/path/to/database.db",
            operation="SELECT",
            table_name="product_data"
        )
        
        assert error.details["database_path"] == "/path/to/database.db"
        assert error.details["operation"] == "SELECT"
        assert error.details["table_name"] == "product_data"
    
    def test_database_error_with_sql_details(self):
        """Test DatabaseError with SQL query details"""
        sql_query = "SELECT * FROM product_data WHERE model_code = ?"
        
        error = DatabaseError(
            message="SQL query execution failed",
            database_path="test.db",
            sql_query=sql_query,
            sql_parameters=["TEST"],
            affected_rows=0
        )
        
        assert error.details["sql_query"] == sql_query
        assert error.details["sql_parameters"] == ["TEST"] 
        assert error.details["affected_rows"] == 0
    
    def test_database_error_with_integrity_violation(self):
        """Test DatabaseError for integrity violations"""
        error = DatabaseError(
            message="Unique constraint violation",
            database_path="integrity.db",
            table_name="product_data",
            constraint_name="unique_model_code",
            conflicting_value="DUPL"
        )
        
        assert error.details["table_name"] == "product_data"
        assert error.details["constraint_name"] == "unique_model_code"
        assert error.details["conflicting_value"] == "DUPL"


class TestExceptionHierarchy:
    """Test exception hierarchy and inheritance"""
    
    def test_all_exceptions_inherit_from_pipeline_error(self):
        """Test that all custom exceptions inherit from PipelineError"""
        exception_classes = [
            ExtractionError, MatchingError, ValidationError,
            GenerationError, UploadError, DatabaseError
        ]
        
        for exception_class in exception_classes:
            assert issubclass(exception_class, PipelineError)
            assert issubclass(exception_class, Exception)
    
    def test_exception_catching_hierarchy(self):
        """Test that exceptions can be caught at different levels"""
        # Specific exception can be caught specifically
        with pytest.raises(ExtractionError):
            raise ExtractionError("Specific extraction error")
        
        # Specific exception can be caught as PipelineError
        with pytest.raises(PipelineError):
            raise ValidationError("Validation error caught as pipeline error")
        
        # Specific exception can be caught as generic Exception
        with pytest.raises(Exception):
            raise UploadError("Upload error caught as generic exception")
    
    def test_exception_context_preservation(self):
        """Test that exception context is preserved through inheritance"""
        original = ValueError("Original validation issue")
        
        validation_error = ValidationError(
            message="Validation wrapper",
            model_code="TEST",
            original_exception=original
        )
        
        # Context should be preserved
        assert validation_error.details["model_code"] == "TEST"
        assert validation_error.original_exception is original
        assert validation_error.stage == "validation"
        
        # Should still be catchable as PipelineError
        try:
            raise validation_error
        except PipelineError as pe:
            assert pe.stage == "validation"
            assert pe.original_exception is original


class TestExceptionIntegration:
    """Integration tests for exception handling"""
    
    def test_exception_error_reporting(self):
        """Test comprehensive error reporting"""
        error = ExtractionError(
            message="Complex extraction failure",
            file_path="/complex/path/document.pdf",
            page_number=15,
            extraction_method="llm_gpt",
            llm_provider="openai",
            prompt_tokens=2048,
            response_tokens=0,
            original_exception=TimeoutError("API timeout after 30s")
        )
        
        # Should contain all relevant information for debugging
        error_details = error.details
        assert error_details["file_path"] == "/complex/path/document.pdf"
        assert error_details["page_number"] == 15
        assert error_details["extraction_method"] == "llm_gpt"
        assert error_details["llm_provider"] == "openai"
        assert error_details["prompt_tokens"] == 2048
        assert error_details["response_tokens"] == 0
        
        # Original exception should be preserved
        assert isinstance(error.original_exception, TimeoutError)
        assert "API timeout" in str(error.original_exception)
    
    def test_exception_serialization(self):
        """Test that exceptions can be serialized for logging"""
        error = MatchingError(
            message="BERT matching failed",
            model_name="test-model",
            similarity_threshold=0.8,
            query_text="Test Query",
            candidate_count=50
        )
        
        # Should be able to convert to dict for JSON serialization
        error_dict = {
            "message": str(error),
            "stage": error.stage,
            "details": error.details,
            "exception_type": error.__class__.__name__
        }
        
        assert error_dict["message"] == "BERT matching failed"
        assert error_dict["stage"] == "matching"
        assert error_dict["details"]["model_name"] == "test-model"
        assert error_dict["exception_type"] == "MatchingError"
    
    def test_exception_logging_integration(self):
        """Test exception integration with logging system"""
        import logging
        import io
        
        # Capture log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger("test_exception")
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        error = GenerationError(
            message="Template error",
            template_name="test.xml.j2",
            product_count=3
        )
        
        try:
            raise error
        except GenerationError as ge:
            logger.error(f"Pipeline error in {ge.stage}: {ge}", exc_info=True)
        
        log_output = log_capture.getvalue()
        
        # Should contain error details
        assert "Pipeline error in generation" in log_output
        assert "Template error" in log_output
        assert "GenerationError" in log_output
        
        # Cleanup
        logger.removeHandler(handler)