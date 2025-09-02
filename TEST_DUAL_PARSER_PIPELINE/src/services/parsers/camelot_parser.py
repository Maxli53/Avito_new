import asyncio
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

from .base_parser import BaseParser, ParseResult, PDFQuality


class CamelotParser(BaseParser):
    """Camelot parser - excellent for complex table structures"""
    
    async def can_parse(self, pdf_path: Path, quality: PDFQuality) -> bool:
        """Check if Camelot can handle this PDF effectively"""
        # Best for complex tables, even in scanned documents
        return (quality.has_complex_tables or 
                (quality.table_count > 2 and quality.text_quality_score > 0.5))
    
    async def parse_price_list(self, pdf_path: Path, market: str, brand: str, year: int) -> ParseResult:
        """Parse price list using Camelot table extraction"""
        start_time = datetime.now()
        entries = []
        errors = []
        
        try:
            import camelot
            
            # Market-specific table detection settings
            table_settings = self._get_market_table_settings(market)
            
            # Try lattice method first (for tables with clear borders)
            tables = camelot.read_pdf(
                str(pdf_path),
                pages='all',
                flavor='lattice',  # For bordered tables
                line_scale=40,     # Line detection sensitivity
                split_text=True,
                strip_text='\n',
                **table_settings
            )
            
            # If lattice fails, try stream method
            if len(tables) == 0 or all(table.df.empty for table in tables):
                self.logger.info("Lattice method found no tables, trying stream method")
                tables = camelot.read_pdf(
                    str(pdf_path),
                    pages='all',
                    flavor='stream',  # For tables without clear borders
                    edge_tol=500,
                    row_tol=10,
                    column_tol=0,
                )
            
            # Process each table
            for table_idx, table in enumerate(tables):
                try:
                    if table.df.empty:
                        continue
                    
                    # Get table accuracy score
                    accuracy = getattr(table, 'accuracy', 0)
                    self.logger.info(f"Table {table_idx} accuracy: {accuracy:.2f}")
                    
                    # Skip low-quality tables
                    if accuracy < 60:
                        self.logger.warning(f"Skipping low-accuracy table {table_idx} (accuracy: {accuracy:.2f})")
                        continue
                    
                    # Process the table
                    table_entries = await self._process_camelot_table(
                        table.df, market, brand, year, table_idx
                    )
                    entries.extend(table_entries)
                    
                except Exception as e:
                    error_msg = f"Failed to process Camelot table {table_idx}: {e}"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            confidence = self._calculate_confidence(entries)
            
            return ParseResult(
                entries=entries,
                confidence=confidence,
                method_used="camelot_table_extraction",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={
                    'tables_found': len(tables),
                    'total_entries': len(entries),
                    'avg_table_accuracy': sum(getattr(t, 'accuracy', 0) for t in tables) / len(tables) if tables else 0
                }
            )
            
        except ImportError:
            error_msg = "Camelot not installed. Install with: pip install camelot-py[cv]"
            errors.append(error_msg)
            self.logger.error(error_msg)
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="camelot_not_available",
                processing_time_ms=0,
                errors=errors,
                metadata={}
            )
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"Camelot parsing failed: {e}"
            errors.append(error_msg)
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="camelot_failed",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={}
            )
    
    async def parse_catalog(self, pdf_path: Path, brand: str, year: int) -> ParseResult:
        """Parse catalog using Camelot (limited implementation)"""
        # Camelot is primarily for tabular data, less suitable for complex catalog layouts
        # This is a basic implementation for catalog tables
        
        start_time = datetime.now()
        base_models = []
        errors = []
        
        try:
            import camelot
            
            # Extract all tables
            tables = camelot.read_pdf(
                str(pdf_path),
                pages='all',
                flavor='lattice',
                line_scale=40
            )
            
            # Process specification tables
            for table_idx, table in enumerate(tables):
                try:
                    if table.df.empty:
                        continue
                    
                    # Look for model specification tables
                    model_data = await self._extract_model_from_table(
                        table.df, brand, year, table_idx
                    )
                    
                    if model_data:
                        base_models.append(model_data)
                    
                except Exception as e:
                    error_msg = f"Failed to process catalog table {table_idx}: {e}"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            confidence = self._calculate_catalog_confidence(base_models)
            
            return ParseResult(
                entries=base_models,
                confidence=confidence,
                method_used="camelot_catalog_extraction",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={
                    'tables_processed': len(tables),
                    'models_extracted': len(base_models)
                }
            )
            
        except ImportError:
            error_msg = "Camelot not installed. Install with: pip install camelot-py[cv]"
            errors.append(error_msg)
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="camelot_not_available",
                processing_time_ms=0,
                errors=errors,
                metadata={}
            )
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"Camelot catalog parsing failed: {e}"
            errors.append(error_msg)
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="camelot_catalog_failed",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={}
            )
    
    async def _process_camelot_table(
        self, 
        df: pd.DataFrame, 
        market: str, 
        brand: str, 
        year: int, 
        table_idx: int
    ) -> List[Dict[str, Any]]:
        """Process a Camelot-extracted table into price entries"""
        entries = []
        
        if df.empty:
            return entries
        
        try:
            # Intelligent header detection
            headers = self._detect_headers(df, market)
            
            # Create column mapping
            column_map = self._get_column_mapping(market)
            field_mapping = {}
            
            for field, column_patterns in column_map.items():
                for i, header in enumerate(headers):
                    header_clean = header.lower().strip()
                    if any(pattern in header_clean for pattern in column_patterns):
                        field_mapping[field] = i
                        break
            
            # Check for required fields
            if 'model_code' not in field_mapping or 'price' not in field_mapping:
                self.logger.warning(f"Required fields not found in table {table_idx}")
                return entries
            
            # Process data rows (skip header row)
            for row_idx in range(1, len(df)):
                try:
                    row = df.iloc[row_idx]
                    
                    # Extract and validate model code
                    model_code = str(row.iloc[field_mapping['model_code']]).strip()
                    if not self._is_valid_model_code(model_code):
                        continue
                    
                    # Extract and validate price
                    price_str = str(row.iloc[field_mapping['price']]).strip()
                    price = self._parse_price(price_str)
                    if not price or price <= 0:
                        continue
                    
                    # Build entry data
                    entry_data = {
                        'model_code': model_code,
                        'price': price,
                        'currency': 'EUR'
                    }
                    
                    # Extract optional fields
                    optional_fields = ['malli', 'paketti', 'moottori', 'telamatto', 
                                     'kaynnistin', 'mittaristo', 'kevatoptiot', 'vari']
                    
                    for field in optional_fields:
                        if field in field_mapping:
                            value = str(row.iloc[field_mapping[field]]).strip()
                            entry_data[field] = value if value and value != 'nan' else None
                    
                    # Build complete entry
                    entry = self._build_price_entry_dict(entry_data, brand, market, year, None)
                    entries.append(entry)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process row {row_idx} in table {table_idx}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Failed to process Camelot table {table_idx}: {e}")
        
        return entries
    
    async def _extract_model_from_table(
        self, 
        df: pd.DataFrame, 
        brand: str, 
        year: int, 
        table_idx: int
    ) -> Dict[str, Any]:
        """Extract model information from a catalog table"""
        
        if df.empty or len(df) < 2:
            return None
        
        try:
            # Look for model name in first column or first row
            model_family = None
            
            # Check first row for model name
            first_row = df.iloc[0]
            for cell in first_row:
                cell_str = str(cell).strip()
                if len(cell_str) > 5 and any(keyword in cell_str.upper() for keyword in ['RE', 'RS', 'XT', 'SPORT']):
                    model_family = cell_str
                    break
            
            # Check first column for model name
            if not model_family:
                first_col = df.iloc[:, 0]
                for cell in first_col:
                    cell_str = str(cell).strip()
                    if len(cell_str) > 5 and any(keyword in cell_str.upper() for keyword in ['RE', 'RS', 'XT', 'SPORT']):
                        model_family = cell_str
                        break
            
            if not model_family:
                return None
            
            # Extract specifications from the table
            specifications = {}
            
            # Look for key-value pairs in the table
            for row_idx in range(len(df)):
                row = df.iloc[row_idx]
                
                if len(row) >= 2:
                    key = str(row.iloc[0]).strip().lower()
                    value = str(row.iloc[1]).strip()
                    
                    if key and value and value != 'nan':
                        # Map to specification categories
                        if any(keyword in key for keyword in ['engine', 'motor']):
                            if 'engine_options' not in specifications:
                                specifications['engine_options'] = {}
                            specifications['engine_options'][key] = value
                        
                        elif any(keyword in key for keyword in ['track', 'belt']):
                            if 'track_options' not in specifications:
                                specifications['track_options'] = {}
                            specifications['track_options'][key] = value
                        
                        elif any(keyword in key for keyword in ['dimension', 'size', 'length', 'width', 'height']):
                            if 'dimensions' not in specifications:
                                specifications['dimensions'] = {}
                            specifications['dimensions'][key] = value
                        
                        elif any(keyword in key for keyword in ['feature', 'equipment']):
                            if 'features' not in specifications:
                                specifications['features'] = []
                            if value not in specifications['features']:
                                specifications['features'].append(value)
            
            # Build base model dictionary
            from uuid import uuid4
            
            model_clean = model_family.replace(' ', '_')
            lookup_key = f"{brand}_{model_clean}_{year}"
            
            return {
                'id': uuid4(),
                'lookup_key': lookup_key,
                'brand': brand,
                'model_family': model_family,
                'model_year': year,
                'engine_options': specifications.get('engine_options', {}),
                'track_options': specifications.get('track_options', {}),
                'suspension_options': specifications.get('suspension_options', {}),
                'starter_options': specifications.get('starter_options', {}),
                'dimensions': specifications.get('dimensions', {}),
                'features': specifications.get('features', []),
                'full_specifications': specifications,
                'marketing_description': None,
                'source_pages': [table_idx],
                'extraction_confidence': Decimal("0.75"),
                'completeness_score': self._calculate_completeness_score(specifications)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract model from table {table_idx}: {e}")
            return None
    
    def _calculate_completeness_score(self, specifications: Dict[str, Any]) -> Decimal:
        """Calculate completeness score for specifications"""
        required_fields = ['engine_options', 'track_options', 'dimensions']
        optional_fields = ['features', 'suspension_options', 'starter_options']
        
        score = 0
        total_possible = len(required_fields) * 2 + len(optional_fields)
        
        for field in required_fields:
            if field in specifications and specifications[field]:
                score += 2
        
        for field in optional_fields:
            if field in specifications and specifications[field]:
                score += 1
        
        return Decimal(str(score / total_possible)) if total_possible > 0 else Decimal("0.0")
    
    def _calculate_catalog_confidence(self, base_models: List[Dict[str, Any]]) -> Decimal:
        """Calculate confidence score for catalog extraction"""
        if not base_models:
            return Decimal("0.0")
        
        total_score = 0
        max_score = len(base_models) * 100
        
        for model in base_models:
            model_score = 0
            
            # Required fields
            if model.get('model_family'):
                model_score += 40
            if model.get('lookup_key'):
                model_score += 20
            
            # Specifications quality  
            specs = model.get('full_specifications', {})
            if specs.get('engine_options'):
                model_score += 15
            if specs.get('track_options'):
                model_score += 15
            if specs.get('dimensions'):
                model_score += 10
            
            total_score += model_score
        
        confidence = total_score / max_score if max_score > 0 else 0
        return Decimal(str(min(1.0, confidence)))