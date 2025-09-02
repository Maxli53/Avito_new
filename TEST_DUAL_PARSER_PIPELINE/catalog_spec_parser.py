import re
import fitz  # PyMuPDF
import sqlite3
import os
import io
from pathlib import Path
from uuid import uuid4
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from difflib import SequenceMatcher
import json

# Image processing imports
try:
    import cv2
    import pytesseract
    from PIL import Image
    import numpy as np
    from sklearn.cluster import KMeans
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    print("Warning: Image processing libraries not available. Install opencv-python, pytesseract, pillow, scikit-learn for full functionality.")

class SkiDooCatalogParser:
    """Comprehensive parser for SKI-DOO Product Spec Book - extracts ALL vehicle data and marketing information"""
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db", docs_folder: str = "docs"):
        self.vehicles = []
        self.engines = {}
        self.colors = {}
        self.marketing_data = {}
        self.db_path = db_path
        self.price_list_base_models = []
        self.parser_version = "2.0.0"
        self.docs_folder = Path(docs_folder)
        self.available_pdfs = {}
        
        # Create directories for image extraction
        self.image_dir = Path("extracted_images/products")
        self.image_dir.mkdir(parents=True, exist_ok=True)
        
        # Discover available PDFs
        self._discover_pdfs()
        
    def extract_all_catalog_data(self, pdf_path: Path = None, brand: str = "SKI-DOO", year: int = 2026) -> Dict[str, Any]:
        """Extract comprehensive catalog data including vehicles, engines, colors, and marketing content"""
        
        # If no specific path provided, find the PDF automatically
        if pdf_path is None:
            pdf_path = self.get_catalog_pdf(brand, year)
            if pdf_path is None:
                raise FileNotFoundError(f"No catalog PDF found for {brand} {year}")
        
        print(f"=== COMPREHENSIVE {brand} {year} CATALOG EXTRACTION ===")
        print(f"Processing: {pdf_path}")
        
        # Store current PDF path for reference
        self.current_pdf_path = pdf_path
        
        # Load price list data for matching
        self._load_price_list_base_models()
        
        results = {
            'vehicles': [],
            'engines': {},
            'colors': {},
            'marketing_data': {},
            'technical_specs': {},
            'comparative_data': {},
            'metadata': {
                'brand': 'SKI-DOO',
                'model_year': 2026,
                'document_type': 'Product Spec Book',
                'total_pages': 0,
                'extraction_timestamp': None
            }
        }
        
        with fitz.open(pdf_path) as pdf:
            results['metadata']['total_pages'] = pdf.page_count
            
            for page_num in range(pdf.page_count):
                page = pdf[page_num]
                print(f"Processing page {page_num + 1}/{pdf.page_count}")
                
                text = page.get_text()
                if not text:
                    continue
                
                # Extract different types of content based on page content
                if page_num < 5:  # Cover and intro pages
                    self._extract_marketing_intro(text, results)
                elif 'ROTAX' in text and 'ENGINES' in text:
                    self._extract_engine_specifications(text, results)
                elif 'COLORS' in text or any(color in text for color in ['TERRA GREEN', 'SCANDI BLUE', 'MONUMENT GREY']):
                    self._extract_color_information(text, results)
                elif any(model in text for model in ['SUMMIT', 'MXZ', 'RENEGADE', 'EXPEDITION', 'FREERIDE', 'BACKCOUNTRY']):
                    self._extract_vehicle_specifications(text, page_num + 1, results)
                elif 'COMPARATIVE CHART' in text:
                    self._extract_comparative_data(text, results)
                
        # Post-process and organize data
        self._finalize_extraction(results)
        
        return results
    
    def _load_price_list_base_models(self):
        """Load Model+Package combinations from price list for matching"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT model_code, malli, paketti 
                FROM price_entries 
                WHERE malli IS NOT NULL AND paketti IS NOT NULL
            """)
            
            for row in cursor.fetchall():
                model_code, malli, paketti = row
                base_model = f"{malli} {paketti}".strip()
                self.price_list_base_models.append({
                    'model_code': model_code,
                    'base_model': base_model,
                    'malli': malli,
                    'paketti': paketti
                })
            
            conn.close()
            print(f"Loaded {len(self.price_list_base_models)} base models from price list")
            
        except Exception as e:
            print(f"Warning: Could not load price list data: {e}")
            self.price_list_base_models = []
    
    def _discover_pdfs(self):
        """Discover all PDF files in docs folder"""
        if not self.docs_folder.exists():
            print(f"Warning: docs folder {self.docs_folder} not found")
            return
        
        pdf_files = list(self.docs_folder.glob("*.pdf"))
        print(f"Discovered {len(pdf_files)} PDF files in {self.docs_folder}")
        
        for pdf_path in pdf_files:
            pdf_info = self._analyze_pdf_file(pdf_path)
            if pdf_info:
                self.available_pdfs[pdf_info['key']] = pdf_info
                print(f"  Registered: {pdf_info['brand']} {pdf_info['year']} {pdf_info['type']} ({pdf_info['size_kb']:.1f}KB)")
    
    def _analyze_pdf_file(self, pdf_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze PDF file to extract metadata"""
        filename = pdf_path.name
        
        # Determine brand
        brand = "UNKNOWN"
        if "SKI-DOO" in filename or "SKIDOO" in filename:
            brand = "SKI-DOO"
        elif "LYNX" in filename:
            brand = "LYNX"
        
        # Extract year
        year_match = re.search(r'(\d{4})', filename)
        year = int(year_match.group(1)) if year_match else 0
        
        # Determine PDF type
        pdf_type = "UNKNOWN"
        if "PRICE" in filename and "LIST" in filename:
            pdf_type = "PRICE_LIST"
        elif "PRODUCT" in filename and "SPEC" in filename:
            pdf_type = "PRODUCT_SPEC_BOOK"
        
        file_size = pdf_path.stat().st_size
        key = f"{brand}_{year}_{pdf_type}"
        
        return {
            'key': key,
            'file_path': pdf_path,
            'filename': filename,
            'brand': brand,
            'year': year,
            'type': pdf_type,
            'size_kb': file_size / 1024
        }
    
    def get_pdf(self, brand: str = "SKI-DOO", year: int = 2026, pdf_type: str = "PRODUCT_SPEC_BOOK") -> Optional[Path]:
        """Get path to specific PDF file"""
        key = f"{brand}_{year}_{pdf_type}"
        pdf_info = self.available_pdfs.get(key)
        return pdf_info['file_path'] if pdf_info else None
    
    def list_available_pdfs(self):
        """Print all available PDFs"""
        print(f"\n=== AVAILABLE PDFS ===")
        for pdf_info in self.available_pdfs.values():
            print(f"  {pdf_info['brand']} {pdf_info['year']} {pdf_info['type']}: {pdf_info['filename']}")
    
    def get_catalog_pdf(self, brand: str = "SKI-DOO", year: int = 2026) -> Optional[Path]:
        """Get catalog PDF path for specified brand and year"""
        return self.get_pdf(brand, year, "PRODUCT_SPEC_BOOK")
    
    def _extract_marketing_intro(self, text: str, results: Dict[str, Any]):
        """Extract marketing introduction and brand messaging"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Extract key marketing messages
            if len(line) > 20 and any(word in line.lower() for word in ['performance', 'experience', 'adventure', 'ultimate', 'precision']):
                if 'marketing_messages' not in results['marketing_data']:
                    results['marketing_data']['marketing_messages'] = []
                results['marketing_data']['marketing_messages'].append(line)
            
            # Extract product categories
            if 'VEHICLES • ACCESSORIES • PARTS • MAINTENANCE • APPAREL' in line:
                results['marketing_data']['product_categories'] = ['VEHICLES', 'ACCESSORIES', 'PARTS', 'MAINTENANCE', 'APPAREL']
    
    def _extract_engine_specifications(self, text: str, results: Dict[str, Any]):
        """Extract comprehensive engine specifications and technical data"""
        lines = text.split('\n')
        
        current_engine = None
        engine_data = {}
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Detect engine types
            if re.match(r'^\d+\s+(E-TEC|ACE|EFI)', line):
                if current_engine and engine_data:
                    results['engines'][current_engine] = engine_data
                
                current_engine = line
                engine_data = {
                    'name': line,
                    'specifications': {},
                    'features': [],
                    'marketing_points': []
                }
            
            # Extract horsepower
            hp_match = re.search(r'(\d+)\s*horsepower', line, re.IGNORECASE)
            if hp_match and current_engine:
                engine_data['specifications']['horsepower'] = int(hp_match.group(1))
            
            # Extract fuel economy
            fuel_match = re.search(r'(\d+\.?\d*)\s*L/100\s*km', line)
            if fuel_match and current_engine:
                engine_data['specifications']['fuel_economy'] = float(fuel_match.group(1))
            
            # Extract engine features
            if any(feature in line for feature in ['E-TEC', 'direct injection', 'turbo', 'ACE', 'iTC']):
                if current_engine:
                    engine_data['features'].append(line)
            
            # Extract marketing benefits
            if any(benefit in line.lower() for benefit in ['fuel economy', 'reliability', 'performance', 'efficient']):
                if current_engine and len(line) > 10:
                    engine_data['marketing_points'].append(line)
        
        # Save last engine
        if current_engine and engine_data:
            results['engines'][current_engine] = engine_data
    
    def _extract_color_information(self, text: str, results: Dict[str, Any]):
        """Extract color palette and naming information"""
        lines = text.split('\n')
        
        color_categories = {
            'main_colors': [],
            'accent_colors': [],
            'special_colors': []
        }
        
        current_category = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect color categories
            if 'MAIN COLORS' in line:
                current_category = 'main_colors'
            elif 'ACCENT COLORS' in line:
                current_category = 'accent_colors'
            
            # Extract color names
            color_names = [
                'TERRA GREEN', 'SCANDI BLUE', 'MAGMA RED', 'MONUMENT GREY', 
                'TIMELESS BLACK', 'FLARE YELLOW', 'MINERAL BLUE', 'NEO YELLOW',
                'WHITE', 'LIQUID TITANIUM', 'CATALYST GREY', 'BLACK', 'ORANGE CRUSH'
            ]
            
            for color in color_names:
                if color in line:
                    color_info = {
                        'name': color,
                        'category': current_category or 'standard',
                        'availability': self._extract_availability_info(line)
                    }
                    
                    if current_category and current_category in color_categories:
                        color_categories[current_category].append(color_info)
                    else:
                        if 'all_colors' not in results['colors']:
                            results['colors']['all_colors'] = []
                        results['colors']['all_colors'].append(color_info)
        
        results['colors'].update(color_categories)
    
    def _extract_vehicle_specifications(self, text: str, page_num: int, results: Dict[str, Any]):
        """Extract comprehensive vehicle specifications and marketing data using intelligent matching"""
        
        # Try to match vehicles from price list
        matched_vehicle = self._match_vehicle_from_text(text, page_num)
        
        if not matched_vehicle:
            return  # Skip if no match found
        
        vehicle = {
            'id': str(uuid4()),
            'page_number': page_num,
            'specifications': {},
            'features': {},
            'marketing': {},
            'dimensions': {},
            'performance': {},
            'options': {},
            'powertrain': {},
            'suspension': {},
            'tracks': {},
            'colors': [],
            'product_images': [],
            # Matching metadata
            'matching_method': matched_vehicle['matching_method'],
            'matching_confidence': matched_vehicle['matching_confidence'],
            'confidence_description': matched_vehicle.get('confidence_description'),
            'matching_notes': matched_vehicle.get('matching_notes'),
            'extraction_timestamp': datetime.now().isoformat(),
            'source_catalog_name': matched_vehicle['source_catalog_name'],
            'source_catalog_page': page_num,
            'price_list_model_code': matched_vehicle.get('price_list_model_code'),
            'extraction_method': 'PDF_TEXT',
            'parser_version': self.parser_version
        }
        
        # Set vehicle name and model family from matched data
        vehicle['name'] = matched_vehicle['vehicle_name']
        vehicle['model_family'] = matched_vehicle['base_model_data']['malli']
        
        # Extract comprehensive data using improved parsing
        self._extract_rotax_engine_specs(text, vehicle)
        self._extract_powertrain_specs(text, vehicle)
        self._extract_weight_dimensions(text, vehicle)
        self._extract_suspension_detailed(text, vehicle)
        self._extract_feature_details(text, vehicle)
        self._extract_track_specifications(text, vehicle)
        self._extract_color_options(text, vehicle)
        self._extract_marketing_content(text, vehicle)
        self._extract_whats_new(text, vehicle)
        self._extract_spring_options(text, vehicle)
        self._extract_package_highlights(text, vehicle)
        
        # Extract product images if available
        if IMAGE_PROCESSING_AVAILABLE:
            vehicle['product_images'] = self._extract_product_images(page_num, vehicle['name'])
        
        results['vehicles'].append(vehicle)
    
    def _match_vehicle_from_text(self, text: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Match vehicle in catalog text to price list base models"""
        
        catalog_name = self.current_pdf_path.name if hasattr(self, 'current_pdf_path') else "Unknown Catalog"
        
        # Try each base model from price list
        for base_model_data in self.price_list_base_models:
            base_model = base_model_data['base_model']
            
            # 1. Try exact match
            if base_model.upper() in text.upper():
                return {
                    'vehicle_name': base_model,
                    'base_model_data': base_model_data,
                    'matching_method': 'EXACT',
                    'matching_confidence': 1.0,
                    'source_catalog_name': catalog_name,
                    'price_list_model_code': base_model_data['model_code']
                }
            
            # 2. Try normalized match (handle spacing, special chars)
            normalized_base = self._normalize_vehicle_name(base_model)
            normalized_text = self._normalize_vehicle_name(text)
            
            if normalized_base in normalized_text:
                return {
                    'vehicle_name': base_model,
                    'base_model_data': base_model_data,
                    'matching_method': 'NORMALIZED',
                    'matching_confidence': 0.95,
                    'source_catalog_name': catalog_name,
                    'price_list_model_code': base_model_data['model_code']
                }
            
            # 3. Try strict fuzzy match as fallback
            fuzzy_result = self._strict_fuzzy_match(base_model, text)
            if fuzzy_result['matched']:
                return {
                    'vehicle_name': base_model,
                    'base_model_data': base_model_data,
                    'matching_method': 'FUZZY',
                    'matching_confidence': fuzzy_result['confidence'],
                    'confidence_description': fuzzy_result['confidence_description'],
                    'matching_notes': fuzzy_result['matching_notes'],
                    'source_catalog_name': catalog_name,
                    'price_list_model_code': base_model_data['model_code']
                }
        
        return None  # No match found
    
    def _normalize_vehicle_name(self, name: str) -> str:
        """Normalize vehicle name for matching"""
        # Remove special characters, extra spaces, normalize case
        normalized = re.sub(r'[®™©]', '', name)  # Remove trademark symbols
        normalized = re.sub(r'[-_]', ' ', normalized)  # Replace hyphens/underscores with spaces
        normalized = re.sub(r'\\s+', ' ', normalized)  # Collapse multiple spaces
        return normalized.strip().upper()
    
    def _strict_fuzzy_match(self, base_model: str, text: str) -> Dict[str, Any]:
        """Perform strict fuzzy matching to avoid false positives"""
        
        # Extract model family from base model
        model_family = base_model.split()[0].upper()
        
        # Only look for candidates with same model family
        candidates = self._extract_same_family_candidates(text, model_family)
        
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            # Check length similarity (within 20%)
            len_ratio = len(candidate) / len(base_model)
            if len_ratio < 0.8 or len_ratio > 1.2:
                continue
            
            # Calculate similarity using SequenceMatcher
            score = SequenceMatcher(None, base_model.upper(), candidate.upper()).ratio()
            
            # Very strict threshold
            if score > 0.92 and score > best_score:
                best_match = candidate
                best_score = score
        
        if best_match:
            return {
                'matched': True,
                'confidence': best_score,
                'confidence_description': f"Strict match with {best_score:.3f} confidence.",
                'matching_notes': "Fuzzy matching used for resolving catalog base model.",
                'matched_text': best_match
            }
        
        return {'matched': False}
    
    def _extract_same_family_candidates(self, text: str, model_family: str) -> List[str]:
        """Extract potential vehicle names from text that belong to the same model family"""
        
        lines = text.split('\\n')
        candidates = []
        
        for line in lines:
            line = line.strip()
            if model_family in line.upper():
                # Extract potential vehicle names that contain the model family
                words = line.split()
                for i, word in enumerate(words):
                    if model_family in word.upper():
                        # Try to capture the full vehicle name (2-4 words)
                        for length in [2, 3, 4]:
                            if i + length <= len(words):
                                candidate = ' '.join(words[i:i+length])
                                if len(candidate) > 5:  # Minimum reasonable length
                                    candidates.append(candidate)
        
        return list(set(candidates))  # Remove duplicates
    
    def _extract_product_images(self, page_num: int, vehicle_name: str) -> List[Dict[str, Any]]:
        """Extract and process product images for the vehicle"""
        
        if not IMAGE_PROCESSING_AVAILABLE:
            return []
        
        product_images = []
        
        try:
            # Re-open PDF to extract images from this specific page
            with fitz.open(self.current_pdf_path) as pdf:
                page = pdf[page_num - 1]  # page_num is 1-indexed
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    pix = fitz.Pixmap(pdf, xref)
                    
                    # Filter out small images (logos, icons)
                    if pix.width > 200 and pix.height > 150:
                        
                        # Save image file
                        clean_vehicle_name = re.sub(r'[^\\w\\s-]', '', vehicle_name).replace(' ', '_')
                        image_filename = f"{clean_vehicle_name}_page{page_num}_{img_index}.png"
                        image_path = self.image_dir / image_filename
                        
                        pix.save(str(image_path))
                        
                        # Analyze image
                        image_analysis = self._analyze_product_image(pix, vehicle_name)
                        
                        product_images.append({
                            'vehicle_name': vehicle_name,
                            'image_filename': image_filename,
                            'image_path': str(image_path),
                            'page_number': page_num,
                            'image_index': img_index,
                            'width': pix.width,
                            'height': pix.height,
                            'image_type': image_analysis['type'],
                            'dominant_colors': image_analysis['colors'],
                            'features_visible': image_analysis['features'],
                            'quality_score': image_analysis['quality'],
                            'extraction_timestamp': datetime.now().isoformat(),
                            'source_catalog': self.current_pdf_path.name,
                            'extraction_method': 'PRODUCT_IMAGE_EXTRACTION'
                        })
                    
                    pix = None
                        
        except Exception as e:
            print(f"Warning: Could not extract images for {vehicle_name}: {e}")
        
        return product_images
    
    def _analyze_product_image(self, pixmap, vehicle_name: str) -> Dict[str, Any]:
        """Analyze product image to determine type and extract metadata"""
        
        analysis = {
            'type': 'UNKNOWN',
            'colors': [],
            'features': [],
            'quality': 0.0
        }
        
        try:
            # Determine image type based on size
            if pixmap.width > 800 and pixmap.height > 400:
                analysis['type'] = 'MAIN_PRODUCT'
                analysis['quality'] = 0.9
            elif pixmap.width > 400 and pixmap.height > 200:
                analysis['type'] = 'COLOR_VARIANT'
                analysis['quality'] = 0.8
            else:
                analysis['type'] = 'DETAIL'
                analysis['quality'] = 0.6
            
            # Convert to PIL for analysis
            pil_image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            
            # Extract dominant colors
            analysis['colors'] = self._extract_vehicle_colors_from_image(pil_image)
            
            # Try to identify visible features using OCR
            analysis['features'] = self._identify_vehicle_features_in_image(pil_image, vehicle_name)
            
        except Exception as e:
            print(f"Warning: Could not analyze image: {e}")
        
        return analysis
    
    def _extract_vehicle_colors_from_image(self, pil_image) -> List[Dict[str, Any]]:
        """Extract actual vehicle colors from product image"""
        
        if not IMAGE_PROCESSING_AVAILABLE:
            return []
        
        try:
            # Convert to numpy array
            img_array = np.array(pil_image)
            
            # Focus on center region where vehicle typically appears
            center_h, center_w = img_array.shape[0]//4, img_array.shape[1]//4
            vehicle_region = img_array[center_h:3*center_h, center_w:3*center_w]
            
            # Color clustering on vehicle region
            pixels = vehicle_region.reshape((-1, 3))
            
            # Use smaller cluster count for better color identification
            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10).fit(pixels)
            
            # Filter out background colors and extract vehicle colors
            vehicle_colors = []
            for color_center in kmeans.cluster_centers_:
                rgb = tuple(map(int, color_center))
                
                # Skip likely background colors (very light or very dark)
                if not self._is_background_color(rgb):
                    color_name = self._map_rgb_to_color_name(rgb)
                    vehicle_colors.append({
                        'rgb': rgb,
                        'hex': '#{:02x}{:02x}{:02x}'.format(*rgb),
                        'name': color_name,
                        'extraction_method': 'PRODUCT_IMAGE_COLOR'
                    })
            
            return vehicle_colors[:3]  # Return top 3 colors
            
        except Exception as e:
            print(f"Warning: Could not extract colors from image: {e}")
            return []
    
    def _identify_vehicle_features_in_image(self, pil_image, vehicle_name: str) -> List[Dict[str, Any]]:
        """Identify visible vehicle features in product image"""
        
        features = []
        
        try:
            # Use OCR to find feature callouts in the image
            ocr_text = pytesseract.image_to_string(pil_image)
            
            # Look for common snowmobile features in image text
            feature_keywords = [
                'LED headlight', 'digital display', 'suspension', 'track', 'ski',
                'windshield', 'seat', 'handlebar', 'brake', 'starter', 'clutch',
                'gauge', 'mirror', 'storage', 'footrest', 'grip'
            ]
            
            for keyword in feature_keywords:
                if keyword.lower() in ocr_text.lower():
                    features.append({
                        'feature_name': keyword,
                        'detection_method': 'OCR_IN_IMAGE',
                        'confidence': 0.7
                    })
            
        except Exception as e:
            print(f"Warning: Could not identify features in image: {e}")
        
        return features
    
    def _is_background_color(self, rgb: tuple) -> bool:
        """Check if RGB color is likely a background color"""
        r, g, b = rgb
        
        # Very light colors (likely background/snow)
        if r > 240 and g > 240 and b > 240:
            return True
        
        # Very dark colors (likely shadows/text)
        if r < 30 and g < 30 and b < 30:
            return True
        
        # Grayish colors (likely background)
        if abs(r - g) < 20 and abs(g - b) < 20 and abs(r - b) < 20:
            if 80 < r < 180:  # Mid-range gray
                return True
        
        return False
    
    def _map_rgb_to_color_name(self, rgb: tuple) -> str:
        """Map RGB values to approximate color names"""
        r, g, b = rgb
        
        # Simple color mapping
        if r > 200 and g < 100 and b < 100:
            return "Red"
        elif r < 100 and g > 200 and b < 100:
            return "Green"
        elif r < 100 and g < 100 and b > 200:
            return "Blue"
        elif r > 200 and g > 200 and b < 100:
            return "Yellow"
        elif r > 200 and g > 150 and b < 100:
            return "Orange"
        elif r > 150 and g < 100 and b > 150:
            return "Purple"
        elif r < 50 and g < 50 and b < 50:
            return "Black"
        elif r > 220 and g > 220 and b > 220:
            return "White"
        elif 100 < r < 150 and 100 < g < 150 and 100 < b < 150:
            return "Gray"
        else:
            return f"RGB({r},{g},{b})"
    
    def _extract_engine_data_from_specs(self, text: str, vehicle: Dict[str, Any]):
        """Extract engine specifications from vehicle spec text"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Engine type
            if 'Engine details' in line or any(engine in line for engine in ['E-TEC', 'ACE', 'EFI', 'TURBO']):
                vehicle['specifications']['engine_type'] = line
            
            # Cylinders and displacement
            cyl_match = re.search(r'(\d+)\s*-\s*(\d+(?:,\d+)?)\s*cc', line)
            if cyl_match:
                vehicle['specifications']['cylinders'] = int(cyl_match.group(1))
                displacement = cyl_match.group(2).replace(',', '')
                vehicle['specifications']['displacement_cc'] = int(displacement)
            
            # Bore and stroke
            bore_match = re.search(r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*mm', line)
            if bore_match:
                vehicle['specifications']['bore_mm'] = float(bore_match.group(1))
                vehicle['specifications']['stroke_mm'] = float(bore_match.group(2))
            
            # Fuel system
            if 'Fuel System' in line:
                vehicle['specifications']['fuel_system'] = line.split('Fuel System')[-1].strip()
            
            # Fuel tank capacity
            fuel_match = re.search(r'Fuel tank.*?(\d+)\s*L', line)
            if fuel_match:
                vehicle['specifications']['fuel_tank_liters'] = int(fuel_match.group(1))
            
            # Oil tank capacity
            oil_match = re.search(r'Oil tank.*?(\d+\.?\d*)\s*L', line)
            if oil_match:
                vehicle['specifications']['oil_tank_liters'] = float(oil_match.group(1))
    
    def _extract_dimensions(self, text: str, vehicle: Dict[str, Any]):
        """Extract physical dimensions"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Overall length
            length_match = re.search(r'Vehicle overall length.*?(\d+(?:,\d+)?)\s*mm', line)
            if length_match:
                vehicle['dimensions']['length_mm'] = int(length_match.group(1).replace(',', ''))
            
            # Overall width
            width_match = re.search(r'Vehicle overall width.*?(\d+(?:,\d+)?)\s*mm', line)
            if width_match:
                vehicle['dimensions']['width_mm'] = int(width_match.group(1).replace(',', ''))
            
            # Overall height
            height_match = re.search(r'Vehicle overall height.*?(\d+(?:,\d+)?)\s*mm', line)
            if height_match:
                vehicle['dimensions']['height_mm'] = int(height_match.group(1).replace(',', ''))
            
            # Ski stance
            ski_match = re.search(r'Ski stance.*?(\d+)\s*mm', line)
            if ski_match:
                vehicle['dimensions']['ski_stance_mm'] = int(ski_match.group(1))
            
            # Dry weight
            weight_match = re.search(r'Dry weight.*?(\d+)\s*kg', line)
            if weight_match:
                vehicle['dimensions']['dry_weight_kg'] = int(weight_match.group(1))
    
    def _extract_suspension_specs(self, text: str, vehicle: Dict[str, Any]):
        """Extract suspension specifications"""
        lines = text.split('\n')
        
        suspension_data = {}
        
        for line in lines:
            line = line.strip()
            
            # Front suspension
            if 'Front suspension' in line:
                suspension_data['front_suspension'] = line.split('Front suspension')[-1].strip()
            
            # Front shock
            if 'Front shock' in line:
                suspension_data['front_shock'] = line.split('Front shock')[-1].strip()
            
            # Front suspension travel
            front_travel_match = re.search(r'Front suspension travel.*?(\d+)\s*mm', line)
            if front_travel_match:
                suspension_data['front_travel_mm'] = int(front_travel_match.group(1))
            
            # Rear suspension
            if 'Rear suspension' in line and 'travel' not in line:
                suspension_data['rear_suspension'] = line.split('Rear suspension')[-1].strip()
            
            # Rear shock
            if 'Rear shock' in line:
                suspension_data['rear_shock'] = line.split('Rear shock')[-1].strip()
            
            # Rear suspension travel
            rear_travel_match = re.search(r'Rear suspension travel.*?(\d+)\s*mm', line)
            if rear_travel_match:
                suspension_data['rear_travel_mm'] = int(rear_travel_match.group(1))
        
        if suspension_data:
            vehicle['specifications']['suspension'] = suspension_data
    
    def _extract_features_list(self, text: str, vehicle: Dict[str, Any]):
        """Extract comprehensive features list"""
        lines = text.split('\n')
        
        features = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Platform
            if 'Platform' in line:
                features['platform'] = line.split('Platform')[-1].strip()
            
            # Headlights
            if 'Headlights' in line:
                features['headlights'] = line.split('Headlights')[-1].strip()
            
            # Skis
            if 'Skis' in line and 'ski stance' not in line.lower():
                features['skis'] = line.split('Skis')[-1].strip()
            
            # Seating
            if 'Seating' in line:
                features['seating'] = line.split('Seating')[-1].strip()
            
            # Handlebar
            if 'Handlebar' in line:
                features['handlebar'] = line.split('Handlebar')[-1].strip()
            
            # Starter
            if 'Starter' in line:
                features['starter'] = line.split('Starter')[-1].strip()
            
            # Reverse
            if 'Reverse' in line:
                features['reverse'] = line.split('Reverse')[-1].strip()
            
            # Brake system
            if 'Brake system' in line:
                features['brake_system'] = line.split('Brake system')[-1].strip()
            
            # Gauge type
            if 'Gauge type' in line:
                features['gauge_type'] = line.split('Gauge type')[-1].strip()
            
            # Windshield
            if 'Windshield' in line:
                features['windshield'] = line.split('Windshield')[-1].strip()
        
        if features:
            vehicle['features'] = features
    
    def _extract_rotax_engine_specs(self, text: str, vehicle: Dict[str, Any]):
        """Extract ROTAX engine specifications"""
        lines = text.split('\n')
        
        engine_specs = {}
        in_engine_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect engine section
            if 'ROTAX' in line and 'ENGINE' in line:
                in_engine_section = True
                engine_specs['engine_family'] = line
                continue
            elif in_engine_section and ('POWERTRAIN' in line or 'DRY WEIGHT' in line):
                break
            
            if in_engine_section:
                # Engine details
                if 'Engine details' in line:
                    engine_specs['engine_details'] = line.split('Engine details')[-1].strip()
                
                # Cylinders and displacement  
                if 'Cylinders – Displacement' in line:
                    cyl_disp = line.split('Cylinders – Displacement')[-1].strip()
                    engine_specs['cylinders_displacement'] = cyl_disp
                    # Parse numbers
                    cyl_match = re.search(r'(\d+)\s*-\s*(\d+(?:,\d+)?)\s*cc', cyl_disp)
                    if cyl_match:
                        engine_specs['cylinders'] = int(cyl_match.group(1))
                        displacement = cyl_match.group(2).replace(',', '')
                        engine_specs['displacement_cc'] = int(displacement)
                
                # Bore and stroke
                if 'Bore – Stroke' in line:
                    bore_stroke = line.split('Bore – Stroke')[-1].strip()
                    engine_specs['bore_stroke'] = bore_stroke
                    bore_match = re.search(r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*mm', bore_stroke)
                    if bore_match:
                        engine_specs['bore_mm'] = float(bore_match.group(1))
                        engine_specs['stroke_mm'] = float(bore_match.group(2))
                
                # Fuel system
                if 'Fuel System' in line:
                    engine_specs['fuel_system'] = line.split('Fuel System')[-1].strip()
                
                # Fuel type and octane
                if 'Fuel type – Octane' in line:
                    engine_specs['fuel_type_octane'] = line.split('Fuel type – Octane')[-1].strip()
                
                # Fuel tank
                if 'Fuel tank (L)' in line:
                    fuel_match = re.search(r'(\d+)', line)
                    if fuel_match:
                        engine_specs['fuel_tank_liters'] = int(fuel_match.group(1))
                
                # Oil tank
                if 'Oil tank capacity (L)' in line:
                    oil_match = re.search(r'(\d+\.?\d*)', line)
                    if oil_match:
                        engine_specs['oil_tank_liters'] = float(oil_match.group(1))
        
        if engine_specs:
            vehicle['specifications']['engine'] = engine_specs
    
    def _extract_powertrain_specs(self, text: str, vehicle: Dict[str, Any]):
        """Extract powertrain specifications"""
        lines = text.split('\n')
        
        powertrain = {}
        in_powertrain_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'POWERTRAIN' in line:
                in_powertrain_section = True
                continue
            elif in_powertrain_section and ('DRY WEIGHT' in line or 'DIMENSIONS' in line):
                break
            
            if in_powertrain_section:
                if 'Drive clutch' in line:
                    powertrain['drive_clutch'] = line.split('Drive clutch')[-1].strip()
                if 'Driven clutch' in line:
                    powertrain['driven_clutch'] = line.split('Driven clutch')[-1].strip()
                if 'Drive sprocket pitch' in line:
                    powertrain['drive_sprocket_pitch'] = line.split('Drive sprocket pitch')[-1].strip()
        
        if powertrain:
            vehicle['powertrain'] = powertrain
    
    def _extract_weight_dimensions(self, text: str, vehicle: Dict[str, Any]):
        """Extract weight and dimensions"""
        lines = text.split('\n')
        
        dimensions = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Dry weight
            if 'Dry weight' in line:
                weight_match = re.search(r'(\d+)\s*kg', line)
                if weight_match:
                    dimensions['dry_weight_kg'] = int(weight_match.group(1))
            
            # Vehicle dimensions
            if 'Vehicle overall length' in line:
                length_match = re.search(r'(\d+(?:,\d+)?)\s*mm', line)
                if length_match:
                    dimensions['length_mm'] = int(length_match.group(1).replace(',', ''))
            
            if 'Vehicle overall width' in line:
                width_match = re.search(r'(\d+(?:,\d+)?)\s*mm', line)
                if width_match:
                    dimensions['width_mm'] = int(width_match.group(1).replace(',', ''))
            
            if 'Vehicle overall height' in line:
                height_match = re.search(r'(\d+(?:,\d+)?)\s*mm', line)
                if height_match:
                    dimensions['height_mm'] = int(height_match.group(1).replace(',', ''))
            
            if 'Ski stance' in line:
                ski_match = re.search(r'(\d+)\s*mm', line)
                if ski_match:
                    dimensions['ski_stance_mm'] = int(ski_match.group(1))
        
        if dimensions:
            vehicle['dimensions'] = dimensions
    
    def _extract_suspension_detailed(self, text: str, vehicle: Dict[str, Any]):
        """Extract detailed suspension specifications"""
        lines = text.split('\n')
        
        suspension = {}
        in_suspension_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'SUSPENSION' in line:
                in_suspension_section = True
                continue
            elif in_suspension_section and ('FEATURES' in line or 'ROTAX' in line):
                break
            
            if in_suspension_section:
                if 'Front suspension' in line:
                    suspension['front_suspension'] = line.split('Front suspension')[-1].strip()
                if 'Front shock' in line:
                    suspension['front_shock'] = line.split('Front shock')[-1].strip()
                if 'Front suspension travel' in line:
                    travel_match = re.search(r'(\d+)\s*mm', line)
                    if travel_match:
                        suspension['front_travel_mm'] = int(travel_match.group(1))
                
                if 'Rear suspension' in line and 'travel' not in line:
                    suspension['rear_suspension'] = line.split('Rear suspension')[-1].strip()
                if 'Center shock' in line:
                    suspension['center_shock'] = line.split('Center shock')[-1].strip()
                if 'Rear shock' in line:
                    suspension['rear_shock'] = line.split('Rear shock')[-1].strip()
                if 'Rear suspension travel' in line:
                    travel_match = re.search(r'(\d+)\s*mm', line)
                    if travel_match:
                        suspension['rear_travel_mm'] = int(travel_match.group(1))
        
        if suspension:
            vehicle['suspension'] = suspension
    
    def _extract_feature_details(self, text: str, vehicle: Dict[str, Any]):
        """Extract detailed features"""
        lines = text.split('\n')
        
        features = {}
        in_features_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'FEATURES' in line:
                in_features_section = True
                continue
            elif in_features_section and any(section in line for section in ['COLOR', 'TRACK', 'Available tracks']):
                break
            
            if in_features_section:
                # Extract key-value pairs
                feature_pairs = [
                    'Platform', 'Headlights', 'Skis', 'Seating', 'Handlebar', 
                    'Riser block height', 'Starter', 'Reverse', 'Brake system',
                    'Heated throttle lever/grips', 'Gauge type', 'Windshield',
                    'Runner', 'Bumpers'
                ]
                
                for feature in feature_pairs:
                    if feature in line:
                        features[feature.lower().replace(' ', '_')] = line.split(feature)[-1].strip()
        
        if features:
            vehicle['features'] = features
    
    def _extract_track_specifications(self, text: str, vehicle: Dict[str, Any]):
        """Extract track specifications"""
        lines = text.split('\n')
        
        tracks = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'Available tracks' in line or 'Length x width x profile' in line:
                # Look ahead for track specifications
                track_patterns = [
                    r'(\w+).*?(\d+)\s*x\s*(\d+)\s*x\s*(\d+\.?\d*)',  # Track name with dimensions
                    r'(\d+)\s*x\s*(\d+)\s*x\s*(\d+\.?\d*)'  # Just dimensions
                ]
                
                for pattern in track_patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        if len(match.groups()) == 4:  # With name
                            track_name = match.group(1)
                            length = int(match.group(2))
                            width = int(match.group(3))
                            profile = float(match.group(4))
                        else:  # Just dimensions
                            track_name = 'Standard'
                            length = int(match.group(1))
                            width = int(match.group(2))
                            profile = float(match.group(3))
                        
                        tracks[track_name] = {
                            'length_inches': length,
                            'width_inches': width,
                            'profile_inches': profile
                        }
        
        if tracks:
            vehicle['tracks'] = tracks
    
    def _extract_color_options(self, text: str, vehicle: Dict[str, Any]):
        """Extract color options for this vehicle"""
        lines = text.split('\n')
        
        colors = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'COLOR' in line:
                # Extract color names from the line
                color_names = [
                    'Terra Green', 'Scandi Blue', 'Magma Red', 'Monument Grey', 
                    'Timeless Black', 'Flare Yellow', 'Mineral Blue', 'Neo Yellow',
                    'White', 'Liquid Titanium', 'Catalyst Grey', 'Black'
                ]
                
                for color in color_names:
                    if color in line:
                        color_info = {
                            'name': color,
                            'availability': self._extract_availability_info(line)
                        }
                        colors.append(color_info)
        
        if colors:
            vehicle['colors'] = colors
    
    def _extract_marketing_content(self, text: str, vehicle: Dict[str, Any]):
        """Extract marketing content and messaging"""
        lines = text.split('\n')
        
        marketing = {
            'tagline': None,
            'key_benefits': [],
            'target_audience': None,
            'positioning': None,
            'description': None
        }
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Extract tagline (descriptive sentences)
            descriptive_words = ['ultimate', 'perfect', 'exceptional', 'precise', 'predictable', 'lightweight', 'agile']
            if len(line) > 30 and any(word in line.lower() for word in descriptive_words):
                if not marketing['tagline']:
                    marketing['tagline'] = line
            
            # Extract key benefits
            if line.startswith('•') or line.startswith('-'):
                marketing['key_benefits'].append(line[1:].strip())
            
            # Target audience
            audience_indicators = ['rider', 'experienced', 'beginner', 'professional', 'value-oriented']
            if any(audience in line.lower() for audience in audience_indicators):
                marketing['target_audience'] = line
        
        # Remove empty values
        marketing = {k: v for k, v in marketing.items() if v}
        
        if marketing:
            vehicle['marketing'] = marketing
    
    def _extract_whats_new(self, text: str, vehicle: Dict[str, Any]):
        """Extract 'What's New' features"""
        lines = text.split('\n')
        
        whats_new = []
        in_whats_new_section = False
        
        for line in lines:
            line = line.strip()
            
            if "WHAT'S NEW" in line or "W H AT ' S N E W" in line:
                in_whats_new_section = True
                continue
            
            if in_whats_new_section:
                if line.startswith('•') or line.startswith('-'):
                    whats_new.append(line[1:].strip())
                elif line.startswith('//') or 'PACKAGE' in line:
                    break
                elif line and not line.startswith('•') and len(line) > 10:
                    whats_new.append(line)
        
        if whats_new:
            vehicle['options']['whats_new'] = whats_new
    
    def _extract_spring_options(self, text: str, vehicle: Dict[str, Any]):
        """Extract spring ordering options"""
        lines = text.split('\n')
        
        spring_options = []
        in_spring_section = False
        
        for line in lines:
            line = line.strip()
            
            if "SPRING OPTIONS" in line or "S P R I N G O PTI O N S" in line:
                in_spring_section = True
                continue
            
            if in_spring_section:
                if line.startswith('•'):
                    spring_options.append(line[1:].strip())
                elif line.startswith('//') or len(line) < 5:
                    break
        
        if spring_options:
            vehicle['options']['spring_options'] = spring_options
    
    def _extract_package_highlights(self, text: str, vehicle: Dict[str, Any]):
        """Extract package highlights"""
        lines = text.split('\n')
        
        package_highlights = []
        in_package_section = False
        
        for line in lines:
            line = line.strip()
            
            if "PACKAGE HIGHLIGHTS" in line or "PA C K A G E H I G H LI G HTS" in line:
                in_package_section = True
                continue
            
            if in_package_section:
                if line.startswith('•'):
                    package_highlights.append(line[1:].strip())
                elif line.startswith('//') or 'ROTAX' in line:
                    break
        
        if package_highlights:
            vehicle['options']['package_highlights'] = package_highlights
    
    def _extract_comparative_data(self, text: str, results: Dict[str, Any]):
        """Extract comparative chart data"""
        lines = text.split('\n')
        
        comparative_data = {
            'categories': [],
            'comparison_matrix': {},
            'specifications_summary': {}
        }
        
        # This would need more sophisticated table parsing for the comparative chart
        # For now, capture key comparative information
        for line in lines:
            line = line.strip()
            if 'COMPARATIVE CHART' in line:
                comparative_data['title'] = line
            elif any(category in line for category in ['DEEP SNOW', 'CROSSOVER', 'TRAIL', 'UTILITY']):
                comparative_data['categories'].append(line)
        
        results['comparative_data'] = comparative_data
    
    def _extract_availability_info(self, line: str) -> str:
        """Extract availability information for colors/options"""
        if 'spring only' in line.lower():
            return 'spring_only'
        elif 'optional' in line.lower():
            return 'optional'
        else:
            return 'standard'
    
    def _finalize_extraction(self, results: Dict[str, Any]):
        """Post-process and clean up extracted data"""
        from datetime import datetime
        
        results['metadata']['extraction_timestamp'] = datetime.now().isoformat()
        results['metadata']['total_vehicles_extracted'] = len(results['vehicles'])
        results['metadata']['total_engines_extracted'] = len(results['engines'])
        
        # Add summary statistics
        results['summary'] = {
            'vehicle_families': list(set(v.get('model_family') for v in results['vehicles'] if v.get('model_family'))),
            'engine_types': list(results['engines'].keys()),
            'color_count': len(results['colors'].get('all_colors', [])),
            'pages_processed': results['metadata']['total_pages']
        }

def extract_ski_doo_catalog_data(pdf_path: Path) -> Dict[str, Any]:
    """Main function to extract comprehensive SKI-DOO catalog data"""
    parser = SkiDooCatalogParser()
    return parser.extract_all_catalog_data(pdf_path)

if __name__ == "__main__":
    pdf_path = Path(
        "../../../../AppData/Roaming/JetBrains/PyCharm2025.1/scratches/SKIDOO_2026 PRODUCT SPEC BOOK 1-35.pdf")
    if pdf_path.exists():
        results = extract_ski_doo_catalog_data(pdf_path)
        
        print(f"\n=== EXTRACTION SUMMARY ===")
        print(f"Total vehicles extracted: {results['metadata']['total_vehicles_extracted']}")
        print(f"Total engines extracted: {results['metadata']['total_engines_extracted']}")
        print(f"Vehicle families found: {', '.join(results['summary']['vehicle_families'])}")
        print(f"Total pages processed: {results['metadata']['total_pages']}")
        
        # Show first few vehicles
        print(f"\n=== FIRST 3 VEHICLES ===")
        for i, vehicle in enumerate(results['vehicles'][:3]):
            print(f"\nVehicle {i+1}: {vehicle.get('name', 'Unknown')}")
            print(f"  Model Family: {vehicle.get('model_family', 'N/A')}")
            print(f"  Page: {vehicle.get('page_number', 'N/A')}")
            if vehicle.get('specifications'):
                print(f"  Engine: {vehicle['specifications'].get('engine_type', 'N/A')}")
            if vehicle.get('marketing', {}).get('tagline'):
                print(f"  Tagline: {vehicle['marketing']['tagline']}")
    else:
        print(f"PDF file not found: {pdf_path}")