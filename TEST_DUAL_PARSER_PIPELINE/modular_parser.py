"""
Modular dual parser pipeline with testable functions and data classes
Replaces monolithic catalog_spec_parser.py with clean architecture
"""

import re
import fitz  # PyMuPDF
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from uuid import uuid4

from data_models import (
    CatalogVehicle, PriceListEntry, VehicleSpecifications, 
    MarketingContent, ProductImage, ColorOption, SpringOption,
    DualParserConfig, MatchingResult, ModelCodeMapping
)
from matching_engine import MatchingEngine, ModelCodeMappingService, TextNormalizer

class PDFDiscoveryService:
    """Service for discovering and managing PDF files"""
    
    def __init__(self, docs_folder: str = "docs"):
        self.docs_folder = Path(docs_folder)
        self.available_pdfs = {}
        self._discover_pdfs()
    
    def _discover_pdfs(self):
        """Discover all PDF files in docs folder"""
        if not self.docs_folder.exists():
            print(f"Warning: docs folder {self.docs_folder} does not exist")
            return
        
        pdf_files = list(self.docs_folder.glob("*.pdf"))
        
        for pdf_path in pdf_files:
            pdf_info = self._analyze_pdf_file(pdf_path)
            key = f"{pdf_info['brand']}_{pdf_info['year']}"
            
            if key not in self.available_pdfs:
                self.available_pdfs[key] = []
            self.available_pdfs[key].append(pdf_info)
        
        print(f"Discovered {len(pdf_files)} PDF files across {len(self.available_pdfs)} brand/year combinations")
    
    def _analyze_pdf_file(self, pdf_path: Path) -> Dict[str, Any]:
        """Analyze PDF file to extract metadata"""
        filename = pdf_path.name.upper()
        
        # Extract brand
        brand = "UNKNOWN"
        if "SKIDOO" in filename or "SKI-DOO" in filename:
            brand = "SKI-DOO"
        elif "LYNX" in filename:
            brand = "LYNX"
        elif "SEA-DOO" in filename:
            brand = "SEA-DOO"
        
        # Extract year
        year = 0
        year_match = re.search(r'(20\d{2})', filename)
        if year_match:
            year = int(year_match.group(1))
        
        # Determine document type
        doc_type = "UNKNOWN"
        if "PRODUCT SPEC" in filename or "SPEC BOOK" in filename:
            doc_type = "PRODUCT_SPEC"
        elif "PRICE" in filename or "HINNASTO" in filename:
            doc_type = "PRICE_LIST"
        elif "ACCESSORY" in filename:
            doc_type = "ACCESSORY_CATALOG"
        
        return {
            'path': pdf_path,
            'filename': pdf_path.name,
            'brand': brand,
            'year': year,
            'document_type': doc_type,
            'file_size': pdf_path.stat().st_size,
            'discovered_at': datetime.now()
        }
    
    def get_catalog_pdf(self, brand: str, year: int, doc_type: str = "PRODUCT_SPEC") -> Optional[Path]:
        """Find specific PDF by brand, year, and document type"""
        key = f"{brand}_{year}"
        
        if key in self.available_pdfs:
            for pdf_info in self.available_pdfs[key]:
                if pdf_info['document_type'] == doc_type:
                    return pdf_info['path']
        
        return None
    
    def list_available_pdfs(self):
        """Display all discovered PDFs"""
        print("\\n=== AVAILABLE PDF FILES ===")
        
        for key, pdfs in self.available_pdfs.items():
            print(f"\\n{key}:")
            for pdf_info in pdfs:
                size_mb = pdf_info['file_size'] / (1024 * 1024)
                print(f"  - {pdf_info['filename']} ({pdf_info['document_type']}, {size_mb:.1f}MB)")

