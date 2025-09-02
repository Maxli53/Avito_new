import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from ..models.domain import PriceEntry, PriceList, ExtractionResult, ProcessingStatus
from ..repositories.database import DatabaseRepository
from .parsers import (
    PyMuPDFParser, CamelotParser, PDFPlumberParser, ClaudeOCRParser,
    PDFQuality, ParseResult
)


logger = logging.getLogger(__name__)


class PriceListExtractor:
    """Sophisticated price list extraction with fallback strategies"""
    
    def __init__(self, db_repo: DatabaseRepository):
        self.db_repo = db_repo
        self.parsers = {
            'pymupdf': PyMuPDFParser(),      # Fast, good for digital PDFs
            'camelot': CamelotParser(),      # Excellent for complex tables
            'pdfplumber': PDFPlumberParser(), # Good for structured data
            'claude_ocr': ClaudeOCRParser()  # Fallback for scanned/poor quality
        }
        
    async def extract_from_pdf(self, pdf_path: Path, price_list_id: UUID) -> ExtractionResult:
        """
        Sophisticated extraction with quality detection and parser selection
        
        Args:
            pdf_path: Path to the price list PDF
            price_list_id: UUID of the price list record
            
        Returns:
            ExtractionResult with extraction statistics
        """
        start_time = datetime.now()
        logger.info(f"Starting sophisticated price extraction from {pdf_path}")
        
        try:
            # Get price list metadata
            price_list = await self.db_repo.get_price_list(price_list_id)
            if not price_list:
                raise ValueError(f"Price list {price_list_id} not found")
            
            # Step 1: Analyze PDF quality
            pdf_quality = await self._analyze_pdf_quality(pdf_path)
            logger.info(f"PDF quality analysis: {pdf_quality.extraction_difficulty} difficulty, "
                       f"text score: {pdf_quality.text_quality_score:.2f}")
            
            # Step 2: Try parsers in order of efficiency
            result = None
            
            if pdf_quality.is_digital and pdf_quality.has_clear_tables:
                # Try fast digital parser first
                logger.info("Trying PyMuPDF parser for digital PDF with clear tables")
                result = await self._try_pymupdf(pdf_path, price_list.market, price_list.brand, price_list.model_year)
                if result.confidence > Decimal("0.9"):
                    logger.info(f"PyMuPDF succeeded with confidence {result.confidence}")
                else:
                    result = None
            
            if not result and pdf_quality.has_complex_tables:
                # Try Camelot for complex table structures
                logger.info("Trying Camelot parser for complex tables")
                result = await self._try_camelot(pdf_path, price_list.market, price_list.brand, price_list.model_year)
                if result.confidence > Decimal("0.85"):
                    logger.info(f"Camelot succeeded with confidence {result.confidence}")
                else:
                    result = None
            
            if not result and pdf_quality.text_quality_score > 0.6:
                # Try PDFPlumber for structured text
                logger.info("Trying PDFPlumber parser for structured text")
                result = await self._try_pdfplumber(pdf_path, price_list.market, price_list.brand, price_list.model_year)
                if result.confidence > Decimal("0.8"):
                    logger.info(f"PDFPlumber succeeded with confidence {result.confidence}")
                else:
                    result = None
            
            if not result and (pdf_quality.is_scanned or pdf_quality.has_images):
                # Use Claude OCR for difficult PDFs
                logger.info("Trying Claude OCR parser for scanned/difficult PDF")
                result = await self._try_claude_ocr(pdf_path, price_list.market, price_list.brand, price_list.model_year)
            
            # Step 3: Merge results from multiple parsers if needed
            if not result or result.confidence < Decimal("0.7"):
                logger.info("Single parser confidence low, attempting merge strategy")
                result = await self._merge_parser_results(pdf_path, price_list.market, price_list.brand, price_list.model_year)
            
            # Process results
            if not result or not result.entries:
                raise ValueError("No valid entries extracted from PDF")
            
            # Store entries in database
            stored_count = await self._store_entries(result.entries, price_list_id)
            
            # Update price list statistics
            await self.db_repo.update_price_list_stats(
                price_list_id,
                total_entries=len(result.entries),
                processed_entries=stored_count,
                status=ProcessingStatus.COMPLETED
            )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            logger.info(f"Sophisticated extraction completed: {stored_count} entries in {processing_time}ms "
                       f"using {result.method_used} with confidence {result.confidence}")
            
            return ExtractionResult(
                success=True,
                entries_extracted=stored_count,
                entries_failed=len(result.entries) - stored_count,
                confidence_score=result.confidence,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Sophisticated price extraction failed: {str(e)}")
            
            await self.db_repo.update_price_list_stats(
                price_list_id,
                status=ProcessingStatus.FAILED
            )
            
            return ExtractionResult(
                success=False,
                entries_extracted=0,
                entries_failed=0,
                error_message=str(e)
            )
    
    async def _analyze_pdf_quality(self, pdf_path: Path) -> PDFQuality:
        """Analyze PDF quality to determine best extraction approach"""
        quality = PDFQuality()
        
        try:
            import fitz
            
            doc = fitz.open(pdf_path)
            
            # Analyze first few pages
            sample_pages = min(3, len(doc))
            total_text_length = 0
            total_tables = 0
            total_images = 0
            has_embedded_fonts = False
            
            for page_num in range(sample_pages):
                page = doc[page_num]
                
                # Check for tables
                tables = page.find_tables()
                total_tables += len(tables)
                
                # Analyze table complexity
                for table in tables:
                    table_data = table.extract()
                    if table_data and len(table_data) > 5 and len(table_data[0]) > 8:
                        quality.has_complex_tables = True
                    elif table_data and len(table_data) > 2:
                        quality.has_clear_tables = True
                
                # Check text content
                text = page.get_text()
                total_text_length += len(text)
                
                # Check for images
                image_list = page.get_images()
                total_images += len(image_list)
                
                # Check if PDF is digital (has fonts) vs scanned
                try:
                    font_list = page.get_fonts()
                    if font_list:
                        has_embedded_fonts = True
                except:
                    pass
            
            # Set quality attributes
            quality.is_digital = has_embedded_fonts
            quality.is_scanned = not has_embedded_fonts
            quality.table_count = total_tables
            quality.has_images = total_images > 0
            quality.text_quality_score = min(1.0, total_text_length / (sample_pages * 2000))  # Normalized
            
            doc.close()
            
            logger.info(f"PDF Quality Analysis: digital={quality.is_digital}, "
                       f"tables={quality.table_count}, text_score={quality.text_quality_score:.2f}")
            
        except Exception as e:
            logger.warning(f"Could not analyze PDF quality: {e}")
            # Default to conservative settings
            quality.is_digital = True
            quality.text_quality_score = 0.5
        
        return quality
    
    async def _try_pymupdf(self, pdf_path: Path, market: str, brand: str, year: int) -> ParseResult:
        """Try PyMuPDF parser"""
        parser = self.parsers['pymupdf']
        if await parser.can_parse(pdf_path, PDFQuality(is_digital=True, has_clear_tables=True)):
            return await parser.parse_price_list(pdf_path, market, brand, year)
        else:
            return ParseResult(
                entries=[], confidence=Decimal("0.0"), method_used="pymupdf_skipped",
                processing_time_ms=0, errors=["PDF not suitable for PyMuPDF"], metadata={}
            )
    
    async def _try_camelot(self, pdf_path: Path, market: str, brand: str, year: int) -> ParseResult:
        """Try Camelot parser"""
        parser = self.parsers['camelot']
        quality = PDFQuality(has_complex_tables=True)
        if await parser.can_parse(pdf_path, quality):
            return await parser.parse_price_list(pdf_path, market, brand, year)
        else:
            return ParseResult(
                entries=[], confidence=Decimal("0.0"), method_used="camelot_skipped",
                processing_time_ms=0, errors=["PDF not suitable for Camelot"], metadata={}
            )
    
    async def _try_pdfplumber(self, pdf_path: Path, market: str, brand: str, year: int) -> ParseResult:
        """Try PDFPlumber parser"""
        parser = self.parsers['pdfplumber']
        quality = PDFQuality(is_digital=True, text_quality_score=0.7)
        if await parser.can_parse(pdf_path, quality):
            return await parser.parse_price_list(pdf_path, market, brand, year)
        else:
            return ParseResult(
                entries=[], confidence=Decimal("0.0"), method_used="pdfplumber_skipped",
                processing_time_ms=0, errors=["PDF not suitable for PDFPlumber"], metadata={}
            )
    
    async def _try_claude_ocr(self, pdf_path: Path, market: str, brand: str, year: int) -> ParseResult:
        """Try Claude OCR parser"""
        parser = self.parsers['claude_ocr']
        quality = PDFQuality(is_scanned=True, has_images=True)
        if await parser.can_parse(pdf_path, quality):
            return await parser.parse_price_list(pdf_path, market, brand, year)
        else:
            return ParseResult(
                entries=[], confidence=Decimal("0.0"), method_used="claude_ocr_unavailable",
                processing_time_ms=0, errors=["Claude OCR not available"], metadata={}
            )
    
    async def _merge_parser_results(self, pdf_path: Path, market: str, brand: str, year: int) -> ParseResult:
        """Merge results from multiple parsers for better coverage"""
        logger.info("Attempting to merge results from multiple parsers")
        
        all_entries = []
        all_errors = []
        methods_used = []
        total_processing_time = 0
        
        # Try each parser and collect results
        for parser_name, parser in self.parsers.items():
            try:
                logger.info(f"Trying {parser_name} for merge strategy")
                result = await parser.parse_price_list(pdf_path, market, brand, year)
                
                if result.entries:
                    all_entries.extend(result.entries)
                    methods_used.append(result.method_used)
                    total_processing_time += result.processing_time_ms
                    logger.info(f"{parser_name} contributed {len(result.entries)} entries")
                
                all_errors.extend(result.errors)
                
                # Add delay between parsers
                await asyncio.sleep(0.5)
                
            except Exception as e:
                error_msg = f"{parser_name} failed in merge: {e}"
                all_errors.append(error_msg)
                logger.warning(error_msg)
        
        # Deduplicate entries by model_code
        unique_entries = {}
        for entry in all_entries:
            model_code = entry.get('model_code')
            if model_code and model_code not in unique_entries:
                unique_entries[model_code] = entry
        
        final_entries = list(unique_entries.values())
        
        # Calculate merged confidence
        confidence = Decimal("0.6") if final_entries else Decimal("0.0")
        if len(final_entries) > 10:
            confidence = Decimal("0.8")
        
        return ParseResult(
            entries=final_entries,
            confidence=confidence,
            method_used=f"merged_({'+'.join(methods_used)})",
            processing_time_ms=total_processing_time,
            errors=all_errors,
            metadata={
                'parsers_tried': len(self.parsers),
                'successful_parsers': len(methods_used),
                'total_raw_entries': len(all_entries),
                'deduplicated_entries': len(final_entries)
            }
        )
    
    # Removed obsolete field mapping method - now handled by individual parsers
    
    # Removed obsolete row extraction method - now handled by individual parsers
    
    # Removed obsolete regex extraction method - now handled by individual parsers
    
    # Removed obsolete safe field getter - now handled by individual parsers
    
    # Removed obsolete price parser - now handled by individual parsers
    
    # Removed obsolete validation method - validation now handled by individual parsers
    
    async def _store_entries(self, entries: List[Dict[str, Any]], price_list_id: UUID) -> int:
        """Store entries in database with enhanced validation"""
        stored_count = 0
        
        for entry_data in entries:
            try:
                # Ensure price_list_id is set
                entry_data['price_list_id'] = price_list_id
                
                # Validate required fields
                if not entry_data.get('model_code') or not entry_data.get('price'):
                    logger.warning(f"Skipping entry with missing required fields: {entry_data.get('model_code')}")
                    continue
                
                # Create PriceEntry object
                entry = PriceEntry(
                    id=entry_data.get('id', uuid4()),
                    price_list_id=entry_data['price_list_id'],
                    model_code=entry_data['model_code'],
                    malli=entry_data.get('malli'),
                    paketti=entry_data.get('paketti'),
                    moottori=entry_data.get('moottori'),
                    telamatto=entry_data.get('telamatto'),
                    kaynnistin=entry_data.get('kaynnistin'),
                    mittaristo=entry_data.get('mittaristo'),
                    kevatoptiot=entry_data.get('kevatoptiot'),
                    vari=entry_data.get('vari'),
                    price=entry_data['price'],
                    currency=entry_data.get('currency', 'EUR'),
                    market=entry_data['market'],
                    brand=entry_data['brand'],
                    model_year=entry_data['model_year'],
                    catalog_lookup_key=entry_data['catalog_lookup_key'],
                    status=ProcessingStatus.EXTRACTED,
                    created_at=datetime.now()
                )
                
                await self.db_repo.create_price_entry(entry)
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Failed to store entry {entry_data.get('model_code', 'unknown')}: {e}")
                continue
        
        logger.info(f"Stored {stored_count} entries in database")
        return stored_count