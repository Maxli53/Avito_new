"""
Base Matcher Abstract Class
Defines the interface for all matching engine implementations
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ...core import ProductData, CatalogData, MatchResult, MatchType, PipelineStats, PipelineStage, MatchingError

logger = logging.getLogger(__name__)


class BaseMatcher(ABC):
    """
    Abstract base class for all matching engine implementations
    
    Provides common functionality and defines the interface that all
    matchers must implement for semantic and inheritance matching.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize matcher with configuration
        
        Args:
            config: Matcher-specific configuration dictionary
        """
        self.config = config or {}
        self.logger = logger
        self.stats = PipelineStats(stage=PipelineStage.MATCHING)
        self.catalog_data: List[CatalogData] = []
        
    @abstractmethod
    def match_product(self, product: ProductData, catalog_entries: List[CatalogData]) -> MatchResult:
        """
        Match a single product against catalog entries
        
        Args:
            product: Product data to match
            catalog_entries: Available catalog entries for matching
            
        Returns:
            MatchResult with best match and confidence score
            
        Raises:
            MatchingError: If matching process fails
        """
        pass
    
    @abstractmethod
    def get_match_type(self) -> MatchType:
        """
        Get the type of matching this matcher performs
        
        Returns:
            MatchType enum value
        """
        pass
    
    def load_catalog_data(self, catalog_entries: List[CatalogData]) -> None:
        """
        Load catalog data for matching operations
        
        Args:
            catalog_entries: List of catalog entries to use for matching
        """
        self.catalog_data = catalog_entries
        self.logger.info(f"Loaded {len(catalog_entries)} catalog entries for matching")
    
    def match_products(self, products: List[ProductData]) -> List[MatchResult]:
        """
        Match multiple products against loaded catalog data
        
        Args:
            products: List of products to match
            
        Returns:
            List of MatchResult objects
        """
        if not self.catalog_data:
            raise MatchingError(
                message="No catalog data loaded for matching",
                matching_method=self.__class__.__name__
            )
        
        try:
            self.stats.start_time = datetime.now()
            match_results = []
            
            for product in products:
                try:
                    start_time = datetime.now()
                    result = self.match_product(product, self.catalog_data)
                    end_time = datetime.now()
                    
                    result.processing_time = (end_time - start_time).total_seconds()
                    match_results.append(result)
                    
                    if result.matched:
                        self.stats.successful += 1
                    else:
                        self.stats.failed += 1
                        
                except Exception as e:
                    self.stats.failed += 1
                    self.logger.warning(f"Failed to match product {product.model_code}: {e}")
                    
                    # Create failed match result
                    failed_result = MatchResult(
                        product_data=product,
                        catalog_data=None,
                        match_type=self.get_match_type(),
                        confidence_score=0.0,
                        matched=False,
                        match_details={'error': str(e)},
                        processing_time=0.0
                    )
                    match_results.append(failed_result)
            
            self.stats.end_time = datetime.now()
            self.stats.total_processed = len(products)
            
            if self.stats.start_time:
                self.stats.processing_time = (self.stats.end_time - self.stats.start_time).total_seconds()
            
            self.logger.info(
                f"Matching completed: {self.stats.successful}/{self.stats.total_processed} successful "
                f"({self.stats.success_rate:.1f}%) in {self.stats.processing_time:.2f}s"
            )
            
            return match_results
            
        except Exception as e:
            raise MatchingError(
                message=f"Batch matching failed",
                matching_method=self.__class__.__name__,
                original_exception=e
            )
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate basic string similarity (can be overridden by subclasses)
        
        Args:
            text1: First text to compare
            text2: Second text to compare
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        # Simple character-based similarity
        text1_norm = text1.lower().strip()
        text2_norm = text2.lower().strip()
        
        if text1_norm == text2_norm:
            return 1.0
        
        # Calculate overlap
        set1 = set(text1_norm.split())
        set2 = set(text2_norm.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def filter_catalog_by_brand(self, brand: str) -> List[CatalogData]:
        """
        Filter catalog entries by brand
        
        Args:
            brand: Brand name to filter by
            
        Returns:
            Filtered list of catalog entries
        """
        if not brand:
            return self.catalog_data
        
        brand_norm = brand.upper().strip()
        return [
            entry for entry in self.catalog_data 
            if brand_norm in entry.extraction_metadata.get('brand', '').upper()
        ]
    
    def get_stats(self) -> PipelineStats:
        """Get matching statistics"""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset matching statistics"""
        self.stats = PipelineStats(stage=PipelineStage.MATCHING)