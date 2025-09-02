"""
Base Generator Abstract Class
Defines the interface for all XML generation implementations
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

from ...core import ProductData, CatalogData, AvitoXMLData, ValidationResult, PipelineStats, PipelineStage, GenerationError

logger = logging.getLogger(__name__)


class BaseGenerator(ABC):
    """
    Abstract base class for all XML generation implementations
    
    Provides common functionality and defines the interface that all
    generators must implement for marketplace XML generation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize generator with configuration
        
        Args:
            config: Generator-specific configuration dictionary
        """
        self.config = config or {}
        self.logger = logger
        self.stats = PipelineStats(stage=PipelineStage.GENERATION)
        self.templates: Dict[str, str] = {}
        
    @abstractmethod
    def generate_xml_data(self, product: ProductData, catalog_data: Optional[CatalogData] = None) -> AvitoXMLData:
        """
        Generate XML data structure for a single product
        
        Args:
            product: Product data to convert
            catalog_data: Optional catalog data for enrichment
            
        Returns:
            AvitoXMLData object ready for XML serialization
            
        Raises:
            GenerationError: If XML data generation fails
        """
        pass
    
    @abstractmethod
    def render_xml(self, xml_data: AvitoXMLData) -> str:
        """
        Render XML data to XML string
        
        Args:
            xml_data: AvitoXMLData object to render
            
        Returns:
            XML string representation
            
        Raises:
            GenerationError: If XML rendering fails
        """
        pass
    
    @abstractmethod
    def load_templates(self) -> None:
        """
        Load XML templates from configuration or files
        
        Raises:
            GenerationError: If templates cannot be loaded
        """
        pass
    
    def generate_xml_for_products(self, products: List[ProductData], catalog_data: Optional[List[CatalogData]] = None) -> List[str]:
        """
        Generate XML strings for multiple products
        
        Args:
            products: List of products to generate XML for
            catalog_data: Optional catalog data for enrichment
            
        Returns:
            List of XML strings
        """
        try:
            self.stats.start_time = datetime.now()
            xml_strings = []
            
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
                    
                    # Generate XML data structure
                    xml_data = self.generate_xml_data(product, product_catalog)
                    
                    # Validate XML data
                    validation_result = xml_data.validate_required_fields()
                    if not validation_result.success:
                        self.logger.warning(f"XML validation failed for {product.model_code}: {validation_result.errors}")
                        self.stats.failed += 1
                        continue
                    
                    # Render to XML string
                    xml_string = self.render_xml(xml_data)
                    xml_strings.append(xml_string)
                    
                    self.stats.successful += 1
                    
                except Exception as e:
                    self.stats.failed += 1
                    self.logger.warning(f"Failed to generate XML for product {product.model_code}: {e}")
            
            self.stats.end_time = datetime.now()
            self.stats.total_processed = len(products)
            
            if self.stats.start_time:
                self.stats.processing_time = (self.stats.end_time - self.stats.start_time).total_seconds()
            
            self.logger.info(
                f"XML generation completed: {self.stats.successful}/{self.stats.total_processed} successful "
                f"({self.stats.success_rate:.1f}%) in {self.stats.processing_time:.2f}s"
            )
            
            return xml_strings
            
        except Exception as e:
            raise GenerationError(
                message=f"Batch XML generation failed",
                template_name=self.__class__.__name__,
                original_exception=e
            )
    
    def save_xml_file(self, xml_strings: List[str], output_path: Path) -> bool:
        """
        Save generated XML strings to file
        
        Args:
            xml_strings: List of XML strings to save
            output_path: Path to output XML file
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Combine XML strings into single file
            xml_content = self._combine_xml_strings(xml_strings)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            self.logger.info(f"Saved {len(xml_strings)} XML entries to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save XML file: {e}")
            raise GenerationError(
                message=f"Failed to save XML file: {output_path}",
                template_name=self.__class__.__name__,
                original_exception=e
            )
    
    def _combine_xml_strings(self, xml_strings: List[str]) -> str:
        """
        Combine individual XML entries into a complete XML document
        
        Args:
            xml_strings: List of individual XML entries
            
        Returns:
            Complete XML document string
        """
        if not xml_strings:
            return '<?xml version="1.0" encoding="UTF-8"?>\n<items>\n</items>'
        
        # XML header and root element
        xml_content = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_content.append('<items>')
        
        # Add each XML entry
        for xml_string in xml_strings:
            # Remove XML declaration if present in individual entries
            if xml_string.startswith('<?xml'):
                xml_string = '\n'.join(xml_string.split('\n')[1:])
            
            xml_content.append(xml_string)
        
        xml_content.append('</items>')
        
        return '\n'.join(xml_content)
    
    def validate_xml_syntax(self, xml_string: str) -> ValidationResult:
        """
        Validate XML syntax and structure
        
        Args:
            xml_string: XML string to validate
            
        Returns:
            ValidationResult for XML validation
        """
        result = ValidationResult(success=True)
        
        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(xml_string)
            
        except ET.ParseError as e:
            result.add_error(f"XML syntax error: {e}")
        except Exception as e:
            result.add_error(f"XML validation error: {e}")
        
        return result
    
    def format_price(self, price: Optional[float], currency: str = 'EUR') -> Optional[int]:
        """
        Format price for marketplace requirements
        
        Args:
            price: Price value to format
            currency: Currency code
            
        Returns:
            Formatted price as integer or None
        """
        if not price or price <= 0:
            return None
        
        # Convert to rubles if needed (rough conversion for example)
        if currency == 'EUR':
            # Convert EUR to RUB (approximate rate)
            price_rub = price * 100  # Simplified conversion
        else:
            price_rub = price
        
        return int(round(price_rub))
    
    def generate_product_title(self, product: ProductData) -> str:
        """
        Generate product title for marketplace listing
        
        Args:
            product: Product data
            
        Returns:
            Formatted product title
        """
        title_parts = []
        
        if product.brand:
            title_parts.append(product.brand)
        
        if product.malli:
            title_parts.append(product.malli)
        
        if product.year:
            title_parts.append(str(product.year))
        
        if product.paketti:
            title_parts.append(product.paketti)
        
        return ' '.join(title_parts) if title_parts else f"Product {product.model_code}"
    
    def generate_product_description(self, product: ProductData, catalog_data: Optional[CatalogData] = None) -> str:
        """
        Generate detailed product description
        
        Args:
            product: Product data
            catalog_data: Optional catalog data for enrichment
            
        Returns:
            Formatted product description
        """
        description_parts = []
        
        # Basic product info
        description_parts.append(f"Model Code: {product.model_code}")
        
        if product.moottori:
            description_parts.append(f"Engine: {product.moottori}")
        
        if product.telamatto:
            description_parts.append(f"Track: {product.telamatto}")
        
        if product.kaynnistin:
            description_parts.append(f"Starter: {product.kaynnistin}")
        
        if product.mittaristo:
            description_parts.append(f"Gauge: {product.mittaristo}")
        
        if product.vari:
            description_parts.append(f"Color: {product.vari}")
        
        # Add catalog features if available
        if catalog_data and catalog_data.features:
            description_parts.append("\nFeatures:")
            for feature in catalog_data.features[:5]:  # Limit to 5 features
                description_parts.append(f"• {feature}")
        
        return '\n'.join(description_parts)
    
    def get_stats(self) -> PipelineStats:
        """Get generation statistics"""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset generation statistics"""
        self.stats = PipelineStats(stage=PipelineStage.GENERATION)