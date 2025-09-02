import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import uuid4

from ...models.domain import PriceEntry, BaseModel


logger = logging.getLogger(__name__)


@dataclass
class PDFQuality:
    """PDF quality analysis results"""
    is_digital: bool = True
    is_scanned: bool = False
    has_clear_tables: bool = False
    has_complex_tables: bool = False
    has_images: bool = False
    text_quality_score: float = 0.0
    table_count: int = 0
    
    @property
    def extraction_difficulty(self) -> str:
        """Categorize extraction difficulty"""
        if self.is_scanned or self.text_quality_score < 0.3:
            return "hard"
        elif self.has_complex_tables or self.text_quality_score < 0.7:
            return "medium"
        else:
            return "easy"


@dataclass
class ParseResult:
    """Result from PDF parsing operation"""
    entries: List[Dict[str, Any]]
    confidence: Decimal
    method_used: str
    processing_time_ms: int
    errors: List[str]
    metadata: Dict[str, Any]
    
    @property
    def success(self) -> bool:
        return len(self.entries) > 0 and self.confidence >= Decimal("0.5")


@dataclass 
class CatalogSection:
    """Represents a section of a catalog PDF"""
    pdf_path: Path
    page_num: int
    section_type: str  # 'model_overview', 'specifications_table', 'features_list'
    title_bbox: tuple = None
    content_bbox: tuple = None
    features_bbox: tuple = None
    has_clear_structure: bool = True
    has_product_images: bool = False
    confidence: float = 1.0


