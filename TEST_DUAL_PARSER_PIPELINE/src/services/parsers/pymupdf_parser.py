import asyncio
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any
import fitz

from .base_parser import BaseParser, ParseResult, PDFQuality, CatalogSection


class PyMuPDFParser(BaseParser):
    """Fast PyMuPDF parser - excellent for digital PDFs with embedded tables"""
    
    async def can_parse(self, pdf_path: Path, quality: PDFQuality) -> bool:
        """Check if PyMuPDF can handle this PDF effectively"""
        # Best for digital PDFs with clear tables
        return (quality.is_digital and 
                quality.has_clear_tables and 
                quality.text_quality_score > 0.7)
    
    async def parse_price_list(self, pdf_path: Path, market: str, brand: str, year: int) -> ParseResult:
        """Parse price list using PyMuPDF table detection"""
        start_time = datetime.now()
        entries = []
        errors = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Find tables on the page
                tables = page.find_tables()
                
                for table_idx, table in enumerate(tables):
                    try:
                        # Extract table data
                        table_data = table.extract()
                        
                        if not table_data or len(table_data) < 2:
                            continue
                        
                        # Process table
                        table_entries = await self._process_price_table(
                            table_data, market, brand, year, page_num, table_idx
                        )
                        entries.extend(table_entries)
                        
                    except Exception as e:
                        error_msg = f"Failed to process table {table_idx} on page {page_num + 1}: {e}"
                        errors.append(error_msg)
                        self.logger.warning(error_msg)
            
            doc.close()
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            confidence = self._calculate_confidence(entries)
            
            return ParseResult(
                entries=entries,
                confidence=confidence,
                method_used="pymupdf_table_detection",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={
                    'total_pages': len(doc) if doc else 0,
                    'tables_found': sum(len(doc[i].find_tables()) for i in range(len(doc))) if doc else 0
                }
            )
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            errors.append(f"PyMuPDF parsing failed: {e}")
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="pymupdf_failed",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={}
            )
    
    async def parse_catalog(self, pdf_path: Path, brand: str, year: int) -> ParseResult:
        """Parse catalog using PyMuPDF"""
        start_time = datetime.now()
        base_models = []
        errors = []
        
        try:
            doc = fitz.open(pdf_path)
            
            current_model = None
            current_specs = {}
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text content
                text = page.get_text()
                
                # Look for model family headers
                model_family = self._extract_model_family_from_text(text, brand)
                
                if model_family:
                    # Save previous model if we have one
                    if current_model and current_specs:
                        base_model_dict = self._build_base_model_dict(
                            current_model, current_specs, brand, year, [page_num-1]
                        )
                        base_models.append(base_model_dict)
                    
                    current_model = model_family
                    current_specs = {}
                
                # Extract specifications from tables
                tables = page.find_tables()
                for table in tables:
                    table_data = table.extract()
                    specs = self._extract_specifications_from_table(table_data)
                    current_specs.update(specs)
                
                # Extract specifications from text
                text_specs = self._extract_specifications_from_text(text)
                current_specs.update(text_specs)
            
            # Don't forget the last model
            if current_model and current_specs:
                base_model_dict = self._build_base_model_dict(
                    current_model, current_specs, brand, year, [len(doc)-1]
                )
                base_models.append(base_model_dict)
            
            doc.close()
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            confidence = self._calculate_catalog_confidence(base_models)
            
            return ParseResult(
                entries=base_models,
                confidence=confidence,
                method_used="pymupdf_catalog_extraction",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={
                    'total_pages': len(doc) if doc else 0,
                    'models_extracted': len(base_models)
                }
            )
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            errors.append(f"PyMuPDF catalog parsing failed: {e}")
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="pymupdf_catalog_failed",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={}
            )
    
    async def _process_price_table(
        self, 
        table_data: List[List[str]], 
        market: str, 
        brand: str, 
        year: int, 
        page_num: int, 
        table_idx: int
    ) -> List[Dict[str, Any]]:
        """Process a single price table"""
        entries = []
        
        if not table_data or len(table_data) < 2:
            return entries
        
        # Detect headers
        headers = self._detect_headers_from_table(table_data)
        
        # Create field mapping
        field_mapping = self._create_field_mapping_from_headers(headers, market)
        
        if not field_mapping.get('model_code') or not field_mapping.get('price'):
            self.logger.warning(
                f"Could not find required fields in table {table_idx} on page {page_num + 1}"
            )
            return entries
        
        # Process data rows
        data_start_row = 1  # Usually first row is headers
        
        for row_idx, row in enumerate(table_data[data_start_row:], data_start_row):
            try:
                if len(row) <= max(field_mapping.values()):
                    continue  # Skip incomplete rows
                
                # Extract model code and validate
                model_code = row[field_mapping['model_code']].strip() if 'model_code' in field_mapping else None
                
                if not self._is_valid_model_code(model_code):
                    continue
                
                # Extract price
                price_str = row[field_mapping['price']].strip() if 'price' in field_mapping else None
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
                        value = row[field_mapping[field]].strip()
                        entry_data[field] = value if value else None
                
                # Build complete entry dictionary
                entry = self._build_price_entry_dict(entry_data, brand, market, year, None)
                entries.append(entry)
                
            except Exception as e:
                self.logger.warning(f"Failed to process row {row_idx}: {e}")
                continue
        
        return entries
    
    def _detect_headers_from_table(self, table_data: List[List[str]]) -> List[str]:
        """Detect headers from table data"""
        if not table_data:
            return []
        
        # First row is most likely headers
        first_row = table_data[0]
        
        # Clean and normalize headers
        headers = []
        for cell in first_row:
            if cell:
                header = str(cell).strip().lower()
                # Remove common formatting artifacts
                header = header.replace('\n', ' ').replace('  ', ' ')
                headers.append(header)
            else:
                headers.append("")
        
        return headers
    
    def _create_field_mapping_from_headers(self, headers: List[str], market: str) -> Dict[str, int]:
        """Create field mapping from detected headers"""
        mapping = {}
        
        # Market-specific field patterns
        field_patterns = {
            'FI': {  # Finnish
                'model_code': ['model', 'code', 'mallikoodi', 'koodi'],
                'malli': ['malli', 'model', 'name'],
                'paketti': ['paketti', 'package', 'pak'],
                'moottori': ['moottori', 'engine', 'motor'],
                'telamatto': ['telamatto', 'track', 'tela'],
                'kaynnistin': ['käynnistin', 'starter', 'start'],
                'mittaristo': ['mittaristo', 'gauge', 'display', 'instruments'],
                'kevatoptiot': ['kevätoptiot', 'spring', 'options', 'optiot'],
                'vari': ['väri', 'color', 'colour'],
                'price': ['hinta', 'price', '€', 'eur', 'euro']
            },
            'SE': {  # Swedish
                'model_code': ['modell', 'kod', 'code'],
                'malli': ['modell', 'model', 'name'],
                'paketti': ['paket', 'package'],
                'moottori': ['motor', 'engine'],
                'telamatto': ['band', 'track'],
                'kaynnistin': ['startare', 'starter'],
                'mittaristo': ['instrument', 'display'],
                'kevatoptiot': ['våralternativ', 'options'],
                'vari': ['färg', 'color'],
                'price': ['pris', 'price', '€', 'eur', 'kr', 'sek']
            },
            'NO': {  # Norwegian
                'model_code': ['modell', 'kode', 'code'],
                'malli': ['modell', 'model', 'name'],
                'paketti': ['pakke', 'package'],
                'moottori': ['motor', 'engine'],
                'telamatto': ['belter', 'track'],
                'kaynnistin': ['starter'],
                'mittaristo': ['instrumenter', 'display'],
                'kevatoptiot': ['våralternativer', 'options'],
                'vari': ['farge', 'color'],
                'price': ['pris', 'price', '€', 'eur', 'kr', 'nok']
            }
        }
        
        patterns = field_patterns.get(market, field_patterns['FI'])
        
        for field, field_patterns in patterns.items():
            for i, header in enumerate(headers):
                if any(pattern in header for pattern in field_patterns):
                    mapping[field] = i
                    break
        
        return mapping
    
    def _extract_model_family_from_text(self, text: str, brand: str) -> str:
        """Extract model family name from page text"""
        import re
        
        # Common patterns for model family headers
        patterns = [
            rf'{brand}\s+([A-Z][a-zA-Z\s]+(?:RE|RS|XT|SWT|SPORT))',  # Brand + Model + Package
            r'^([A-Z][a-zA-Z\s]+(?:RE|RS|XT|SWT|SPORT))\s*$',  # Standalone model name
            r'(\w+\s+\w+)\s+SPECIFICATIONS',  # Model + SPECIFICATIONS
        ]
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 50:  # Skip very long lines
                continue
                
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    model_name = match.group(1).strip()
                    if len(model_name) > 2 and model_name.upper() not in ['THE', 'AND', 'FOR']:
                        return model_name
        
        return None
    
    def _extract_specifications_from_table(self, table_data: List[List[str]]) -> Dict[str, Any]:
        """Extract specifications from table data"""
        specs = {}
        
        if not table_data or len(table_data) < 2:
            return specs
        
        try:
            # Look for specification patterns in table
            for row in table_data:
                if len(row) < 2:
                    continue
                
                key = row[0].strip().lower() if row[0] else ""
                value = row[1].strip() if row[1] else ""
                
                if not key or not value:
                    continue
                
                # Map common specification fields
                if any(keyword in key for keyword in ['engine', 'motor', 'moottori']):
                    if 'engine_options' not in specs:
                        specs['engine_options'] = {}
                    self._parse_engine_specifications(value, specs['engine_options'])
                
                elif any(keyword in key for keyword in ['track', 'tela']):
                    if 'track_options' not in specs:
                        specs['track_options'] = {}
                    self._parse_track_specifications(value, specs['track_options'])
                
                elif any(keyword in key for keyword in ['dimension', 'size', 'koko']):
                    if 'dimensions' not in specs:
                        specs['dimensions'] = {}
                    specs['dimensions'][key] = value
                
                elif any(keyword in key for keyword in ['weight', 'paino']):
                    specs['weight'] = value
                
                elif any(keyword in key for keyword in ['feature', 'ominaisuus']):
                    if 'features' not in specs:
                        specs['features'] = []
                    if value not in specs['features']:
                        specs['features'].append(value)
        
        except Exception as e:
            self.logger.warning(f"Failed to extract specifications from table: {e}")
        
        return specs
    
    def _extract_specifications_from_text(self, text: str) -> Dict[str, Any]:
        """Extract specifications from free text"""
        specs = {}
        
        import re
        
        # Engine specifications
        engine_patterns = [
            r'Engine[:\s]*([^\.]+(?:E-TEC|ETEC|ACE|TBI)[^\.]*)',
            r'Motor[:\s]*([^\.]+(?:E-TEC|ETEC|ACE|TBI)[^\.]*)',
            r'([0-9]+R?\s*(?:E-TEC|ETEC|ACE|TBI)(?:\s*Turbo)?[^\.]*)'
        ]
        
        for pattern in engine_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if 'engine_options' not in specs:
                    specs['engine_options'] = {}
                engine_text = match.group(1).strip()
                self._parse_engine_specifications(engine_text, specs['engine_options'])
        
        # Track specifications
        track_patterns = [
            r'Track[:\s]*([0-9]+(?:in|"|\s*inch)[^\.]*)',
            r'([0-9]+(?:in|"|\s*inch)[^\.]+track[^\.]*)',
            r'([0-9]+(?:in|"|\s*inch)\s*x\s*[0-9]+(?:mm|cm)[^\.]*)'
        ]
        
        for pattern in track_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if 'track_options' not in specs:
                    specs['track_options'] = {}
                track_text = match.group(1).strip()
                self._parse_track_specifications(track_text, specs['track_options'])
        
        return specs
    
    def _parse_engine_specifications(self, engine_text: str, engine_options: Dict[str, Any]):
        """Parse engine specification text into structured data"""
        import re
        
        try:
            # Extract engine type and displacement
            engine_match = re.search(r'([0-9]+R?)\s*(E-TEC|ETEC|ACE|TBI)(\s*Turbo\s*R?)?', engine_text, re.IGNORECASE)
            if engine_match:
                displacement = engine_match.group(1)
                engine_type = engine_match.group(2).upper()
                turbo = engine_match.group(3) is not None
                
                engine_key = f"{displacement}_{engine_type}"
                if turbo:
                    engine_key += "_TURBO"
                
                engine_options[engine_key] = {
                    'displacement': displacement,
                    'type': engine_type,
                    'turbo': turbo,
                    'full_name': engine_text.strip()
                }
        except Exception as e:
            self.logger.warning(f"Failed to parse engine spec '{engine_text}': {e}")
    
    def _parse_track_specifications(self, track_text: str, track_options: Dict[str, Any]):
        """Parse track specification text into structured data"""
        import re
        
        try:
            # Extract track length
            track_match = re.search(r'([0-9]+)(?:in|"|\s*inch)', track_text, re.IGNORECASE)
            if track_match:
                track_length = track_match.group(1)
                
                # Extract additional track info
                width_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:mm|cm)', track_text)
                width = width_match.group(1) + "mm" if width_match else None
                
                track_options[f"{track_length}in"] = {
                    'length_inches': int(track_length),
                    'width': width,
                    'full_description': track_text.strip()
                }
        except Exception as e:
            self.logger.warning(f"Failed to parse track spec '{track_text}': {e}")
    
    def _build_base_model_dict(self, model_family: str, specifications: Dict[str, Any], brand: str, year: int, source_pages: List[int]) -> Dict[str, Any]:
        """Build base model dictionary"""
        from uuid import uuid4
        
        # Generate lookup key
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
            'source_pages': source_pages,
            'extraction_confidence': Decimal("0.85"),
            'completeness_score': self._calculate_completeness_score(specifications)
        }
    
    def _calculate_completeness_score(self, specifications: Dict[str, Any]) -> Decimal:
        """Calculate completeness score based on available specifications"""
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
        
        return Decimal(str(score / total_possible))
    
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
                model_score += 30
            if model.get('lookup_key'):
                model_score += 20
            
            # Specifications quality
            specs = model.get('full_specifications', {})
            if specs.get('engine_options'):
                model_score += 20
            if specs.get('track_options'):
                model_score += 15
            if specs.get('dimensions'):
                model_score += 10
            if specs.get('features'):
                model_score += 5
            
            total_score += model_score
        
        confidence = total_score / max_score if max_score > 0 else 0
        return Decimal(str(min(1.0, confidence)))