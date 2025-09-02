"""
Base Validator Abstract Class
Defines the interface for all validation implementations
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ...core import ProductData, CatalogData, ValidationResult, PipelineStats, PipelineStage, ValidationError

logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """
    Abstract base class for all validation implementations
    
    Provides common functionality and defines the interface that all
    validators must implement for data quality and business rule validation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize validator with configuration
        
        Args:
            config: Validator-specific configuration dictionary
        """
        self.config = config or {}
        self.logger = logger
        self.stats = PipelineStats(stage=PipelineStage.VALIDATION)
        self.validation_rules: Dict[str, Any] = {}
        
    @abstractmethod
    def validate_product(self, product: ProductData, catalog_data: Optional[CatalogData] = None) -> ValidationResult:
        """
        Validate a single product against business rules
        
        Args:
            product: Product data to validate
            catalog_data: Optional catalog data for reference validation
            
        Returns:
            ValidationResult with success status and detailed feedback
            
        Raises:
            ValidationError: If validation process fails
        """
        pass
    
    @abstractmethod
    def load_validation_rules(self) -> None:
        """
        Load validation rules from configuration or data sources
        
        Raises:
            ValidationError: If rules cannot be loaded
        """
        pass
    
    def validate_products(self, products: List[ProductData], catalog_data: Optional[List[CatalogData]] = None) -> List[ValidationResult]:
        """
        Validate multiple products
        
        Args:
            products: List of products to validate
            catalog_data: Optional catalog data for reference validation
            
        Returns:
            List of ValidationResult objects
        """
        try:
            self.stats.start_time = datetime.now()
            validation_results = []
            
            # Create catalog lookup if provided
            catalog_lookup = {}
            if catalog_data:
                for catalog_entry in catalog_data:
                    catalog_lookup[catalog_entry.model_family] = catalog_entry
            
            for product in products:
                try:
                    # Find matching catalog data if available
                    product_catalog = None
                    if catalog_lookup and product.malli:
                        for model_family, catalog_entry in catalog_lookup.items():
                            if catalog_entry.matches_product(product):
                                product_catalog = catalog_entry
                                break
                    
                    result = self.validate_product(product, product_catalog)
                    validation_results.append(result)
                    
                    if result.success:
                        self.stats.successful += 1
                    else:
                        self.stats.failed += 1
                        
                except Exception as e:
                    self.stats.failed += 1
                    self.logger.warning(f"Failed to validate product {product.model_code}: {e}")
                    
                    # Create failed validation result
                    failed_result = ValidationResult(
                        success=False,
                        errors=[f"Validation failed: {str(e)}"],
                        confidence=0.0
                    )
                    validation_results.append(failed_result)
            
            self.stats.end_time = datetime.now()
            self.stats.total_processed = len(products)
            
            if self.stats.start_time:
                self.stats.processing_time = (self.stats.end_time - self.stats.start_time).total_seconds()
            
            self.logger.info(
                f"Validation completed: {self.stats.successful}/{self.stats.total_processed} successful "
                f"({self.stats.success_rate:.1f}%) in {self.stats.processing_time:.2f}s"
            )
            
            return validation_results
            
        except Exception as e:
            raise ValidationError(
                message=f"Batch validation failed",
                validation_rule=self.__class__.__name__,
                original_exception=e
            )
    
    def validate_required_fields(self, product: ProductData) -> ValidationResult:
        """
        Validate that required fields are present and valid
        
        Args:
            product: Product to validate
            
        Returns:
            ValidationResult for required fields check
        """
        result = ValidationResult(success=True)
        
        # Check model_code
        if not product.model_code or len(product.model_code) != 4:
            result.add_error("model_code must be exactly 4 characters")
        
        # Check brand
        if not product.brand or product.brand.strip() == "":
            result.add_error("brand cannot be empty")
        
        # Check year
        if not product.year or product.year < 2015 or product.year > 2030:
            result.add_error(f"year must be between 2015-2030, got: {product.year}")
        
        # Check price if present
        if product.price is not None:
            if product.price <= 0:
                result.add_error("price must be greater than 0")
            elif product.price > 10000000:  # 10M threshold
                result.add_error(f"price seems unrealistic: {product.price}")
        
        return result
    
    def validate_business_rules(self, product: ProductData) -> ValidationResult:
        """
        Validate business-specific rules (can be overridden by subclasses)
        
        Args:
            product: Product to validate
            
        Returns:
            ValidationResult for business rules check
        """
        result = ValidationResult(success=True)
        
        # Example business rules that can be overridden
        if product.brand and product.brand.upper() not in ['LYNX', 'SKI-DOO', 'BRP']:
            result.warnings.append(f"Unknown brand: {product.brand}")
        
        if product.malli and len(product.malli) < 2:
            result.warnings.append(f"Model name seems too short: {product.malli}")
        
        return result
    
    def validate_data_consistency(self, product: ProductData, catalog_data: Optional[CatalogData] = None) -> ValidationResult:
        """
        Validate data consistency between fields and against catalog
        
        Args:
            product: Product to validate
            catalog_data: Optional catalog reference data
            
        Returns:
            ValidationResult for consistency check
        """
        result = ValidationResult(success=True)
        
        # Check consistency between fields
        if product.brand and product.malli:
            if product.brand.upper() == 'LYNX' and 'ski-doo' in product.malli.lower():
                result.add_error("Brand/model mismatch: LYNX brand with SKI-DOO model")
            elif product.brand.upper() == 'SKI-DOO' and 'lynx' in product.malli.lower():
                result.add_error("Brand/model mismatch: SKI-DOO brand with LYNX model")
        
        # Validate against catalog if available
        if catalog_data:
            if product.moottori:
                available_engines = catalog_data.available_engines
                if available_engines and product.moottori not in available_engines:
                    result.warnings.append(f"Engine '{product.moottori}' not found in catalog")
        
        return result
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Generate summary statistics for validation results
        
        Args:
            results: List of validation results
            
        Returns:
            Summary statistics dictionary
        """
        if not results:
            return {}
        
        total = len(results)
        successful = sum(1 for r in results if r.success)
        with_warnings = sum(1 for r in results if r.warnings)
        with_errors = sum(1 for r in results if r.errors)
        avg_confidence = sum(r.confidence for r in results) / total
        
        return {
            'total_validated': total,
            'successful': successful,
            'success_rate': (successful / total) * 100,
            'with_warnings': with_warnings,
            'with_errors': with_errors,
            'average_confidence': avg_confidence,
            'common_errors': self._get_common_issues([e for r in results for e in r.errors]),
            'common_warnings': self._get_common_issues([w for r in results for w in r.warnings])
        }
    
    def _get_common_issues(self, issues: List[str], top_n: int = 5) -> List[Dict[str, Any]]:
        """Get most common issues from validation results"""
        if not issues:
            return []
        
        issue_counts = {}
        for issue in issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'issue': issue, 'count': count}
            for issue, count in sorted_issues[:top_n]
        ]
    
    def get_stats(self) -> PipelineStats:
        """Get validation statistics"""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset validation statistics"""
        self.stats = PipelineStats(stage=PipelineStage.VALIDATION)