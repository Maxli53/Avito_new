import asyncio
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base_parser import BaseParser, ParseResult, PDFQuality


class PDFPlumberParser(BaseParser):
    """PDFPlumber parser - excellent for structured data extraction with precise positioning"""
    
    async def can_parse(self, pdf_path: Path, quality: PDFQuality) -> bool:
        """Check if PDFPlumber can handle this PDF effectively"""
        # Good for structured documents with consistent layouts
        return (quality.is_digital and 
                quality.text_quality_score > 0.6 and
                not quality.has_complex_tables)
    
    async def parse_price_list(self, pdf_path: Path, market: str, brand: str, year: int) -> ParseResult:
        """Parse price list using PDFPlumber structured extraction"""
        start_time = datetime.now()
        entries = []
        errors = []
        
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Try table extraction first
                        tables = page.extract_tables()
                        
                        if tables:
                            # Process tables
                            for table_idx, table in enumerate(tables):
                                table_entries = await self._process_pdfplumber_table(
                                    table, market, brand, year, page_num, table_idx
                                )
                                entries.extend(table_entries)
                        else:
                            # Fall back to text-based extraction
                            text_entries = await self._process_pdfplumber_text(
                                page, market, brand, year, page_num
                            )
                            entries.extend(text_entries)
                            
                    except Exception as e:
                        error_msg = f"Failed to process page {page_num + 1}: {e}"
                        errors.append(error_msg)
                        self.logger.warning(error_msg)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            confidence = self._calculate_confidence(entries)
            
            return ParseResult(
                entries=entries,
                confidence=confidence,
                method_used="pdfplumber_structured_extraction",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={
                    'total_pages': len(pdf.pages),
                    'total_entries': len(entries),
                    'extraction_method': 'table' if any('table' in str(e) for e in errors) else 'text'
                }
            )
            
        except ImportError:
            error_msg = "PDFPlumber not installed. Install with: pip install pdfplumber"
            errors.append(error_msg)
            self.logger.error(error_msg)
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="pdfplumber_not_available",
                processing_time_ms=0,
                errors=errors,
                metadata={}
            )
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"PDFPlumber parsing failed: {e}"
            errors.append(error_msg)
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="pdfplumber_failed",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={}
            )
    
    async def parse_catalog(self, pdf_path: Path, brand: str, year: int) -> ParseResult:
        """Parse catalog using PDFPlumber with precise positioning"""
        start_time = datetime.now()
        base_models = []
        errors = []
        
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                current_model = None
                current_specs = {}
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Analyze page layout
                        layout = self._analyze_page_layout(page)
                        
                        # Extract based on detected layout
                        if layout['has_structured_content']:
                            page_data = await self._extract_structured_catalog_page(
                                page, brand, year, page_num
                            )
                        else:
                            page_data = await self._extract_freeform_catalog_page(
                                page, brand, year, page_num
                            )
                        
                        # Process extracted data
                        if page_data.get('model_family'):
                            # Save previous model if we have one
                            if current_model and current_specs:
                                base_model = self._build_base_model_dict(
                                    current_model, current_specs, brand, year, [page_num-1]
                                )
                                base_models.append(base_model)
                            
                            # Start new model
                            current_model = page_data['model_family']
                            current_specs = page_data.get('specifications', {})
                        else:
                            # Add to current model specifications
                            if page_data.get('specifications'):
                                current_specs.update(page_data['specifications'])
                        
                    except Exception as e:
                        error_msg = f"Failed to process catalog page {page_num + 1}: {e}"
                        errors.append(error_msg)
                        self.logger.warning(error_msg)
                
                # Don't forget the last model
                if current_model and current_specs:
                    base_model = self._build_base_model_dict(
                        current_model, current_specs, brand, year, [len(pdf.pages)-1]
                    )
                    base_models.append(base_model)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            confidence = self._calculate_catalog_confidence(base_models)
            
            return ParseResult(
                entries=base_models,
                confidence=confidence,
                method_used="pdfplumber_catalog_extraction",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={
                    'total_pages': len(pdf.pages) if 'pdf' in locals() else 0,
                    'models_extracted': len(base_models)
                }
            )
            
        except ImportError:
            error_msg = "PDFPlumber not installed. Install with: pip install pdfplumber"
            errors.append(error_msg)
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="pdfplumber_not_available",
                processing_time_ms=0,
                errors=errors,
                metadata={}
            )
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"PDFPlumber catalog parsing failed: {e}"
            errors.append(error_msg)
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="pdfplumber_catalog_failed",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={}
            )
    
    async def _process_pdfplumber_table(
        self, 
        table: List[List[str]], 
        market: str, 
        brand: str, 
        year: int, 
        page_num: int, 
        table_idx: int
    ) -> List[Dict[str, Any]]:
        """Process a PDFPlumber-extracted table"""
        entries = []
        
        if not table or len(table) < 2:
            return entries
        
        try:
            # Detect headers
            headers = table[0] if table else []
            headers = [h.strip().lower() if h else "" for h in headers]
            
            # Create field mapping
            field_mapping = self._create_field_mapping_from_headers(headers, market)
            
            if not field_mapping.get('model_code') or not field_mapping.get('price'):
                self.logger.warning(
                    f"Required fields not found in table {table_idx} on page {page_num + 1}"
                )
                return entries
            
            # Process data rows
            for row_idx, row in enumerate(table[1:], 1):
                try:
                    if not row or len(row) <= max(field_mapping.values()):
                        continue
                    
                    # Extract and validate model code
                    model_code = row[field_mapping['model_code']].strip() if field_mapping.get('model_code') else None
                    if not self._is_valid_model_code(model_code):
                        continue
                    
                    # Extract and validate price
                    price_str = row[field_mapping['price']].strip() if field_mapping.get('price') else None
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
                        if field in field_mapping and field_mapping[field] < len(row):
                            value = row[field_mapping[field]].strip() if row[field_mapping[field]] else None
                            entry_data[field] = value if value else None
                    
                    # Build complete entry
                    entry = self._build_price_entry_dict(entry_data, brand, market, year, None)
                    entries.append(entry)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process row {row_idx} in table {table_idx}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Failed to process PDFPlumber table {table_idx}: {e}")
        
        return entries
    
    async def _process_pdfplumber_text(
        self, 
        page, 
        market: str, 
        brand: str, 
        year: int, 
        page_num: int
    ) -> List[Dict[str, Any]]:
        """Process page using text-based extraction when tables aren't detected"""
        entries = []
        
        try:
            # Extract all text
            text = page.extract_text()
            if not text:
                return entries
            
            # Look for price list patterns using regex
            import re
            
            # Market-specific patterns
            patterns = {
                'FI': r'([A-Z0-9]{2,8})\s+([^€]+?)\s+€\s*([0-9,]+(?:\.[0-9]{2})?)',  # Finnish
                'SE': r'([A-Z0-9]{2,8})\s+([^kr]+?)\s+([0-9,]+(?:\.[0-9]{2})?\s*kr)',  # Swedish
                'NO': r'([A-Z0-9]{2,8})\s+([^kr]+?)\s+([0-9,]+(?:\.[0-9]{2})?\s*kr)'   # Norwegian
            }
            
            pattern = patterns.get(market, patterns['FI'])
            
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            
            for match in matches:
                try:
                    model_code = match.group(1).strip()
                    description = match.group(2).strip()
                    price_str = match.group(3).strip()
                    
                    if not self._is_valid_model_code(model_code):
                        continue
                    
                    price = self._parse_price(price_str)
                    if not price or price <= 0:
                        continue
                    
                    # Parse description for additional fields
                    description_parts = self._parse_description(description, market)
                    
                    # Build entry data
                    entry_data = {
                        'model_code': model_code,
                        'price': price,
                        'currency': 'EUR',
                        **description_parts
                    }
                    
                    # Build complete entry
                    entry = self._build_price_entry_dict(entry_data, brand, market, year, None)
                    entries.append(entry)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process text match on page {page_num + 1}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Failed to process PDFPlumber text on page {page_num + 1}: {e}")
        
        return entries
    
    def _analyze_page_layout(self, page) -> Dict[str, bool]:
        """Analyze page layout to determine extraction strategy"""
        layout = {
            'has_structured_content': False,
            'has_tables': False,
            'has_images': False,
            'text_blocks_count': 0
        }
        
        try:
            # Check for tables
            tables = page.extract_tables()
            layout['has_tables'] = len(tables) > 0
            
            # Check text structure
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                non_empty_lines = [line for line in lines if line.strip()]
                layout['text_blocks_count'] = len(non_empty_lines)
            
            # Check for images (basic detection)
            try:
                images = page.images
                layout['has_images'] = len(images) > 0
            except:
                layout['has_images'] = False
            
            # Determine if content is structured
            layout['has_structured_content'] = (
                layout['has_tables'] or 
                layout['text_blocks_count'] > 10
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze page layout: {e}")
        
        return layout
    
    async def _extract_structured_catalog_page(
        self, 
        page, 
        brand: str, 
        year: int, 
        page_num: int
    ) -> Dict[str, Any]:
        """Extract from structured catalog page"""
        extracted_data = {
            'model_family': None,
            'specifications': {}
        }
        
        try:
            # Extract tables first
            tables = page.extract_tables()
            
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # Look for model name in table
                for row in table[:3]:  # Check first few rows
                    for cell in row:
                        if cell and isinstance(cell, str) and len(cell.strip()) > 5:
                            cell_clean = cell.strip()
                            if any(keyword in cell_clean.upper() for keyword in ['RE', 'RS', 'XT', 'SPORT']):
                                extracted_data['model_family'] = cell_clean
                                break
                    if extracted_data['model_family']:
                        break
                
                # Extract specifications from table
                specs = self._extract_specs_from_table(table)
                extracted_data['specifications'].update(specs)
            
            # Extract from text if no model found in tables
            if not extracted_data['model_family']:
                text = page.extract_text()
                extracted_data['model_family'] = self._extract_model_from_text(text, brand)
            
        except Exception as e:
            self.logger.warning(f"Failed to extract structured catalog page {page_num + 1}: {e}")
        
        return extracted_data
    
    async def _extract_freeform_catalog_page(
        self, 
        page, 
        brand: str, 
        year: int, 
        page_num: int
    ) -> Dict[str, Any]:
        """Extract from freeform catalog page"""
        extracted_data = {
            'model_family': None,
            'specifications': {}
        }
        
        try:
            # Extract all text
            text = page.extract_text()
            if not text:
                return extracted_data
            
            # Look for model family
            extracted_data['model_family'] = self._extract_model_from_text(text, brand)
            
            # Extract specifications from text
            extracted_data['specifications'] = self._extract_specs_from_text(text)
            
        except Exception as e:
            self.logger.warning(f"Failed to extract freeform catalog page {page_num + 1}: {e}")
        
        return extracted_data
    
    def _create_field_mapping_from_headers(self, headers: List[str], market: str) -> Dict[str, int]:
        """Create field mapping from headers"""
        mapping = {}
        
        # Market-specific patterns
        field_patterns = self._get_field_patterns_for_market(market)
        
        for field, patterns in field_patterns.items():
            for i, header in enumerate(headers):
                if any(pattern in header for pattern in patterns):
                    mapping[field] = i
                    break
        
        return mapping
    
    def _get_field_patterns_for_market(self, market: str) -> Dict[str, List[str]]:
        """Get field patterns for specific market"""
        patterns = {
            'FI': {
                'model_code': ['mallikoodi', 'koodi', 'model'],
                'malli': ['malli', 'model'],
                'paketti': ['paketti', 'package'],
                'moottori': ['moottori', 'engine'],
                'telamatto': ['telamatto', 'track'],
                'kaynnistin': ['käynnistin', 'starter'],
                'mittaristo': ['mittaristo', 'instruments'],
                'kevatoptiot': ['kevätoptiot', 'options'],
                'vari': ['väri', 'color'],
                'price': ['hinta', 'price', '€']
            },
            'SE': {
                'model_code': ['modellkod', 'kod', 'model'],
                'malli': ['modell', 'model'],
                'paketti': ['paket', 'package'],
                'moottori': ['motor', 'engine'],
                'telamatto': ['band', 'track'],
                'kaynnistin': ['startare', 'starter'],
                'mittaristo': ['instrument', 'display'],
                'kevatoptiot': ['våralternativ', 'options'],
                'vari': ['färg', 'color'],
                'price': ['pris', 'price', 'kr']
            },
            'NO': {
                'model_code': ['modellkode', 'kode', 'model'],
                'malli': ['modell', 'model'],
                'paketti': ['pakke', 'package'],
                'moottori': ['motor', 'engine'],
                'telamatto': ['belter', 'track'],
                'kaynnistin': ['starter'],
                'mittaristo': ['instrumenter', 'display'],
                'kevatoptiot': ['våralternativer', 'options'],
                'vari': ['farge', 'color'],
                'price': ['pris', 'price', 'kr']
            }
        }
        
        return patterns.get(market, patterns['FI'])
    
    def _parse_description(self, description: str, market: str) -> Dict[str, Optional[str]]:
        """Parse description text into structured fields"""
        fields = {
            'malli': None,
            'paketti': None,
            'moottori': None,
            'telamatto': None,
            'vari': None
        }
        
        try:
            import re
            
            # Common patterns for extracting information
            patterns = {
                'engine': r'([0-9]+R?\s*(?:E-TEC|ETEC|ACE|TBI)(?:\s*Turbo)?)',
                'track': r'([0-9]+(?:in|"|\s*inch))',
                'color': r'(Red|Blue|Black|White|Yellow|Green|Silver|Viper|Arctic)'
            }
            
            desc_lower = description.lower()
            
            # Extract engine
            engine_match = re.search(patterns['engine'], description, re.IGNORECASE)
            if engine_match:
                fields['moottori'] = engine_match.group(1).strip()
            
            # Extract track
            track_match = re.search(patterns['track'], description, re.IGNORECASE)
            if track_match:
                fields['telamatto'] = track_match.group(1).strip()
            
            # Extract color
            color_match = re.search(patterns['color'], description, re.IGNORECASE)
            if color_match:
                fields['vari'] = color_match.group(1).strip()
            
            # Extract model name (first word usually)
            words = description.split()
            if words:
                first_word = words[0].strip()
                if len(first_word) > 2 and first_word.isalpha():
                    fields['malli'] = first_word
            
        except Exception as e:
            self.logger.warning(f"Failed to parse description '{description}': {e}")
        
        return fields
    
    def _extract_specs_from_table(self, table: List[List[str]]) -> Dict[str, Any]:
        """Extract specifications from table data"""
        specs = {}
        
        try:
            for row in table:
                if len(row) >= 2:
                    key = row[0].strip().lower() if row[0] else ""
                    value = row[1].strip() if row[1] else ""
                    
                    if key and value:
                        if 'engine' in key or 'motor' in key:
                            if 'engine_options' not in specs:
                                specs['engine_options'] = {}
                            specs['engine_options'][key] = value
                        
                        elif 'track' in key or 'belt' in key:
                            if 'track_options' not in specs:
                                specs['track_options'] = {}
                            specs['track_options'][key] = value
                        
                        elif any(dim in key for dim in ['length', 'width', 'height', 'weight']):
                            if 'dimensions' not in specs:
                                specs['dimensions'] = {}
                            specs['dimensions'][key] = value
        
        except Exception as e:
            self.logger.warning(f"Failed to extract specs from table: {e}")
        
        return specs
    
    def _extract_specs_from_text(self, text: str) -> Dict[str, Any]:
        """Extract specifications from free text"""
        specs = {}
        
        try:
            import re
            
            # Engine specifications
            engine_matches = re.findall(
                r'([0-9]+R?\s*(?:E-TEC|ETEC|ACE|TBI)(?:\s*Turbo)?[^\n]*)',
                text, re.IGNORECASE
            )
            if engine_matches:
                specs['engine_options'] = {f'engine_{i}': match for i, match in enumerate(engine_matches)}
            
            # Track specifications
            track_matches = re.findall(
                r'([0-9]+(?:in|"|\s*inch)[^\n]*)',
                text, re.IGNORECASE
            )
            if track_matches:
                specs['track_options'] = {f'track_{i}': match for i, match in enumerate(track_matches)}
            
            # Features (lines starting with bullet points or dashes)
            feature_matches = re.findall(r'^[\s]*[-•*]\s*([^\n]+)', text, re.MULTILINE)
            if feature_matches:
                specs['features'] = [f.strip() for f in feature_matches if len(f.strip()) > 5]
        
        except Exception as e:
            self.logger.warning(f"Failed to extract specs from text: {e}")
        
        return specs
    
    def _extract_model_from_text(self, text: str, brand: str) -> Optional[str]:
        """Extract model family name from text"""
        import re
        
        patterns = [
            rf'{brand}\s+([A-Z][a-zA-Z\s]+(?:RE|RS|XT|SWT|SPORT))',
            r'^([A-Z][a-zA-Z\s]+(?:RE|RS|XT|SWT|SPORT))\s*$',
            r'(\w+\s+(?:RE|RS|XT|SWT|SPORT))',
        ]
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 50:
                continue
            
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    model_name = match.group(1).strip()
                    if len(model_name) > 2:
                        return model_name
        
        return None
    
    def _build_base_model_dict(self, model_family: str, specifications: Dict[str, Any], brand: str, year: int, source_pages: List[int]) -> Dict[str, Any]:
        """Build base model dictionary"""
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
            'source_pages': source_pages,
            'extraction_confidence': Decimal("0.80"),
            'completeness_score': self._calculate_completeness_score(specifications)
        }
    
    def _calculate_completeness_score(self, specifications: Dict[str, Any]) -> Decimal:
        """Calculate completeness score"""
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
        """Calculate confidence for catalog extraction"""
        if not base_models:
            return Decimal("0.0")
        
        total_score = 0
        max_score = len(base_models) * 100
        
        for model in base_models:
            model_score = 0
            
            if model.get('model_family'):
                model_score += 40
            if model.get('lookup_key'):
                model_score += 20
            
            specs = model.get('full_specifications', {})
            if specs.get('engine_options'):
                model_score += 20
            if specs.get('track_options'):
                model_score += 20
            
            total_score += model_score
        
        confidence = total_score / max_score if max_score > 0 else 0
        return Decimal(str(min(1.0, confidence)))