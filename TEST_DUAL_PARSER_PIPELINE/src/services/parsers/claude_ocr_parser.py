import asyncio
import base64
import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import os

from .base_parser import BaseParser, ParseResult, PDFQuality


class ClaudeOCRParser(BaseParser):
    """Claude OCR parser - fallback for scanned/poor quality PDFs using AI vision"""
    
    def __init__(self):
        super().__init__()
        self.claude_client = None
        self._initialize_claude()
    
    def _initialize_claude(self):
        """Initialize Claude client"""
        try:
            from anthropic import AsyncAnthropic
            api_key = os.getenv("CLAUDE_API_KEY")
            if api_key:
                self.claude_client = AsyncAnthropic(api_key=api_key)
            else:
                self.logger.warning("CLAUDE_API_KEY not set, Claude OCR parser will not be available")
        except ImportError:
            self.logger.warning("Anthropic package not installed, Claude OCR parser will not be available")
    
    async def can_parse(self, pdf_path: Path, quality: PDFQuality) -> bool:
        """Check if Claude OCR can handle this PDF"""
        # Best for scanned documents or when other parsers fail
        return (self.claude_client is not None and 
                (quality.is_scanned or 
                 quality.text_quality_score < 0.5 or 
                 quality.extraction_difficulty == "hard"))
    
    async def parse_price_list(self, pdf_path: Path, market: str, brand: str, year: int) -> ParseResult:
        """Parse price list using Claude OCR"""
        start_time = datetime.now()
        entries = []
        errors = []
        
        if not self.claude_client:
            error_msg = "Claude client not initialized. Check CLAUDE_API_KEY."
            errors.append(error_msg)
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="claude_ocr_unavailable",
                processing_time_ms=0,
                errors=errors,
                metadata={}
            )
        
        try:
            # Convert PDF pages to images
            images = await self._pdf_to_images(pdf_path)
            
            if not images:
                error_msg = "Failed to convert PDF to images"
                errors.append(error_msg)
                return ParseResult(
                    entries=[],
                    confidence=Decimal("0.0"),
                    method_used="claude_ocr_conversion_failed",
                    processing_time_ms=0,
                    errors=errors,
                    metadata={}
                )
            
            # Process each page with Claude
            for page_num, image_data in enumerate(images):
                try:
                    self.logger.info(f"Processing page {page_num + 1} with Claude OCR")
                    
                    page_entries = await self._process_page_with_claude(
                        image_data, market, brand, year, page_num
                    )
                    entries.extend(page_entries)
                    
                    # Add delay to respect API rate limits
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Failed to process page {page_num + 1} with Claude: {e}"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            confidence = self._calculate_confidence(entries)
            
            return ParseResult(
                entries=entries,
                confidence=confidence,
                method_used="claude_ocr_vision",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={
                    'total_pages': len(images),
                    'total_entries': len(entries),
                    'api_calls': len(images)
                }
            )
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"Claude OCR parsing failed: {e}"
            errors.append(error_msg)
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="claude_ocr_failed",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={}
            )
    
    async def parse_catalog(self, pdf_path: Path, brand: str, year: int) -> ParseResult:
        """Parse catalog using Claude OCR (limited implementation)"""
        start_time = datetime.now()
        base_models = []
        errors = []
        
        if not self.claude_client:
            error_msg = "Claude client not initialized. Check CLAUDE_API_KEY."
            errors.append(error_msg)
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="claude_ocr_unavailable",
                processing_time_ms=0,
                errors=errors,
                metadata={}
            )
        
        try:
            # Convert PDF pages to images (limit to first few pages for catalogs)
            images = await self._pdf_to_images(pdf_path, max_pages=5)
            
            if not images:
                error_msg = "Failed to convert catalog PDF to images"
                errors.append(error_msg)
                return ParseResult(
                    entries=[],
                    confidence=Decimal("0.0"),
                    method_used="claude_ocr_conversion_failed",
                    processing_time_ms=0,
                    errors=errors,
                    metadata={}
                )
            
            # Process each page for catalog information
            for page_num, image_data in enumerate(images):
                try:
                    self.logger.info(f"Processing catalog page {page_num + 1} with Claude OCR")
                    
                    page_models = await self._process_catalog_page_with_claude(
                        image_data, brand, year, page_num
                    )
                    base_models.extend(page_models)
                    
                    # Add delay for API rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Failed to process catalog page {page_num + 1}: {e}"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            confidence = self._calculate_catalog_confidence(base_models)
            
            return ParseResult(
                entries=base_models,
                confidence=confidence,
                method_used="claude_ocr_catalog",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={
                    'pages_processed': len(images),
                    'models_extracted': len(base_models),
                    'api_calls': len(images)
                }
            )
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"Claude OCR catalog parsing failed: {e}"
            errors.append(error_msg)
            
            return ParseResult(
                entries=[],
                confidence=Decimal("0.0"),
                method_used="claude_ocr_catalog_failed",
                processing_time_ms=processing_time,
                errors=errors,
                metadata={}
            )
    
    async def _pdf_to_images(self, pdf_path: Path, max_pages: Optional[int] = None, dpi: int = 200) -> List[bytes]:
        """Convert PDF pages to images"""
        images = []
        
        try:
            import fitz  # PyMuPDF for PDF to image conversion
            
            doc = fitz.open(pdf_path)
            
            page_count = len(doc)
            if max_pages:
                page_count = min(page_count, max_pages)
            
            for page_num in range(page_count):
                page = doc[page_num]
                
                # Render page to image
                mat = fitz.Matrix(dpi/72, dpi/72)  # Scale factor for DPI
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PNG bytes
                img_bytes = pix.pil_tobytes(format="PNG")
                images.append(img_bytes)
                
                self.logger.debug(f"Converted page {page_num + 1} to image ({len(img_bytes)} bytes)")
            
            doc.close()
            
        except ImportError:
            self.logger.error("PyMuPDF not available for PDF to image conversion")
        except Exception as e:
            self.logger.error(f"Failed to convert PDF to images: {e}")
        
        return images
    
    async def _process_page_with_claude(
        self, 
        image_data: bytes, 
        market: str, 
        brand: str, 
        year: int, 
        page_num: int
    ) -> List[Dict[str, Any]]:
        """Process a single page image with Claude Vision API"""
        
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Build market-specific prompt
            prompt = self._build_price_list_prompt(market, brand, year)
            
            # Call Claude Vision API
            response = await self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_b64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # Parse Claude response
            response_text = response.content[0].text
            entries = self._parse_claude_price_response(response_text, brand, market, year, page_num)
            
            return entries
            
        except Exception as e:
            self.logger.error(f"Failed to process page {page_num + 1} with Claude: {e}")
            return []
    
    async def _process_catalog_page_with_claude(
        self, 
        image_data: bytes, 
        brand: str, 
        year: int, 
        page_num: int
    ) -> List[Dict[str, Any]]:
        """Process a catalog page with Claude Vision API"""
        
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Build catalog extraction prompt
            prompt = self._build_catalog_prompt(brand, year)
            
            # Call Claude Vision API
            response = await self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_b64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # Parse Claude response
            response_text = response.content[0].text
            models = self._parse_claude_catalog_response(response_text, brand, year, page_num)
            
            return models
            
        except Exception as e:
            self.logger.error(f"Failed to process catalog page {page_num + 1} with Claude: {e}")
            return []
    
    def _build_price_list_prompt(self, market: str, brand: str, year: int) -> str:
        """Build market-specific prompt for price list extraction"""
        
        market_info = {
            'FI': {
                'language': 'Finnish',
                'currency': '€ (Euro)',
                'columns': 'Mallikoodi (Model Code), Malli, Paketti, Moottori, Telamatto, Käynnistin, Mittaristo, Kevätoptiot, Väri, Hinta'
            },
            'SE': {
                'language': 'Swedish', 
                'currency': 'kr (Swedish Krona)',
                'columns': 'Modellkod, Modell, Paket, Motor, Band, Startare, Instrument, Våralternativ, Färg, Pris'
            },
            'NO': {
                'language': 'Norwegian',
                'currency': 'kr (Norwegian Krone)',
                'columns': 'Modellkode, Modell, Pakke, Motor, Belter, Starter, Instrumenter, Våralternativer, Farge, Pris'
            }
        }
        
        info = market_info.get(market, market_info['FI'])
        
        return f"""
Extract snowmobile price list data from this image.

**Context:**
- Brand: {brand}
- Year: {year}
- Market: {market} ({info['language']})
- Currency: {info['currency']}

**Expected Table Columns:**
{info['columns']}

**Instructions:**
1. Look for tabular data with snowmobile models and prices
2. Extract each row as a separate entry
3. Validate model codes (should be 2-8 alphanumeric characters)
4. Parse prices correctly (remove currency symbols, handle commas/decimals)
5. Return data as valid JSON array

**Required JSON Format:**
```json
[
  {{
    "model_code": "LTTA",
    "malli": "Rave",
    "paketti": "RE", 
    "moottori": "600R E-TEC",
    "telamatto": "137in 3500mm",
    "kaynnistin": "Manual",
    "mittaristo": "7.2 in. Digital Display",
    "kevatoptiot": "Black edition",
    "vari": "Viper Red / Black",
    "price": "18750.00"
  }}
]
```

**Important:**
- Only extract valid, complete rows
- Model codes must be 2-8 characters (letters/numbers)
- Prices must be numeric values (no currency symbols)
- Return empty array [] if no valid data found
- Ensure JSON is valid and parseable
"""
    
    def _build_catalog_prompt(self, brand: str, year: int) -> str:
        """Build prompt for catalog extraction"""
        
        return f"""
Extract snowmobile model specifications from this catalog page.

**Context:**
- Brand: {brand}
- Year: {year}
- Document Type: Product Specification Catalog

**Instructions:**
1. Look for model family names (e.g., "Rave RE", "Summit X", "Backcountry X-RS")
2. Extract available engine options with specifications
3. Extract track options and dimensions
4. Extract standard features and equipment lists
5. Extract technical specifications (dimensions, weight, etc.)

**Required JSON Format:**
```json
[
  {{
    "model_family": "Rave RE",
    "engine_options": {{
      "600R_E-TEC": {{
        "displacement": "600R",
        "type": "E-TEC",
        "power": "125 HP",
        "full_name": "Rotax 600R E-TEC"
      }},
      "850_E-TEC": {{
        "displacement": "850",
        "type": "E-TEC", 
        "power": "165 HP",
        "full_name": "Rotax 850 E-TEC"
      }}
    }},
    "track_options": {{
      "137in": {{
        "length_inches": 137,
        "width": "3500mm",
        "full_description": "137in x 3500mm Cobra track"
      }}
    }},
    "dimensions": {{
      "length": "3060mm",
      "width": "1120mm", 
      "height": "1270mm",
      "weight": "237kg"
    }},
    "features": [
      "Electric starter",
      "LED headlights",
      "Quick-release seat",
      "Digital display"
    ]
  }}
]
```

**Important:**
- Focus on model families, not individual model codes
- Extract comprehensive specification data
- Group related specifications logically
- Return empty array [] if no model data found
- Ensure JSON is valid and parseable
"""
    
    def _parse_claude_price_response(
        self, 
        response_text: str, 
        brand: str, 
        market: str, 
        year: int, 
        page_num: int
    ) -> List[Dict[str, Any]]:
        """Parse Claude's JSON response for price list data"""
        entries = []
        
        try:
            # Extract JSON from response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                self.logger.warning(f"No JSON array found in Claude response for page {page_num + 1}")
                return entries
            
            json_str = response_text[json_start:json_end]
            parsed_data = json.loads(json_str)
            
            # Process each entry
            for item in parsed_data:
                try:
                    # Validate required fields
                    if not item.get('model_code') or not item.get('price'):
                        continue
                    
                    # Validate model code format
                    if not self._is_valid_model_code(item['model_code']):
                        continue
                    
                    # Parse price
                    price = self._parse_price(str(item['price']))
                    if not price or price <= 0:
                        continue
                    
                    # Build entry data
                    entry_data = {
                        'model_code': str(item['model_code']).strip(),
                        'price': price,
                        'currency': 'EUR'
                    }
                    
                    # Add optional fields
                    optional_fields = ['malli', 'paketti', 'moottori', 'telamatto', 
                                     'kaynnistin', 'mittaristo', 'kevatoptiot', 'vari']
                    
                    for field in optional_fields:
                        if field in item and item[field]:
                            entry_data[field] = str(item[field]).strip()
                    
                    # Build complete entry
                    entry = self._build_price_entry_dict(entry_data, brand, market, year, None)
                    entries.append(entry)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process Claude entry on page {page_num + 1}: {e}")
                    continue
            
            self.logger.info(f"Claude OCR extracted {len(entries)} valid entries from page {page_num + 1}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Claude JSON response for page {page_num + 1}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to process Claude response for page {page_num + 1}: {e}")
        
        return entries
    
    def _parse_claude_catalog_response(
        self, 
        response_text: str, 
        brand: str, 
        year: int, 
        page_num: int
    ) -> List[Dict[str, Any]]:
        """Parse Claude's JSON response for catalog data"""
        models = []
        
        try:
            # Extract JSON from response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                self.logger.warning(f"No JSON array found in Claude catalog response for page {page_num + 1}")
                return models
            
            json_str = response_text[json_start:json_end]
            parsed_data = json.loads(json_str)
            
            # Process each model
            for item in parsed_data:
                try:
                    # Validate required fields
                    if not item.get('model_family'):
                        continue
                    
                    # Build base model dictionary
                    from uuid import uuid4
                    
                    model_family = str(item['model_family']).strip()
                    model_clean = model_family.replace(' ', '_')
                    lookup_key = f"{brand}_{model_clean}_{year}"
                    
                    model_dict = {
                        'id': uuid4(),
                        'lookup_key': lookup_key,
                        'brand': brand,
                        'model_family': model_family,
                        'model_year': year,
                        'engine_options': item.get('engine_options', {}),
                        'track_options': item.get('track_options', {}),
                        'suspension_options': item.get('suspension_options', {}),
                        'starter_options': item.get('starter_options', {}),
                        'dimensions': item.get('dimensions', {}),
                        'features': item.get('features', []),
                        'full_specifications': item,
                        'marketing_description': None,
                        'source_pages': [page_num],
                        'extraction_confidence': Decimal("0.75"),  # OCR confidence
                        'completeness_score': self._calculate_completeness_score(item)
                    }
                    
                    models.append(model_dict)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process Claude catalog entry on page {page_num + 1}: {e}")
                    continue
            
            self.logger.info(f"Claude OCR extracted {len(models)} models from catalog page {page_num + 1}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Claude catalog JSON for page {page_num + 1}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to process Claude catalog response for page {page_num + 1}: {e}")
        
        return models
    
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