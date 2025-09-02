"""
Base Extractor Abstract Class
Defines the interface for all data extraction implementations
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

from ...core import ProductData, PipelineStats, PipelineStage, ExtractionError

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """
    Abstract base class for all data extraction implementations
    
    Provides common functionality and defines the interface that all
    extractors must implement for the pipeline architecture.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize extractor with configuration
        
        Args:
            config: Extractor-specific configuration dictionary
        """
        self.config = config or {}
        self.logger = logger
        self.stats = PipelineStats(stage=PipelineStage.EXTRACTION)
        
    @abstractmethod
    def extract(self, source: Path, **kwargs) -> List[ProductData]:
        """
        Extract product data from source file
        
        Args:
            source: Path to source file (PDF, Excel, etc.)
            **kwargs: Additional extraction parameters
            
        Returns:
            List of extracted ProductData objects
            
        Raises:
            ExtractionError: If extraction fails
        """
        pass
    
    @abstractmethod
    def supports_format(self, file_path: Path) -> bool:
        """
        Check if extractor supports the given file format
        
        Args:
            file_path: Path to file to check
            
        Returns:
            True if format is supported, False otherwise
        """
        pass
    
    def validate_source(self, source: Path) -> bool:
        """
        Validate that source file exists and is readable
        
        Args:
            source: Path to source file
            
        Returns:
            True if source is valid, False otherwise
        """
        try:
            if not source.exists():
                raise ExtractionError(
                    message=f"Source file does not exist: {source}",
                    file_path=str(source)
                )
            
            if not source.is_file():
                raise ExtractionError(
                    message=f"Source is not a file: {source}",
                    file_path=str(source)
                )
            
            if source.stat().st_size == 0:
                raise ExtractionError(
                    message=f"Source file is empty: {source}",
                    file_path=str(source)
                )
            
            return True
            
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(
                message=f"Failed to validate source file: {source}",
                file_path=str(source),
                original_exception=e
            )
    
    def pre_extraction_hook(self, source: Path, **kwargs) -> Dict[str, Any]:
        """
        Hook called before extraction starts
        
        Args:
            source: Source file path
            **kwargs: Additional parameters
            
        Returns:
            Metadata dictionary for extraction context
        """
        self.stats.start_time = datetime.now()
        self.logger.info(f"Starting extraction from {source}")
        
        return {
            'source_path': str(source),
            'source_size': source.stat().st_size,
            'extraction_method': self.__class__.__name__,
            'start_time': self.stats.start_time.isoformat()
        }
    
    def post_extraction_hook(self, products: List[ProductData], metadata: Dict[str, Any]) -> None:
        """
        Hook called after extraction completes
        
        Args:
            products: Extracted product data
            metadata: Extraction metadata from pre_extraction_hook
        """
        self.stats.end_time = datetime.now()
        self.stats.total_processed = len(products)
        self.stats.successful = len([p for p in products if p.model_code])
        self.stats.failed = self.stats.total_processed - self.stats.successful
        
        if self.stats.start_time:
            processing_time = (self.stats.end_time - self.stats.start_time).total_seconds()
            self.stats.processing_time = processing_time
        
        self.logger.info(
            f"Extraction completed: {self.stats.successful}/{self.stats.total_processed} successful "
            f"({self.stats.success_rate:.1f}%) in {self.stats.processing_time:.2f}s"
        )
    
    def extract_with_hooks(self, source: Path, **kwargs) -> List[ProductData]:
        """
        Extract data with pre/post processing hooks
        
        Args:
            source: Source file path
            **kwargs: Additional extraction parameters
            
        Returns:
            List of extracted ProductData objects
        """
        try:
            # Validate source
            self.validate_source(source)
            
            # Pre-extraction hook
            metadata = self.pre_extraction_hook(source, **kwargs)
            
            # Main extraction
            products = self.extract(source, **kwargs)
            
            # Add extraction metadata to products
            for product in products:
                product.extraction_metadata.update(metadata)
            
            # Post-extraction hook
            self.post_extraction_hook(products, metadata)
            
            return products
            
        except Exception as e:
            self.stats.end_time = datetime.now()
            self.stats.failed = 1
            
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(
                message=f"Extraction failed for {source}",
                file_path=str(source),
                extraction_method=self.__class__.__name__,
                original_exception=e
            )
    
    def get_stats(self) -> PipelineStats:
        """Get extraction statistics"""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset extraction statistics"""
        self.stats = PipelineStats(stage=PipelineStage.EXTRACTION)