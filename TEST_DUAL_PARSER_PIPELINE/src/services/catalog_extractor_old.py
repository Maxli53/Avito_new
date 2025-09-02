import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
from uuid import UUID, uuid4
import json
import re

from ..models.domain import BaseModel, Catalog, ExtractionResult, ProcessingStatus
from ..repositories.database import DatabaseRepository
from .parsers import (
    PyMuPDFParser, CamelotParser, PDFPlumberParser, ClaudeOCRParser,
    PDFQuality, ParseResult, CatalogSection
)


logger = logging.getLogger(__name__)


class CatalogExtractor:
    """Sophisticated catalog extraction handling complex layouts"""
    
    def __init__(self, db_repo: DatabaseRepository):
        self.db_repo = db_repo
        self.parsers = {
            'pymupdf': PyMuPDFParser(),      # Fast, good for digital PDFs
            'camelot': CamelotParser(),      # Excellent for complex tables
            'pdfplumber': PDFPlumberParser(), # Good for structured data
            'claude_ocr': ClaudeOCRParser()  # Fallback for scanned/poor quality
        }
        
    async def extract_from_pdf(self, pdf_path: Path, catalog_id: UUID) -> ExtractionResult:
        """
        Extract from complex multi-page catalog layouts
        
        Args:
            pdf_path: Path to the catalog PDF
            catalog_id: UUID of the catalog record
            
        Returns:
            ExtractionResult with extraction statistics
        """
        start_time = datetime.now()
        logger.info(f"Starting sophisticated catalog extraction from {pdf_path}")
        
        try:
            # Get catalog metadata
            catalog = await self.db_repo.get_catalog(catalog_id)
            if not catalog:
                raise ValueError(f"Catalog {catalog_id} not found")
            
            # Step 1: Analyze catalog structure
            structure = await self._analyze_catalog_structure(pdf_path)
            logger.info(f"Catalog structure analysis: {len(structure.sections)} sections found")
            
            # Step 2: Process by section type
            base_models = []
            
            for section in structure.sections:
                try:
                    if section.section_type == 'model_overview':
                        model = await self._extract_model_section(section, catalog)
                        if model:
                            base_models.append(model)
                    elif section.section_type == 'specifications_table':
                        specs = await self._extract_specs_table(section)
                        self._merge_specs_to_model(base_models, specs)
                    elif section.section_type == 'features_list':
                        features = await self._extract_features(section)
                        self._merge_features_to_model(base_models, features)
                except Exception as e:
                    logger.warning(f"Failed to process section {section.section_type}: {e}")
                    continue
            
            # Step 3: Fallback to parser-based extraction if structure analysis failed
            if not base_models:
                logger.info("Structure-based extraction yielded no results, trying parser-based approach")
                result = await self._extract_with_parsers(pdf_path, catalog)
                base_models = result.entries if result.success else []
            
            # Store models in database
            stored_count = await self._store_models(base_models, catalog_id)
            
            # Update catalog statistics
            await self.db_repo.update_catalog_stats(
                catalog_id,
                total_models_extracted=stored_count,
                status=ProcessingStatus.COMPLETED
            )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            logger.info(f"Sophisticated catalog extraction completed: {stored_count} models in {processing_time}ms")
            
            return ExtractionResult(
                success=True,
                entries_extracted=stored_count,
                entries_failed=len(base_models) - stored_count,
                confidence_score=Decimal("0.85"),  # Good confidence for sophisticated extraction
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Sophisticated catalog extraction failed: {str(e)}")
            
            await self.db_repo.update_catalog_stats(
                catalog_id,
                status=ProcessingStatus.FAILED
            )
            
            return ExtractionResult(
                success=False,
                entries_extracted=0,
                entries_failed=0,
                error_message=str(e)
            )
    
    async def _analyze_catalog_structure(self, pdf_path: Path) -> 'CatalogStructure':
        """Analyze catalog structure to identify sections"""
        from dataclasses import dataclass
        
        @dataclass
        class CatalogStructure:
            sections: List[CatalogSection]
            total_pages: int
            extraction_difficulty: str
        
        sections = []
        
        try:
            import fitz
            doc = fitz.open(pdf_path)
            
            for page_num in range(min(10, len(doc))):  # Analyze first 10 pages
                page = doc[page_num]
                text = page.get_text()
                
                # Detect section type based on content patterns
                section_type = self._detect_section_type(text)
                
                if section_type:
                    section = CatalogSection(
                        pdf_path=pdf_path,
                        page_num=page_num,
                        section_type=section_type,
                        has_clear_structure=len(page.find_tables()) > 0,
                        has_product_images=len(page.get_images()) > 0
                    )
                    sections.append(section)
            
            doc.close()
            
            difficulty = "medium"
            if len(sections) < 2:
                difficulty = "hard"
            elif all(s.has_clear_structure for s in sections):
                difficulty = "easy"
            
            return CatalogStructure(
                sections=sections,
                total_pages=len(doc) if doc else 0,
                extraction_difficulty=difficulty
            )
            
        except Exception as e:
            logger.warning(f"Could not analyze catalog structure: {e}")
            return CatalogStructure(sections=[], total_pages=0, extraction_difficulty="hard")
    
    def _detect_section_type(self, text: str) -> Optional[str]:
        """Detect what type of section this page contains"""
        text_lower = text.lower()
        
        # Model overview indicators
        if any(keyword in text_lower for keyword in ['specifications', 'features', 'overview']):
            if any(model in text_lower for model in ['re', 'rs', 'xt', 'sport', 'backcountry']):
                return 'model_overview'
        
        # Specifications table indicators
        if any(keyword in text_lower for keyword in ['engine', 'track', 'suspension', 'dimensions']):
            return 'specifications_table'
        
        # Features list indicators
        if any(keyword in text_lower for keyword in ['standard', 'optional', 'equipment']):
            return 'features_list'
        
        return None
    
    async def _extract_model_section(self, section: CatalogSection, catalog: Catalog) -> Optional[Dict[str, Any]]:
        """
        Extract from varied catalog layouts
        """
        
        # Strategy 1: Try structured extraction
        if section.has_clear_structure:
            return await self._extract_structured(section, catalog)
        
        # Strategy 2: Use computer vision for image-heavy pages
        if section.has_product_images:
            return await self._extract_with_cv(section, catalog)
        
        # Strategy 3: Claude for complex mixed layouts
        return await self._extract_with_claude(section, catalog)
    
    async def _extract_structured(self, section: CatalogSection, catalog: Catalog) -> Optional[Dict[str, Any]]:
        """
        Extract from well-structured catalog pages
        """
        
        try:
            # Use PDFPlumber for precise text positioning
            import pdfplumber
            
            with pdfplumber.open(section.pdf_path) as pdf:
                page = pdf.pages[section.page_num]
                
                # Extract based on coordinates
                model_name = page.within_bbox(
                    section.title_bbox or (0, 0, page.width, page.height * 0.2)
                ).extract_text()
                
                # Extract specification table
                table = page.extract_table(
                    table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "text",
                        "min_words_vertical": 2
                    }
                )
                
                # Extract features from specific regions
                features_text = page.within_bbox(
                    section.features_bbox or (0, page.height * 0.6, page.width, page.height)
                ).extract_text()
                
                return self._build_base_model(model_name, table, features_text, catalog)
        
        except ImportError:
            logger.warning("PDFPlumber not available for structured extraction")
            return None
        except Exception as e:
            logger.warning(f"Structured extraction failed: {e}")
            return None
    
    async def _extract_with_cv(self, section: CatalogSection, catalog: Catalog) -> Optional[Dict[str, Any]]:
        """
        Use computer vision for image-heavy catalog pages
        """
        
        try:
            # Convert page to image
            image = await self._page_to_image(section.pdf_path, section.page_num)
            
            # Use OCR with layout detection
            try:
                import pytesseract
                import cv2
                import numpy as np
                
                # Preprocess image
                processed = self._preprocess_for_ocr(image)
                
                # Detect text regions
                text_regions = self._detect_text_regions(processed)
                
                # Extract from each region
                extracted_data = {}
                for region in text_regions:
                    text = pytesseract.image_to_string(
                        region.image,
                        config='--psm 6'  # Uniform block of text
                    )
                    extracted_data[region.type] = text
                
                return self._build_base_model_from_cv(extracted_data, catalog)
                
            except ImportError:
                logger.warning("Computer vision libraries not available")
                return None
        
        except Exception as e:
            logger.warning(f"Computer vision extraction failed: {e}")
            return None
    
    def _extract_model_family_from_text(self, text: str, brand: str) -> Optional[str]:
        """Extract model family name from page text"""
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
            # Assume first row is headers, rest are data
            headers = [h.strip().lower() if h else "" for h in table_data[0]]
            
            for row in table_data[1:]:
                if len(row) < len(headers):
                    continue
                
                for i, value in enumerate(row):
                    if i >= len(headers):
                        break
                    
                    header = headers[i]
                    if not header or not value or not value.strip():
                        continue
                    
                    # Map common specification fields
                    if any(keyword in header for keyword in ['engine', 'motor', 'moottori']):
                        if 'engine_options' not in specs:
                            specs['engine_options'] = {}
                        self._parse_engine_specifications(value.strip(), specs['engine_options'])
                    
                    elif any(keyword in header for keyword in ['track', 'tela']):
                        if 'track_options' not in specs:
                            specs['track_options'] = {}
                        self._parse_track_specifications(value.strip(), specs['track_options'])
                    
                    elif any(keyword in header for keyword in ['dimension', 'size', 'koko']):
                        if 'dimensions' not in specs:
                            specs['dimensions'] = {}
                        self._parse_dimension_specifications(value.strip(), specs['dimensions'])
                    
                    elif any(keyword in header for keyword in ['weight', 'paino']):
                        specs['weight'] = self._parse_weight(value.strip())
                    
                    elif any(keyword in header for keyword in ['feature', 'ominaisuus']):
                        if 'features' not in specs:
                            specs['features'] = []
                        if value.strip() not in specs['features']:
                            specs['features'].append(value.strip())
        
        except Exception as e:
            logger.warning(f"Failed to extract specifications from table: {e}")
        
        return specs
    
    def _extract_specifications_from_text(self, text: str) -> Dict[str, Any]:
        """Extract specifications from free text"""
        specs = {}
        
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
        
        # Dimensions
        dimension_patterns = [
            r'Length[:\s]*([0-9,]+(?:\.[0-9]+)?\s*(?:mm|cm|m|in|ft))',
            r'Width[:\s]*([0-9,]+(?:\.[0-9]+)?\s*(?:mm|cm|m|in|ft))',
            r'Height[:\s]*([0-9,]+(?:\.[0-9]+)?\s*(?:mm|cm|m|in|ft))',
            r'Weight[:\s]*([0-9,]+(?:\.[0-9]+)?\s*(?:kg|lbs|lb))'
        ]
        
        for pattern in dimension_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if 'dimensions' not in specs:
                    specs['dimensions'] = {}
                dimension_text = match.group(1).strip()
                field_name = pattern.split('[')[0].lower()
                specs['dimensions'][field_name] = dimension_text
        
        return specs
    
    def _parse_engine_specifications(self, engine_text: str, engine_options: Dict[str, Any]):
        """Parse engine specification text into structured data"""
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
            logger.warning(f"Failed to parse engine spec '{engine_text}': {e}")
    
    def _parse_track_specifications(self, track_text: str, track_options: Dict[str, Any]):
        """Parse track specification text into structured data"""
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
            logger.warning(f"Failed to parse track spec '{track_text}': {e}")
    
    def _parse_dimension_specifications(self, dimension_text: str, dimensions: Dict[str, Any]):
        """Parse dimension text into structured data"""
        # This is handled in the calling function for now
        pass
    
    def _parse_weight(self, weight_text: str) -> Optional[str]:
        """Parse weight text"""
        weight_match = re.search(r'([0-9,]+(?:\.[0-9]+)?)\s*(kg|lbs|lb)', weight_text, re.IGNORECASE)
        if weight_match:
            return weight_match.group(0)
        return None
    
    def _split_text_into_model_sections(self, text: str, brand: str) -> List[str]:
        """Split catalog text into individual model sections"""
        # This is a simplified approach - in practice, you'd need more sophisticated parsing
        sections = []
        current_section = ""
        
        lines = text.split('\n')
        in_model_section = False
        
        for line in lines:
            line = line.strip()
            
            # Check if this line starts a new model section
            if self._is_model_header(line, brand):
                if current_section.strip():
                    sections.append(current_section.strip())
                current_section = line + "\n"
                in_model_section = True
            elif in_model_section:
                current_section += line + "\n"
        
        # Don't forget the last section
        if current_section.strip():
            sections.append(current_section.strip())
        
        return sections
    
    def _is_model_header(self, line: str, brand: str) -> bool:
        """Check if a line represents a model header"""
        # Simple heuristics for model headers
        if len(line) > 50:  # Headers are usually short
            return False
        
        if any(keyword in line.upper() for keyword in ['RE', 'RS', 'XT', 'SWT', 'SPORT']):
            return True
        
        if brand.upper() in line.upper() and len(line.split()) <= 4:
            return True
        
        return False
    
    def _parse_text_model_section(self, section: str, catalog: Catalog) -> Optional[Dict[str, Any]]:
        """Parse a text section into a model dictionary"""
        lines = section.split('\n')
        if not lines:
            return None
        
        model_family = lines[0].strip()
        if not model_family:
            return None
        
        specifications = self._extract_specifications_from_text(section)
        
        return self._create_base_model_dict(model_family, specifications, catalog, [1])
    
    def _create_base_model_dict(self, model_family: str, specifications: Dict[str, Any], catalog: Catalog, source_pages: List[int]) -> Dict[str, Any]:
        """Create a standardized base model dictionary"""
        # Generate lookup key
        model_clean = model_family.replace(' ', '_')
        lookup_key = f"{catalog.brand}_{model_clean}_{catalog.model_year}"
        
        return {
            'id': uuid4(),
            'catalog_id': catalog.id,
            'lookup_key': lookup_key,
            'brand': catalog.brand,
            'model_family': model_family,
            'model_year': catalog.model_year,
            'engine_options': specifications.get('engine_options', {}),
            'track_options': specifications.get('track_options', {}),
            'suspension_options': specifications.get('suspension_options', {}),
            'starter_options': specifications.get('starter_options', {}),
            'dimensions': specifications.get('dimensions', {}),
            'features': specifications.get('features', []),
            'full_specifications': specifications,
            'marketing_description': None,  # Could be extracted separately
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
    
    def _validate_models(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate extracted models"""
        validated = []
        
        for model in models:
            # Required fields validation
            if not model.get('model_family') or not model.get('lookup_key'):
                logger.warning(f"Skipping model with missing required fields: {model.get('model_family')}")
                continue
            
            # Must have at least one specification category
            has_specs = any(
                model.get(field) for field in ['engine_options', 'track_options', 'dimensions', 'features']
            )
            if not has_specs:
                logger.warning(f"Skipping model with no specifications: {model['model_family']}")
                continue
            
            validated.append(model)
        
        logger.info(f"Validated {len(validated)} of {len(models)} models")
        return validated
    
    async def _extract_with_claude(self, section: CatalogSection, catalog: Catalog) -> Optional[Dict[str, Any]]:
        """Use Claude for complex mixed layouts"""
        try:
            # Convert page to image for Claude vision
            image_data = await self._page_to_image_bytes(section.pdf_path, section.page_num)
            
            if not image_data:
                return None
            
            # Use Claude OCR parser
            parser = self.parsers['claude_ocr']
            if hasattr(parser, 'claude_client') and parser.claude_client:
                models = await parser._process_catalog_page_with_claude(
                    image_data, catalog.brand, catalog.model_year, section.page_num
                )
                return models[0] if models else None
            else:
                logger.warning("Claude client not available for complex layout extraction")
                return None
        
        except Exception as e:
            logger.warning(f"Claude extraction failed: {e}")
            return None
    
    async def _extract_with_parsers(self, pdf_path: Path, catalog: Catalog) -> ParseResult:
        """Fallback extraction using parser-based approach"""
        logger.info("Using parser-based fallback for catalog extraction")
        
        # Try parsers in order of preference for catalogs
        parser_order = ['pymupdf', 'pdfplumber', 'camelot', 'claude_ocr']
        
        for parser_name in parser_order:
            try:
                parser = self.parsers[parser_name]
                result = await parser.parse_catalog(pdf_path, catalog.brand, catalog.model_year)
                
                if result.success and result.entries:
                    logger.info(f"Parser {parser_name} succeeded with {len(result.entries)} models")
                    return result
                
            except Exception as e:
                logger.warning(f"Parser {parser_name} failed: {e}")
                continue
        
        # Return empty result if all parsers failed
        return ParseResult(
            entries=[], confidence=Decimal("0.0"), method_used="all_parsers_failed",
            processing_time_ms=0, errors=["All catalog parsers failed"], metadata={}
        )
    
    async def _extract_specs_table(self, section: CatalogSection) -> Dict[str, Any]:
        """Extract specifications from table section"""
        # Implementation would depend on specific table structure
        return {}
    
    async def _extract_features(self, section: CatalogSection) -> List[str]:
        """Extract features from features list section"""
        # Implementation would depend on specific feature list format
        return []
    
    def _merge_specs_to_model(self, base_models: List[Dict[str, Any]], specs: Dict[str, Any]):
        """Merge specifications to existing models"""
        for model in base_models:
            if model.get('full_specifications'):
                model['full_specifications'].update(specs)
    
    def _merge_features_to_model(self, base_models: List[Dict[str, Any]], features: List[str]):
        """Merge features to existing models"""
        for model in base_models:
            if model.get('features'):
                model['features'].extend(features)
    
    async def _store_models(self, models: List[Dict[str, Any]], catalog_id: UUID) -> int:
        """Store models in database with enhanced error handling"""
        stored_count = 0
        
        for model_data in models:
            try:
                # Ensure catalog_id is set
                model_data['catalog_id'] = catalog_id
                
                # Validate required fields
                if not model_data.get('model_family') or not model_data.get('lookup_key'):
                    logger.warning(f"Skipping model with missing required fields: {model_data.get('model_family')}")
                    continue
                
                # Create BaseModel object
                base_model = BaseModel(
                    id=model_data.get('id', uuid4()),
                    catalog_id=model_data['catalog_id'],
                    lookup_key=model_data['lookup_key'],
                    brand=model_data['brand'],
                    model_family=model_data['model_family'],
                    model_year=model_data['model_year'],
                    engine_options=model_data.get('engine_options'),
                    track_options=model_data.get('track_options'),
                    suspension_options=model_data.get('suspension_options'),
                    starter_options=model_data.get('starter_options'),
                    dimensions=model_data.get('dimensions'),
                    features=model_data.get('features'),
                    full_specifications=model_data.get('full_specifications'),
                    marketing_description=model_data.get('marketing_description'),
                    source_pages=model_data.get('source_pages'),
                    extraction_confidence=model_data.get('extraction_confidence'),
                    completeness_score=model_data.get('completeness_score'),
                    created_at=datetime.now()
                )
                
                await self.db_repo.create_base_model(base_model)
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Failed to store model {model_data.get('model_family', 'unknown')}: {e}")
                continue
        
        logger.info(f"Stored {stored_count} models in database")
        return stored_count
    
    def _build_base_model(self, model_name: str, table: List[List[str]], features_text: str, catalog: Catalog) -> Dict[str, Any]:
        """Build base model from structured data"""
        try:
            # Clean model name
            if not model_name or not model_name.strip():
                return None
            
            model_family = model_name.strip()
            
            # Extract specifications from table
            specifications = {}
            if table:
                for row in table:
                    if len(row) >= 2:
                        key = row[0].strip().lower()
                        value = row[1].strip()
                        
                        if key and value:
                            if 'engine' in key:
                                if 'engine_options' not in specifications:
                                    specifications['engine_options'] = {}
                                specifications['engine_options'][key] = value
                            elif 'track' in key:
                                if 'track_options' not in specifications:
                                    specifications['track_options'] = {}
                                specifications['track_options'][key] = value
                            elif any(dim in key for dim in ['length', 'width', 'height', 'weight']):
                                if 'dimensions' not in specifications:
                                    specifications['dimensions'] = {}
                                specifications['dimensions'][key] = value
            
            # Extract features from text
            features = []
            if features_text:
                # Simple feature extraction - split by lines and clean
                lines = features_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 5 and not line.isupper():
                        features.append(line)
            
            specifications['features'] = features
            
            # Generate lookup key
            model_clean = model_family.replace(' ', '_')
            lookup_key = f"{catalog.brand}_{model_clean}_{catalog.model_year}"
            
            return {
                'id': uuid4(),
                'catalog_id': catalog.id,
                'lookup_key': lookup_key,
                'brand': catalog.brand,
                'model_family': model_family,
                'model_year': catalog.model_year,
                'engine_options': specifications.get('engine_options', {}),
                'track_options': specifications.get('track_options', {}),
                'suspension_options': specifications.get('suspension_options', {}),
                'starter_options': specifications.get('starter_options', {}),
                'dimensions': specifications.get('dimensions', {}),
                'features': features,
                'full_specifications': specifications,
                'marketing_description': None,
                'source_pages': [0],  # Would need actual page number
                'extraction_confidence': Decimal("0.80"),
                'completeness_score': self._calculate_completeness_score(specifications)
            }
        
        except Exception as e:
            logger.error(f"Failed to build base model from structured data: {e}")
            return None
    
    def _build_base_model_from_cv(self, extracted_data: Dict[str, str], catalog: Catalog) -> Optional[Dict[str, Any]]:
        """Build base model from computer vision extracted data"""
        try:
            # Extract model name from title region
            model_family = extracted_data.get('title', '').strip()
            
            if not model_family:
                # Try to find model name in other regions
                for key, text in extracted_data.items():
                    if any(keyword in text.lower() for keyword in ['re', 'rs', 'xt', 'sport']):
                        lines = text.split('\n')
                        for line in lines:
                            if any(keyword in line.lower() for keyword in ['re', 'rs', 'xt', 'sport']):
                                model_family = line.strip()
                                break
                        if model_family:
                            break
            
            if not model_family:
                return None
            
            # Extract specifications from text regions
            specifications = {}
            
            specs_text = extracted_data.get('specifications', '')
            if specs_text:
                # Simple specification extraction
                lines = specs_text.split('\n')
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if 'engine' in key:
                            if 'engine_options' not in specifications:
                                specifications['engine_options'] = {}
                            specifications['engine_options'][key] = value
                        elif 'track' in key:
                            if 'track_options' not in specifications:
                                specifications['track_options'] = {}
                            specifications['track_options'][key] = value
            
            # Extract features
            features_text = extracted_data.get('features', '')
            features = []
            if features_text:
                lines = features_text.split('\n')
                features = [line.strip() for line in lines if line.strip() and len(line.strip()) > 3]
            
            # Generate lookup key
            model_clean = model_family.replace(' ', '_')
            lookup_key = f"{catalog.brand}_{model_clean}_{catalog.model_year}"
            
            return {
                'id': uuid4(),
                'catalog_id': catalog.id,
                'lookup_key': lookup_key,
                'brand': catalog.brand,
                'model_family': model_family,
                'model_year': catalog.model_year,
                'engine_options': specifications.get('engine_options', {}),
                'track_options': specifications.get('track_options', {}),
                'suspension_options': specifications.get('suspension_options', {}),
                'starter_options': specifications.get('starter_options', {}),
                'dimensions': specifications.get('dimensions', {}),
                'features': features,
                'full_specifications': specifications,
                'marketing_description': None,
                'source_pages': [0],
                'extraction_confidence': Decimal("0.70"),  # Lower confidence for CV
                'completeness_score': self._calculate_completeness_score(specifications)
            }
        
        except Exception as e:
            logger.error(f"Failed to build base model from CV data: {e}")
            return None
    
    async def _page_to_image(self, pdf_path: Path, page_num: int):
        """Convert PDF page to image for computer vision"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            
            # Render page to image
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to numpy array for CV processing
            import numpy as np
            img_data = pix.samples
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            doc.close()
            return img
        
        except Exception as e:
            logger.error(f"Failed to convert page to image: {e}")
            return None
    
    async def _page_to_image_bytes(self, pdf_path: Path, page_num: int) -> Optional[bytes]:
        """Convert PDF page to image bytes for Claude"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            
            # Render page to image
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PNG bytes
            img_bytes = pix.pil_tobytes(format="PNG")
            
            doc.close()
            return img_bytes
        
        except Exception as e:
            logger.error(f"Failed to convert page to image bytes: {e}")
            return None
    
    def _preprocess_for_ocr(self, image):
        """Preprocess image for better OCR results"""
        try:
            import cv2
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Apply threshold to get binary image
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            
            # Denoise
            denoised = cv2.medianBlur(binary, 3)
            
            return denoised
        
        except ImportError:
            logger.warning("OpenCV not available for image preprocessing")
            return image
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image
    
    def _detect_text_regions(self, image):
        """Detect text regions in image"""
        # Simplified implementation - would need more sophisticated region detection
        from dataclasses import dataclass
        
        @dataclass
        class TextRegion:
            image: any
            type: str
            confidence: float
        
        # For now, return the whole image as a single region
        return [TextRegion(image=image, type='full_page', confidence=1.0)]
    
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