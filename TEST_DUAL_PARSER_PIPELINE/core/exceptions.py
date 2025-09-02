"""
Custom Exception Classes for Avito Pipeline
Provides specific exception types for different pipeline stages and error conditions
"""

from typing import Dict, Any, Optional


class PipelineError(Exception):
    """
    Base exception class for all pipeline errors
    
    Attributes:
        message: Error message
        stage: Pipeline stage where error occurred
        details: Additional error details
        original_exception: Original exception that caused this error
    """
    
    def __init__(
        self, 
        message: str, 
        stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.stage = stage
        self.details = details or {}
        self.original_exception = original_exception
        
        # Create full error message
        full_message = message
        if stage:
            full_message = f"[{stage.upper()}] {message}"
        
        super().__init__(full_message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'stage': self.stage,
            'details': self.details,
            'original_exception': str(self.original_exception) if self.original_exception else None
        }


class ExtractionError(PipelineError):
    """
    Exception raised during data extraction stage
    
    Common causes:
    - PDF parsing failures
    - Invalid file formats
    - Missing required fields
    - LLM API failures
    """
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        page_number: Optional[int] = None,
        extraction_method: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        details = {}
        if file_path:
            details['file_path'] = file_path
        if page_number:
            details['page_number'] = page_number
        if extraction_method:
            details['extraction_method'] = extraction_method
            
        super().__init__(
            message=message,
            stage="extraction",
            details=details,
            original_exception=original_exception
        )


class MatchingError(PipelineError):
    """
    Exception raised during matching stage
    
    Common causes:
    - BERT model loading failures
    - Similarity calculation errors
    - Missing catalog data
    - Claude API failures
    """
    
    def __init__(
        self,
        message: str,
        product_code: Optional[str] = None,
        matching_method: Optional[str] = None,
        confidence_score: Optional[float] = None,
        original_exception: Optional[Exception] = None
    ):
        details = {}
        if product_code:
            details['product_code'] = product_code
        if matching_method:
            details['matching_method'] = matching_method
        if confidence_score is not None:
            details['confidence_score'] = confidence_score
            
        super().__init__(
            message=message,
            stage="matching",
            details=details,
            original_exception=original_exception
        )


class ValidationError(PipelineError):
    """
    Exception raised during validation stage
    
    Common causes:
    - Invalid field values
    - Missing required data
    - Business rule violations
    - Model catalog fetch failures
    """
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        details = {}
        if field_name:
            details['field_name'] = field_name
        if field_value is not None:
            details['field_value'] = field_value
        if validation_rule:
            details['validation_rule'] = validation_rule
            
        super().__init__(
            message=message,
            stage="validation",
            details=details,
            original_exception=original_exception
        )


class GenerationError(PipelineError):
    """
    Exception raised during XML generation stage
    
    Common causes:
    - Template rendering failures
    - Invalid XML structure
    - Missing required XML fields
    - Field mapping errors
    """
    
    def __init__(
        self,
        message: str,
        template_name: Optional[str] = None,
        xml_field: Optional[str] = None,
        product_code: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        details = {}
        if template_name:
            details['template_name'] = template_name
        if xml_field:
            details['xml_field'] = xml_field
        if product_code:
            details['product_code'] = product_code
            
        super().__init__(
            message=message,
            stage="generation",
            details=details,
            original_exception=original_exception
        )


class UploadError(PipelineError):
    """
    Exception raised during upload stage
    
    Common causes:
    - FTP connection failures
    - Authentication errors
    - Network timeouts
    - File permission issues
    """
    
    def __init__(
        self,
        message: str,
        server_host: Optional[str] = None,
        upload_path: Optional[str] = None,
        file_size: Optional[int] = None,
        original_exception: Optional[Exception] = None
    ):
        details = {}
        if server_host:
            details['server_host'] = server_host
        if upload_path:
            details['upload_path'] = upload_path
        if file_size:
            details['file_size'] = file_size
            
        super().__init__(
            message=message,
            stage="upload",
            details=details,
            original_exception=original_exception
        )


class ConfigurationError(PipelineError):
    """
    Exception raised for configuration-related errors
    
    Common causes:
    - Missing environment variables
    - Invalid configuration values
    - Missing configuration files
    - API key issues
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        details = {}
        if config_key:
            details['config_key'] = config_key
        if config_file:
            details['config_file'] = config_file
            
        super().__init__(
            message=message,
            stage="configuration",
            details=details,
            original_exception=original_exception
        )


class DatabaseError(PipelineError):
    """
    Exception raised for database-related errors
    
    Common causes:
    - Connection failures
    - Query execution errors
    - Schema mismatches
    - Transaction failures
    """
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        table_name: Optional[str] = None,
        database_path: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        details = {}
        if query:
            details['query'] = query
        if table_name:
            details['table_name'] = table_name
        if database_path:
            details['database_path'] = database_path
            
        super().__init__(
            message=message,
            stage="database",
            details=details,
            original_exception=original_exception
        )