class CatalogExtractor:
    """Service for extracting data from catalog PDFs"""
    
    def __init__(self, config: DualParserConfig):
        self.config = config
        self.normalizer = TextNormalizer()
    
    def extract_vehicles_from_pdf(self, pdf_path: Path) -> List[CatalogVehicle]:
        """Extract all vehicles from a catalog PDF"""
        vehicles = []
        
        with fitz.open(pdf_path) as pdf:
            for page_num in range(pdf.page_count):
                page = pdf[page_num]
                text = page.get_text()
                
                if not text:
                    continue
                
                # Check if this page contains vehicle information
                if self._is_vehicle_page(text):
                    vehicle = self._extract_vehicle_from_page(text, page_num + 1, pdf_path.name)
                    if vehicle:
                        vehicles.append(vehicle)
        
        return vehicles
    
    def _is_vehicle_page(self, text: str) -> bool:
        """Determine if page contains vehicle specification information"""
        model_families = ['SUMMIT', 'MXZ', 'RENEGADE', 'EXPEDITION', 'FREERIDE', 'BACKCOUNTRY', 'SKANDIC', 'TUNDRA']
        
        # Must contain a model family name
        has_model = any(model in text.upper() for model in model_families)
        
        # Must contain technical specifications
        has_specs = any(keyword in text.upper() for keyword in [
            'ENGINE', 'TRACK', 'SUSPENSION', 'E-TEC', 'ACE', 'ROTAX'
        ])
        
        # Avoid intro/cover pages
        avoid_keywords = ['TABLE OF CONTENTS', 'SPECIFICATIONS OVERVIEW', '2026 PRODUCT SPEC BOOK']
        is_intro = any(keyword in text.upper() for keyword in avoid_keywords)
        
        return has_model and has_specs and not is_intro
    
    def _extract_vehicle_from_page(self, text: str, page_number: int, source_catalog: str) -> Optional[CatalogVehicle]:
        """Extract vehicle information from a single page"""
        try:
            vehicle = CatalogVehicle()
            vehicle.page_number = page_number
            vehicle.source_catalog_name = source_catalog
            vehicle.extraction_timestamp = datetime.now()
            
            # Extract vehicle name and model family
            vehicle.name, vehicle.model_family = self._extract_model_info(text)
            vehicle.base_model_name = self._extract_base_model_name(vehicle.name)
            vehicle.package_name = self._extract_package_name(vehicle.name)
            
            # Extract specifications
            vehicle.specifications = self._extract_specifications(text)
            
            # Extract marketing content
            vehicle.marketing = self._extract_marketing_content(text)
            
            # Extract colors and spring options
            vehicle.available_colors = self._extract_colors(text)
            vehicle.spring_options = self._extract_spring_options(text)
            
            return vehicle
            
        except Exception as e:
            print(f"Error extracting vehicle from page {page_number}: {e}")
            return None
    
    def _extract_model_info(self, text: str) -> Tuple[str, str]:
        """Extract vehicle name and model family from text"""
        lines = [line.strip() for line in text.split('\\n') if line.strip()]
        
        # Look for model name in first few lines
        for line in lines[:10]:
            line_upper = line.upper()
            
            # Skip headers and page numbers
            if any(skip in line_upper for skip in ['2026', 'VEHICLE SPECIFICATIONS', 'PAGE']):
                continue
            
            # Check for model family keywords
            model_families = ['SUMMIT', 'MXZ', 'RENEGADE', 'EXPEDITION', 'FREERIDE', 'BACKCOUNTRY', 'SKANDIC', 'TUNDRA']
            for family in model_families:
                if family in line_upper:
                    # Clean up the line to get the full vehicle name
                    vehicle_name = re.sub(r'[^A-Za-z0-9\\s\\-]', ' ', line)
                    vehicle_name = ' '.join(vehicle_name.split())
                    return vehicle_name, family
        
        return "Unknown Vehicle", "Unknown"
    
    def _extract_base_model_name(self, full_name: str) -> str:
        """Extract base model name without package suffixes"""
        # Remove common package indicators
        base_name = re.sub(r'\\b(WITH|EXPERT|COMPETITION|PACKAGE)\\b', '', full_name, flags=re.IGNORECASE)
        base_name = re.sub(r'\\s+', ' ', base_name).strip()
        return base_name
    
    def _extract_package_name(self, full_name: str) -> Optional[str]:
        """Extract package name from full vehicle name"""
        package_patterns = [
            r'WITH\\s+(\\w+\\s+PACKAGE)',
            r'\\b(EXPERT|COMPETITION|ADRENALINE|XTREME|SPORT)\\b'
        ]
        
        for pattern in package_patterns:
            match = re.search(pattern, full_name, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_specifications(self, text: str) -> VehicleSpecifications:
        """Extract technical specifications from text"""
        specs = VehicleSpecifications()
        
        # Extract engine information
        engine_match = re.search(r'(\d{3,4})\s*([R]?)\s*(E-TEC|ACE)\s*(TURBO\s*R?)?', text, re.IGNORECASE)
        if engine_match:
            displacement = engine_match.group(1)
            r_variant = engine_match.group(2)
            engine_type = engine_match.group(3)
            turbo = engine_match.group(4) or ""
            
            specs.engine = f"{displacement}{r_variant} {engine_type} {turbo}".strip()
            specs.displacement_cc = int(displacement)
            specs.engine_family = engine_type.upper()
        
        # Extract track information
        track_match = re.search(r'(\d{2,3})\s*["\']?\s*(?:in)?\s*x\s*(\d{3,4})\s*mm', text, re.IGNORECASE)
        if track_match:
            specs.track_length_in = int(track_match.group(1))
            specs.track_length_mm = int(track_match.group(2))
        
        # Extract display information
        display_match = re.search(r'(\d+\.?\d*)\s*(?:in\.?|inch)\s+.*(?:display|screen)', text, re.IGNORECASE)
        if display_match:
            specs.display_size = f"{display_match.group(1)} in."
        
        # Extract starter system
        if re.search(r'electric\s+start', text, re.IGNORECASE):
            specs.starter_system = "Electric"
        elif re.search(r'manual\s+start', text, re.IGNORECASE):
            specs.starter_system = "Manual"
        
        return specs
    
    def _extract_marketing_content(self, text: str) -> MarketingContent:
        """Extract marketing and promotional content"""
        marketing = MarketingContent()
        
        # Extract tagline (usually near the top)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for i, line in enumerate(lines[:15]):  # Check first 15 lines
            if len(line) > 30 and '.' in line and not any(skip in line.upper() for skip in ['ENGINE', 'TRACK', 'SUSPENSION']):
                # This might be a marketing tagline
                marketing.tagline = line
                break
        
        # Extract bullet points as key benefits
        bullet_points = re.findall(r'•\s*([^\n•]+)', text)
        marketing.key_benefits = [point.strip() for point in bullet_points if len(point.strip()) > 10]
        
        # Extract package highlights
        package_section = re.search(r'PACKAGE\s+HIGHLIGHTS?([^\n]*(?:\n[^\n]*)*?)(?:\n\s*\n|$)', text, re.IGNORECASE)
        if package_section:
            highlights_text = package_section.group(1)
            highlights = re.findall(r'•\s*([^\n•]+)', highlights_text)
            marketing.package_highlights = [h.strip() for h in highlights]
        
        return marketing
    
    def _extract_colors(self, text: str) -> List[ColorOption]:
        """Extract color options from text"""
        colors = []
        
        # Common color patterns
        color_patterns = [
            r'(TERRA\s+GREEN)', r'(SCANDI\s+BLUE)', r'(MONUMENT\s+GREY)',
            r'(WHITE)', r'(BLACK)', r'(RED)', r'(BLUE)', r'(GREEN)'
        ]
        
        for pattern in color_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                color_name = match.group(1).title()
                
                # Check if it's already in the list
                if not any(c.name == color_name for c in colors):
                    color = ColorOption(name=color_name)
                    
                    # Check for spring-only restrictions
                    context = text[max(0, match.start()-100):match.end()+100]
                    if 'spring' in context.lower():
                        color.spring_only = True
                    
                    colors.append(color)
        
        return colors
    
    def _extract_spring_options(self, text: str) -> List[SpringOption]:
        """Extract spring option information"""
        spring_options = []
        
        # Look for spring options section
        spring_section = re.search(r'SPRING\s+OPTIONS?([^\n]*(?:\n[^\n]*)*?)(?:\n\s*\n|$)', text, re.IGNORECASE)
        if not spring_section:
            return spring_options
        
        spring_text = spring_section.group(1)
        
        # Extract individual spring options
        option_lines = re.findall(r'•\s*([^\n•]+)', spring_text)
        
        for line in option_lines:
            option = SpringOption()
            option.description = line.strip()
            
            # Extract color if mentioned
            color_match = re.search(r'(\w+\s+\w*)\s+color', line, re.IGNORECASE)
            if color_match:
                option.color_name = color_match.group(1).title()
            
            # Extract engine restriction
            engine_match = re.search(r'(\d{3,4}\s*[R]?\s*E-TEC[^\)]*)', line, re.IGNORECASE)
            if engine_match:
                option.engine_restriction = engine_match.group(1).strip()
            
            # Extract track length
            track_match = re.search(r'(\d{2,3})\s*["\']?\s*track', line, re.IGNORECASE)
            if track_match:
                option.track_length = f"{track_match.group(1)}\""
            
            spring_options.append(option)
        
        return spring_options

class PriceListService:
    """Service for managing price list data"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.normalizer = TextNormalizer()
    
    def load_all_price_entries(self) -> List[PriceListEntry]:
        """Load all price list entries from database"""
        entries = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, model_code, malli, paketti, moottori, telamatto,
                       kaynnistin, mittaristo, kevatoptiot, vari, price, currency,
                       normalized_model_name, normalized_package_name, normalized_engine_spec
                FROM price_entries
            """)
            
            for row in cursor.fetchall():
                entry = PriceListEntry(
                    id=row[0], model_code=row[1], malli=row[2], paketti=row[3],
                    moottori=row[4], telamatto=row[5], kaynnistin=row[6],
                    mittaristo=row[7], kevatoptiot=row[8], vari=row[9],
                    price=row[10], currency=row[11] or "EUR",
                    normalized_model_name=row[12], normalized_package_name=row[13],
                    normalized_engine_spec=row[14]
                )
                entries.append(entry)
            
            return entries
            
        except Exception as e:
            print(f"Error loading price entries: {e}")
            return []
        finally:
            conn.close()
    
    def normalize_and_update_entries(self, entries: List[PriceListEntry]) -> bool:
        """Normalize price list entries and update database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for entry in entries:
                # Normalize fields if not already done
                if not entry.normalized_model_name:
                    entry.normalized_model_name = self.normalizer.normalize_model_name(entry.malli or "")
                if not entry.normalized_package_name:
                    entry.normalized_package_name = self.normalizer.normalize_package_name(entry.paketti or "")
                if not entry.normalized_engine_spec:
                    entry.normalized_engine_spec = self.normalizer.normalize_engine_spec(entry.moottori or "")
                
                # Update database
                cursor.execute("""
                    UPDATE price_entries 
                    SET normalized_model_name = ?, normalized_package_name = ?, normalized_engine_spec = ?
                    WHERE id = ?
                """, (entry.normalized_model_name, entry.normalized_package_name, 
                      entry.normalized_engine_spec, entry.id))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error normalizing price entries: {e}")
            return False
        finally:
            conn.close()

class ModularDualParser:
    """Main orchestrator class for the dual parser pipeline"""
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db", docs_folder: str = "docs"):
        self.db_path = db_path
        
        # Load configuration
        self.config = DualParserConfig.from_database(db_path)
        
        # Initialize services
        self.pdf_discovery = PDFDiscoveryService(docs_folder)
        self.catalog_extractor = CatalogExtractor(self.config)
        self.price_list_service = PriceListService(db_path)
        self.matching_engine = MatchingEngine(self.config)
        self.mapping_service = ModelCodeMappingService(db_path)
    
    def run_complete_pipeline(self, brand: str = "SKI-DOO", year: int = 2026) -> Dict[str, Any]:
        """Run the complete dual parser pipeline"""
        print(f"=== MODULAR DUAL PARSER PIPELINE ===")
        print(f"Processing {brand} {year} catalog and price list")
        
        results = {
            'catalog_vehicles': [],
            'price_entries': [],
            'successful_matches': [],
            'failed_matches': [],
            'processing_statistics': {}
        }
        
        start_time = datetime.now()
        
        try:
            # Step 1: Extract catalog vehicles
            catalog_pdf = self.pdf_discovery.get_catalog_pdf(brand, year, "PRODUCT_SPEC")
            if not catalog_pdf:
                raise FileNotFoundError(f"No catalog PDF found for {brand} {year}")
            
            print(f"Extracting vehicles from: {catalog_pdf.name}")
            catalog_vehicles = self.catalog_extractor.extract_vehicles_from_pdf(catalog_pdf)
            results['catalog_vehicles'] = catalog_vehicles
            print(f"Extracted {len(catalog_vehicles)} catalog vehicles")
            
            # Step 2: Load and normalize price entries
            print("Loading price list entries...")
            price_entries = self.price_list_service.load_all_price_entries()
            results['price_entries'] = price_entries
            print(f"Loaded {len(price_entries)} price entries")
            
            # Normalize price entries
            self.price_list_service.normalize_and_update_entries(price_entries)
            
            # Step 3: Match price entries to catalog vehicles
            print("Matching price entries to catalog vehicles...")
            
            for entry in price_entries:
                matched_vehicle, matching_result = self.matching_engine.match_price_to_catalog(
                    entry, catalog_vehicles
                )
                
                if matched_vehicle:
                    # Create mapping
                    mapping = self.mapping_service.create_mapping(entry, matched_vehicle, matching_result)
                    self.mapping_service.save_mapping(mapping)
                    
                    results['successful_matches'].append({
                        'price_entry': entry,
                        'catalog_vehicle': matched_vehicle,
                        'matching_result': matching_result,
                        'mapping': mapping
                    })
                else:
                    results['failed_matches'].append({
                        'price_entry': entry,
                        'matching_result': matching_result
                    })
            
            # Step 4: Generate statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            results['processing_statistics'] = {
                'total_processing_time_seconds': processing_time,
                'catalog_vehicles_extracted': len(catalog_vehicles),
                'price_entries_processed': len(price_entries),
                'successful_matches': len(results['successful_matches']),
                'failed_matches': len(results['failed_matches']),
                'match_success_rate': len(results['successful_matches']) / len(price_entries) if price_entries else 0,
                'extraction_timestamp': datetime.now()
            }
            
            print(f"\\n=== PIPELINE COMPLETED ===")
            print(f"Processing time: {processing_time:.2f} seconds")
            print(f"Match success rate: {results['processing_statistics']['match_success_rate']:.1%}")
            
            return results
            
        except Exception as e:
            print(f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return results
    
    def list_available_pdfs(self):
        """List all available PDF files"""
        self.pdf_discovery.list_available_pdfs()