class BaseParser(ABC):
    """Base class for all PDF parsers"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def can_parse(self, pdf_path: Path, quality: PDFQuality) -> bool:
        """Check if this parser can handle the given PDF"""
        pass
    
    @abstractmethod 
    async def parse_price_list(self, pdf_path: Path, market: str, brand: str, year: int) -> ParseResult:
        """Parse price list from PDF"""
        pass
    
    @abstractmethod
    async def parse_catalog(self, pdf_path: Path, brand: str, year: int) -> ParseResult:
        """Parse catalog from PDF"""
        pass
    
    def _is_valid_model_code(self, model_code: str) -> bool:
        """Validate model code format"""
        if not model_code or not isinstance(model_code, str):
            return False
        
        # Remove whitespace and check format
        code = model_code.strip()
        
        # Must be 2-8 alphanumeric characters
        import re
        return bool(re.match(r'^[A-Z0-9]{2,8}$', code))
    
    def _parse_price(self, price_str: str) -> Optional[Decimal]:
        """Parse price string to Decimal"""
        if not price_str:
            return None
            
        try:
            import re
            # Remove currency symbols and spaces
            clean_price = re.sub(r'[€$£¥\s]', '', price_str)
            # Replace comma with dot for decimal
            clean_price = clean_price.replace(',', '.')
            # Remove any remaining non-numeric characters except dots
            clean_price = re.sub(r'[^\d.]', '', clean_price)
            
            if not clean_price:
                return None
            
            return Decimal(clean_price)
            
        except Exception as e:
            self.logger.warning(f"Could not parse price '{price_str}': {e}")
            return None
    
    def _get_market_table_settings(self, market: str) -> Dict[str, Any]:
        """Get market-specific table detection settings"""
        settings = {
            'FI': {  # Finnish market
                'table_areas': ['0,0,1,1'],  # Full page
                'columns': ['0,0.15,0.25,0.35,0.45,0.55,0.65,0.75,0.85,1'],
                'edge_tol': 500,
                'row_tol': 10
            },
            'SE': {  # Swedish market
                'table_areas': ['0,0,1,1'],
                'columns': ['0,0.12,0.24,0.36,0.48,0.6,0.72,0.84,1'],
                'edge_tol': 300,
                'row_tol': 15
            },
            'NO': {  # Norwegian market  
                'table_areas': ['0,0,1,1'],
                'columns': ['0,0.1,0.2,0.35,0.5,0.65,0.8,1'],
                'edge_tol': 400,
                'row_tol': 12
            }
        }
        
        return settings.get(market, settings['FI'])
    
    def _get_column_mapping(self, market: str) -> Dict[str, str]:
        """Get market-specific column mapping"""
        mappings = {
            'FI': {  # Finnish headers
                'model_code': 'mallikoodi',
                'malli': 'malli',  
                'paketti': 'paketti',
                'moottori': 'moottori',
                'telamatto': 'telamatto',
                'kaynnistin': 'käynnistin',
                'mittaristo': 'mittaristo',
                'kevatoptiot': 'kevätoptiot',
                'vari': 'väri',
                'price': 'hinta'
            },
            'SE': {  # Swedish headers
                'model_code': 'modellkod',
                'malli': 'modell',
                'paketti': 'paket',
                'moottori': 'motor', 
                'telamatto': 'band',
                'kaynnistin': 'startare',
                'mittaristo': 'instrument',
                'kevatoptiot': 'våralternativ',
                'vari': 'färg',
                'price': 'pris'
            },
            'NO': {  # Norwegian headers
                'model_code': 'modellkode',
                'malli': 'modell',
                'paketti': 'pakke',
                'moottori': 'motor',
                'telamatto': 'belter',
                'kaynnistin': 'starter', 
                'mittaristo': 'instrumenter',
                'kevatoptiot': 'våralternativer',
                'vari': 'farge',
                'price': 'pris'
            }
        }
        
        return mappings.get(market, mappings['FI'])
    
    def _detect_headers(self, data_frame, market: str) -> List[str]:
        """Intelligently detect headers in table data"""
        if data_frame is None or data_frame.empty:
            return []
        
        # Try first few rows as potential headers
        for row_idx in range(min(3, len(data_frame))):
            row = data_frame.iloc[row_idx]
            
            # Check if this row contains header-like text
            header_score = 0
            for cell in row:
                if cell and isinstance(cell, str):
                    cell_lower = cell.lower().strip()
                    
                    # Check for common header keywords
                    header_keywords = [
                        'model', 'malli', 'code', 'koodi', 'price', 'hinta', 'pris',
                        'engine', 'moottori', 'motor', 'track', 'telamatto', 'band'
                    ]
                    
                    if any(keyword in cell_lower for keyword in header_keywords):
                        header_score += 1
            
            # If we found enough header keywords, use this row
            if header_score >= 3:
                return [str(cell).strip() if cell else "" for cell in row]
        
        # Fallback to first row
        return [str(cell).strip() if cell else "" for cell in data_frame.iloc[0]]
    
    def _calculate_confidence(self, entries: List[Dict[str, Any]]) -> Decimal:
        """Calculate confidence score based on extraction quality"""
        if not entries:
            return Decimal("0.0")
        
        total_score = 0
        max_score = len(entries) * 100  # 100 points per entry
        
        for entry in entries:
            entry_score = 0
            
            # Required fields (40 points each)
            if entry.get('model_code'):
                entry_score += 40
            if entry.get('price'):
                entry_score += 40
            
            # Optional fields (4 points each)  
            optional_fields = ['malli', 'moottori', 'telamatto', 'vari', 'paketti']
            for field in optional_fields:
                if entry.get(field):
                    entry_score += 4
            
            total_score += entry_score
        
        confidence = total_score / max_score if max_score > 0 else 0
        return Decimal(str(min(1.0, confidence)))
    
    def _build_price_entry_dict(self, data: Dict[str, Any], brand: str, market: str, year: int, price_list_id) -> Dict[str, Any]:
        """Build standardized price entry dictionary"""
        
        # Generate catalog lookup key
        paketti_part = data.get('paketti', '') or ''
        malli = data.get('malli', '')
        model_part = f"{malli}_{paketti_part}".replace(' ', '_')
        catalog_lookup_key = f"{brand}_{model_part}_{year}"
        
        return {
            'id': uuid4(),
            'price_list_id': price_list_id,
            'model_code': data.get('model_code', ''),
            'malli': data.get('malli'),
            'paketti': data.get('paketti'),
            'moottori': data.get('moottori'),
            'telamatto': data.get('telamatto'),
            'kaynnistin': data.get('kaynnistin'),
            'mittaristo': data.get('mittaristo'),
            'kevatoptiot': data.get('kevatoptiot'),
            'vari': data.get('vari'),
            'price': data.get('price'),
            'currency': data.get('currency', 'EUR'),
            'market': market,
            'brand': brand,
            'model_year': year,
            'catalog_lookup_key': catalog_lookup_key
        }