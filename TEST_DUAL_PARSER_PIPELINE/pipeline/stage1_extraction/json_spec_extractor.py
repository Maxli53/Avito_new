#!/usr/bin/env python3
"""
Professional JSON-First Spec Book Extractor
Extracts structured specifications directly into JSON format for target schema
"""

import pdfplumber
import re
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JsonSpecExtractor:
    """Professional JSON-first extractor for spec book data"""
    
    def __init__(self, db_path: str = "dual_db.db"):
        self.db_path = db_path
    
    def normalize_engine_name(self, engine_name: str) -> str:
        """
        Comprehensive engine name normalization to prevent all types of duplicates
        Handles: case variations, symbols, spacing, abbreviations, punctuation
        """
        if not engine_name:
            return ""
        
        # Convert to uppercase
        normalized = engine_name.upper()
        
        # Remove all trademark symbols and special characters
        normalized = re.sub(r'[®™℠©•�]', '', normalized)
        
        # Standardize common variations and abbreviations  
        replacements = {
            # Turbo variations
            r'\bTURBO\s*R\b': 'TURBOR',
            r'\bTURBO\s*CHARGED\b': 'TURBO',
            r'\bTURBOCHARGED\b': 'TURBO',
            
            # E-TEC variations
            r'\bE-TEC\b': 'ETEC',
            r'\bETEC\b': 'ETEC',
            r'\bE\s*TEC\b': 'ETEC',
            
            # ACE variations  
            r'\bACE\b': 'ACE',
            r'\bA\.C\.E\.\b': 'ACE',
            
            # EFI variations
            r'\bEFI\b': 'EFI',
            r'\bE\.F\.I\.\b': 'EFI',
            r'\bFUEL\s*INJECTION\b': 'EFI',
            
            # Remove common filler words
            r'\bWITH\b': '',
            r'\bAND\b': '',
            r'\bOR\b': '',
            r'\bTHE\b': '',
            
            # Standardize separators
            r'[-–—_/\\]': '',  # Remove dashes, slashes, underscores
            r'[.:]': '',       # Remove periods and colons
        }
        
        # Apply all replacements
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        # Remove all remaining non-alphanumeric characters except spaces
        normalized = re.sub(r'[^A-Z0-9\s]', '', normalized)
        
        # Normalize whitespace - collapse multiple spaces to single space
        normalized = re.sub(r'\s+', ' ', normalized.strip())
        
        # Remove extra spaces around numbers and letters
        normalized = re.sub(r'\s*(\d+)\s*', r'\1', normalized)
        
        return normalized
    
    def deduplicate_list(self, items: List[str], normalizer_func=None) -> List[str]:
        """
        Generic deduplication function for any list of items
        Uses custom normalizer function or default string normalization
        """
        if not items:
            return []
        
        seen = set()
        result = []
        
        for item in items:
            if normalizer_func:
                normalized = normalizer_func(item)
            else:
                # Default normalization: uppercase, no extra spaces, no special chars
                normalized = re.sub(r'[^A-Z0-9\s]', '', str(item).upper().strip())
                normalized = re.sub(r'\s+', ' ', normalized)
            
            if normalized not in seen:
                seen.add(normalized)
                result.append(item)
        
        return result
        
    def extract_model_info(self, page_text: str) -> Dict[str, Any]:
        """Extract basic model information from page"""
        lines = page_text.split('\n')
        
        # Normalize text to handle spaced headers like "S U M M I T � X �"
        # Remove all non-alphanumeric characters to collapse spaced letters
        normalized_text = re.sub(r'[^A-Z0-9]+', '', page_text.upper())
        
        # Model name patterns - work with normalized text (alphanumeric only)
        # SKIDOO Models
        skidoo_patterns = [
            (r'SUMMITXWITHEXPERTPACKAGE', 'Summit X', 'Expert Package', 'deep-snow'),
            (r'SUMMITX(?!.*EXPERT)', 'Summit X', 'Base', 'deep-snow'),
            (r'SUMMITADRENALINE', 'Summit Adrenaline', 'Base', 'deep-snow'),
            (r'SUMMITNEO', 'Summit Neo', 'Base', 'deep-snow'),
            (r'FREERIDE', 'Freeride', 'Base', 'deep-snow'),
            (r'BACKCOUNTRYXRS', 'Backcountry X-RS', 'Base', 'crossover'),
            (r'BACKCOUNTRYADRENALINE', 'Backcountry Adrenaline', 'Base', 'crossover'),
            (r'BACKCOUNTRYSPORT', 'Backcountry Sport', 'Base', 'crossover'),
            (r'MXZXRSWITHCOMPETITIONPACKAGE', 'MXZ X-RS', 'Competition Package', 'trail'),
            (r'MXZXRS(?!.*COMPETITION)', 'MXZ X-RS', 'Base', 'trail'),
            (r'MXZSPORT', 'MXZ Sport', 'Base', 'trail'),
            (r'MXZNEO', 'MXZ Neo+', 'Base', 'trail'),
            (r'RENEGADEXRS', 'Renegade X-RS', 'Base', 'trail'),
            (r'RENEGADEADRENALINE', 'Renegade Adrenaline', 'Base', 'trail'),
            (r'RENEGADESPORT', 'Renegade Sport', 'Base', 'trail'),
            (r'EXPEDITIONXTREME', 'Expedition Xtreme', 'Base', 'utility'),
            (r'EXPEDITIONSE', 'Expedition SE', 'Base', 'utility'),
            (r'EXPEDITIONLE', 'Expedition LE', 'Base', 'utility'),
            (r'EXPEDITIONSPORT', 'Expedition Sport', 'Base', 'utility'),
            (r'GRANDTOURINGSPORT', 'Grand Touring Sport', 'Base', 'touring'),
            (r'TUNDRАЛЕ', 'Tundra LE', 'Base', 'utility'),
            (r'SKANDICLE', 'Skandic LE', 'Base', 'utility'),
            (r'SKANDICSPORT', 'Skandic Sport', 'Base', 'utility'),
        ]
        
        # LYNX Models
        lynx_patterns = [
            (r'RAVEREWITHENDUROPACKAGE', 'Rave RE', 'Enduro Package', 'trail'),
            (r'RAVERE(?!.*ENDURO)', 'Rave RE', 'Base', 'trail'),
            (r'RAVEGLS', 'Rave GLS', 'Base', 'trail'),
            (r'ADVENTURELIMITED', 'Adventure Limited', 'Base', 'touring'),
            (r'ADVENTURELX', 'Adventure LX', 'Base', 'touring'),
            (r'ADVENTUREELECTRIC', 'Adventure Electric', 'Base', 'utility'),
            (r'ADVENTURECORE', 'Adventure Core', 'Base', 'touring'),
            (r'ADVENTURE(?!.*LIMITED|.*LX|.*ELECTRIC|.*CORE)', 'Adventure', 'Base', 'touring'),
        ]
        
        model_patterns = skidoo_patterns + lynx_patterns
        
        for pattern, model_name, configuration, category in model_patterns:
            if re.search(pattern, normalized_text):
                return {
                    'model': model_name,
                    'configuration': configuration,
                    'category': category,
                    'found_in_line': f'Matched {pattern} in normalized text'
                }
        
        return {'model': 'Unknown Model', 'configuration': 'Base', 'category': 'general', 'found_in_line': ''}
    
    def extract_engine_specifications(self, page_text: str) -> Dict[str, Any]:
        """Extract engine specifications from page text"""
        engine_data = {'variants': []}
        
        # Look for engine variant headers
        engine_patterns = [
            r'850 E-TEC[®\s]*TURBO R',
            r'850 E-TEC[®\s]*',
            r'600R E-TEC[®\s]*',
            r'600 EFI[®\s]*–[®\s]*85',
            r'600 EFI[®\s]*–[®\s]*55',
            r'900 ACE[®\s]*TURBO R',
            r'900 ACE[®\s]*TURBO',
            r'900 ACE[®\s]*',
            r'600 ACE[®\s]*',
        ]
        
        found_engines = []
        normalized_engines = []  # Track normalized versions to prevent duplicates
        
        for pattern in engine_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                clean_engine = re.sub(r'[®\s]+', ' ', match).strip()
                
                # Comprehensive normalization for duplicate detection
                normalized = self.normalize_engine_name(clean_engine)
                
                if normalized not in normalized_engines:
                    found_engines.append(clean_engine)
                    normalized_engines.append(normalized)
        
        # Extract specifications for each engine
        lines = page_text.split('\n')
        current_specs = {}
        
        for line in lines:
            line = line.strip()
            
            # Engine details pattern
            if 'liquid-cooled' in line.lower():
                current_specs['cooling'] = 'liquid-cooled'
                if 'two-stroke' in line.lower():
                    current_specs['type'] = '2-stroke'
                elif 'four-stroke' in line.lower():
                    current_specs['type'] = '4-stroke'
            
            # Displacement pattern  
            displacement_match = re.search(r'(\d+)\s*-\s*(\d+\.?\d*)\s*cc', line)
            if displacement_match:
                current_specs['displacement'] = int(float(displacement_match.group(2)))  # Convert via float first to handle decimals
                current_specs['displacement_cc'] = f"{displacement_match.group(1)} - {displacement_match.group(2)} cc"
            
            # Bore x Stroke pattern
            bore_match = re.search(r'(\d+\.?\d*)\s*x\s*(\d+\.?\d*)\s*mm', line)
            if bore_match:
                current_specs['bore_stroke'] = f"{bore_match.group(1)} x {bore_match.group(2)} mm"
            
            # Fuel system
            if 'fuel system' in line.lower():
                fuel_match = re.search(r'fuel system\s+(.*)', line, re.IGNORECASE)
                if fuel_match:
                    current_specs['fuel_system'] = fuel_match.group(1).strip()
            
            # Fuel type
            if 'premium unleaded' in line.lower():
                current_specs['fuel_type'] = 'Premium unleaded - 95'
            
            # Fuel tank
            fuel_tank_match = re.search(r'fuel tank.*?(\d+)', line, re.IGNORECASE)
            if fuel_tank_match:
                current_specs['fuel_tank_l'] = int(fuel_tank_match.group(1))
        
        # Create engine variants
        if found_engines:
            for engine_name in found_engines:
                variant = current_specs.copy()
                variant['name'] = engine_name
                variant['turbo'] = 'turbo' in engine_name.lower()
                engine_data['variants'].append(variant)
        else:
            # Single engine variant
            if current_specs:
                current_specs['name'] = 'Standard Engine'
                current_specs['turbo'] = False
                engine_data['variants'].append(current_specs)
        
        return engine_data
    
    def extract_dimensions_weight(self, page_text: str) -> Dict[str, Any]:
        """Extract dimensions and weight data"""
        dimensions = {}
        lines = page_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Overall dimensions
            length_match = re.search(r'overall length.*?(\d{1,4})\s*mm', line, re.IGNORECASE)
            if length_match:
                dimensions['overall_length_mm'] = int(length_match.group(1))
            
            width_match = re.search(r'overall width.*?(\d{1,4})\s*mm', line, re.IGNORECASE)  
            if width_match:
                dimensions['overall_width_mm'] = int(width_match.group(1))
                
            height_match = re.search(r'overall height.*?(\d{1,4})\s*mm', line, re.IGNORECASE)
            if height_match:
                dimensions['overall_height_mm'] = int(height_match.group(1))
            
            # Ski stance
            ski_match = re.search(r'ski stance.*?(\d{1,4})\s*mm', line, re.IGNORECASE)
            if ski_match:
                dimensions['ski_stance_mm'] = int(ski_match.group(1))
            
            # Dry weight
            weight_match = re.search(r'dry weight.*?(\d{1,4})\s*kg', line, re.IGNORECASE)
            if weight_match:
                dimensions['dry_weight_kg'] = int(weight_match.group(1))
        
        return dimensions
    
    def extract_features_lists(self, page_text: str) -> Dict[str, List[str]]:
        """Extract features, what's new, and package highlights"""
        features_data = {
            'features': [],
            'whats_new': [],
            'package_highlights': []
        }
        
        lines = page_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Section headers
            if "what's new" in line.lower():
                current_section = 'whats_new'
                continue
            elif 'package highlights' in line.lower():
                current_section = 'package_highlights'  
                continue
            elif 'features' in line.lower() and line.isupper():
                current_section = 'features'
                continue
            
            # Feature items (start with bullet)
            if line.startswith('•') or line.startswith('�'):
                feature_text = re.sub(r'^[•�]\s*', '', line).strip()
                if feature_text and current_section:
                    features_data[current_section].append(feature_text)
        
        # Deduplicate all feature lists
        for section in features_data:
            features_data[section] = self.deduplicate_list(features_data[section])
        
        return features_data
    
    def extract_track_options(self, page_text: str) -> List[Dict[str, Any]]:
        """Extract track options and specifications"""
        tracks = []
        
        # Track patterns
        track_pattern = r'(\w+(?:\s+\w+)*)[:\s]*\s*(\d+)\s*x\s*(\d+)\s*x\s*(\d+\.?\d*)'
        matches = re.findall(track_pattern, page_text)
        
        for match in matches:
            track_name, length, width, profile = match
            tracks.append({
                'name': track_name.strip(),
                'length_inch': int(length),
                'width_inch': int(width),
                'profile_inch': float(profile)
            })
        
        # Deduplicate tracks based on name + dimensions combination
        def track_normalizer(track):
            if isinstance(track, dict):
                name = track.get('name', '')
                dims = f"{track.get('length_inch', '')}{track.get('width_inch', '')}{track.get('profile_inch', '')}"
                return f"{name.upper().strip()}{dims}"
            return str(track).upper().strip()
        
        # Simple deduplication based on track name and dimensions
        seen_tracks = set()
        unique_tracks = []
        
        for track in tracks:
            track_key = track_normalizer(track)
            if track_key not in seen_tracks:
                seen_tracks.add(track_key)
                unique_tracks.append(track)
        
        return unique_tracks
    
    def extract_page_data(self, page_text: str, page_num: int, source_doc: str, brand: str) -> Optional[Dict[str, Any]]:
        """Extract all data from a single page and structure as JSON"""
        
        # Skip pages that don't contain model specifications
        # Look for either engine specs or model names (handle spaced text like "S U M M I T")
        has_engine_specs = any(keyword in page_text.upper() for keyword in ['ROTAX', 'E-TEC', 'CYLINDERS', 'DISPLACEMENT', 'DRY WEIGHT'])
        
        # Use same normalized text approach for detecting model names
        normalized_text = re.sub(r'[^A-Z0-9]+', '', page_text.upper())
        # Include both SKIDOO and LYNX model keywords
        model_keywords = ['SUMMIT', 'MXZ', 'RENEGADE', 'EXPEDITION', 'BACKCOUNTRY', 'FREERIDE', 'TUNDRA', 'SKANDIC',  # SKIDOO
                         'RAVE', 'ADVENTURE']  # LYNX
        has_model_names = any(keyword in normalized_text for keyword in model_keywords)
        
        if not (has_engine_specs and has_model_names):
            return None
        
        # Extract model information
        model_info = self.extract_model_info(page_text)
        if model_info['model'] == 'Unknown Model':
            return None
        
        # Extract all specifications
        engine_specs = self.extract_engine_specifications(page_text)
        dimensions = self.extract_dimensions_weight(page_text)
        features = self.extract_features_lists(page_text)
        tracks = self.extract_track_options(page_text)
        
        # Generate SKU
        sku = f"{brand}-{model_info['model'].replace(' ', '-').upper()}"
        if model_info['configuration'] != 'Base':
            sku += f"-{model_info['configuration'].replace(' ', '-').upper()}"
        sku += f"-2026"
        
        # Build specifications JSON in unified structure
        specifications = {
            'engines': [
                {
                    'name': variant.get('name', 'Standard Engine'),
                    'type': variant.get('type', '2-stroke'),
                    'displacement': variant.get('displacement'),
                    'bore_stroke': variant.get('bore_stroke'),
                    'turbo': variant.get('turbo', False),
                    'cooling': variant.get('cooling', 'liquid-cooled'),
                    'fuel_system': variant.get('fuel_system'),
                    'fuel_type': variant.get('fuel_type'),
                    'fuel_tank_l': variant.get('fuel_tank_l'),
                    'displacement_cc': variant.get('displacement_cc')
                } for variant in engine_specs.get('variants', [])
            ],
            'dimensions': {
                'overall': {
                    'length_mm': dimensions.get('overall_length_mm'),
                    'width_mm': dimensions.get('overall_width_mm'),
                    'height_mm': dimensions.get('overall_height_mm')
                },
                'ski_stance_mm': dimensions.get('ski_stance_mm'),
                'dry_weight_kg': dimensions.get('dry_weight_kg')
            },
            'tracks': [
                {
                    'name': track.get('name', 'Standard'),
                    'size': f"{track.get('length_inch')}x{track.get('width_inch')}x{track.get('profile_inch')}",
                    'length_inch': track.get('length_inch'),
                    'width_inch': track.get('width_inch'),
                    'profile_inch': track.get('profile_inch')
                } for track in tracks
            ],
            'features': {
                'platform': 'REV Gen5',  # Default, could be extracted
                'source_page': page_num
            }
        }
        
        # Extract key fields for indexed columns
        primary_engine = engine_specs['variants'][0] if engine_specs['variants'] else {}
        
        return {
            'sku': sku,
            'brand': brand,
            'model': model_info['model'],
            'configuration': model_info['configuration'],  # Updated field name
            'category': model_info['category'],  # New field
            'model_year': 2026,
            'description': f"{brand} {model_info['model']} {model_info['configuration']}",
            'specifications': specifications,
            'whats_new': features['whats_new'],  # Separate field
            'package_highlights': features['package_highlights'],  # Separate field
            'spring_options': [],  # TODO: Extract spring options
            'engine_displacement': primary_engine.get('displacement'),
            'engine_type': primary_engine.get('type'),
            'engine_turbo': primary_engine.get('turbo', False),
            'dry_weight_kg': dimensions.get('dry_weight_kg'),
            'track_length_mm': tracks[0]['length_inch'] * 25.4 if tracks else None,
            'ski_stance_mm': dimensions.get('ski_stance_mm'),
            'source_document': source_doc,
            'extraction_method': 'unified_structure_v2'
        }
    
    def extract_pdf(self, pdf_path: Path, brand: str) -> List[Dict[str, Any]]:
        """Extract all models from PDF"""
        all_products = []
        
        logger.info(f"Extracting from {pdf_path.name}")
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            # Focus on specification pages
            spec_pages = range(8, min(32, total_pages + 1))
            
            for page_num in spec_pages:
                if page_num <= total_pages:
                    page = pdf.pages[page_num - 1]
                    page_text = page.extract_text()
                    
                    if page_text:
                        product_data = self.extract_page_data(page_text, page_num, pdf_path.name, brand)
                        
                        if product_data:
                            all_products.append(product_data)
                            logger.info(f"  Page {page_num}: Extracted {product_data['model']} {product_data['configuration']}")
        
        return all_products
    
    def save_to_database(self, products: List[Dict[str, Any]]):
        """Save products to target schema table"""
        if not products:
            logger.warning("No products to save")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for product in products:
            try:
                # Calculate derived fields from specifications
                specifications = product.get('specifications', {})
                engines = specifications.get('engines', [])
                
                # Calculate primary engine displacement
                primary_engine_displacement = None
                if engines and len(engines) > 0:
                    primary_engine_displacement = engines[0].get('displacement')
                
                # Calculate weight range from engines or dimensions
                min_dry_weight_kg = None
                max_dry_weight_kg = None
                if engines:
                    weights = [eng.get('dry_weight_kg') for eng in engines if eng.get('dry_weight_kg')]
                    if weights:
                        min_dry_weight_kg = min(weights)
                        max_dry_weight_kg = max(weights)
                
                # If no engine weights, try dimensions
                if not min_dry_weight_kg and not max_dry_weight_kg:
                    dimensions = specifications.get('dimensions', {})
                    dry_weight = dimensions.get('dry_weight_kg')
                    if dry_weight:
                        min_dry_weight_kg = dry_weight
                        max_dry_weight_kg = dry_weight
                
                # Check if any engine has turbo
                has_turbo = any(eng.get('turbo', False) for eng in engines) if engines else False
                
                # Count engines
                engine_count = len(engines) if engines else 1
                
                cursor.execute('''
                    INSERT OR REPLACE INTO raw_specbook_data_target_schema
                    (sku, brand, model, configuration, category, model_year, description, 
                     specifications, whats_new, package_highlights, spring_options,
                     primary_engine_displacement, min_dry_weight_kg, max_dry_weight_kg, 
                     has_turbo, engine_count, source_document, extraction_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product['sku'],
                    product['brand'],
                    product['model'],
                    product['configuration'],
                    product['category'],
                    product['model_year'],
                    product['description'],
                    json.dumps(product['specifications']),
                    json.dumps(product['whats_new']) if product['whats_new'] else None,
                    json.dumps(product['package_highlights']) if product['package_highlights'] else None,
                    json.dumps(product['spring_options']) if product['spring_options'] else None,
                    primary_engine_displacement,
                    min_dry_weight_kg,
                    max_dry_weight_kg,
                    has_turbo,
                    engine_count,
                    product['source_document'],
                    product['extraction_method']
                ))
                
            except Exception as e:
                logger.error(f"Error inserting {product['sku']}: {e}")
                
        conn.commit()
        conn.close()
        
        logger.info(f"Saved {len(products)} products to database")

def main():
    """Main extraction process"""
    extractor = JsonSpecExtractor()
    total_products = 0
    
    # Extract SKIDOO spec book
    skidoo_pdf = Path("docs/SKIDOO_2026 PRODUCT SPEC BOOK - 1-30.pdf")
    if skidoo_pdf.exists():
        skidoo_products = extractor.extract_pdf(skidoo_pdf, "SKIDOO")
        extractor.save_to_database(skidoo_products)
        total_products += len(skidoo_products)
        logger.info(f"SKIDOO extraction complete: {len(skidoo_products)} models")
    else:
        logger.error(f"SKIDOO PDF not found: {skidoo_pdf}")
    
    # Extract LYNX spec book
    lynx_pdf = Path("docs/LYNX_2026 PRODUCT SPEC BOOK - 1-35.pdf")
    if lynx_pdf.exists():
        lynx_products = extractor.extract_pdf(lynx_pdf, "LYNX")
        extractor.save_to_database(lynx_products)
        total_products += len(lynx_products)
        logger.info(f"LYNX extraction complete: {len(lynx_products)} models")
    else:
        logger.error(f"LYNX PDF not found: {lynx_pdf}")
    
    logger.info(f"Total extraction complete: {total_products} models from both brands")

if __name__ == "__main__":
    main()