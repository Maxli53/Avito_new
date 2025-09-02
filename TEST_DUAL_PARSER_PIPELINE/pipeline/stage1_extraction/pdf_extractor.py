"""
PDF Extractor Implementation - Camelot Stream Method
Handles structured table extraction from Finnish price list PDFs
"""

import camelot
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import re
from datetime import datetime
import uuid

import sys
sys.path.append('..')
from .base_extractor import BaseExtractor
from core import ProductData, ExtractionError

logger = logging.getLogger(__name__)


class PDFExtractor(BaseExtractor):
    """
    PDF extractor for Finnish price list documents using Camelot Stream method
    Extracts structured table data and saves to raw_pricelist_data table
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize PDF extractor with Camelot configuration"""
        default_config = {
            'camelot_flavor': 'stream',  # Use stream method
            'camelot_pages': 'all',      # Extract all pages
            'parser_version': '2.0_camelot',
            'max_pages': 100,
            'db_path': 'dual_db.db'
        }
        
        if config:
            default_config.update(config)
            
        super().__init__(default_config)
    
    def extract(self, source: Path, **kwargs) -> List[ProductData]:
        """
        Extract product data from PDF using Camelot table extraction
        
        Args:
            source: Path to PDF file
            **kwargs: Additional extraction parameters
            
        Returns:
            List of extracted ProductData objects
        """
        self.stats.start_time = datetime.now()
        
        try:
            logger.info(f"Starting Camelot extraction from {source}")
            
            # Extract tables using Camelot Stream method
            tables = camelot.read_pdf(
                str(source),
                flavor=self.config['camelot_flavor'],
                pages=self.config['camelot_pages']
            )
            
            logger.info(f"Camelot found {len(tables)} tables")
            
            # Process all tables and extract product data
            all_products = []
            
            for table_idx, table in enumerate(tables):
                logger.info(f"Processing table {table_idx + 1}, accuracy: {table.accuracy:.2f}")
                
                products = self._process_table(table, source, table_idx + 1)
                all_products.extend(products)
            
            # Save to database
            self._save_to_database(all_products, source)
            
            self.stats.successful = len(all_products)
            self.stats.total_processed = len(all_products)
            
            logger.info(f"Successfully extracted {len(all_products)} products from {source}")
            return all_products
            
        except Exception as e:
            self.stats.failed += 1
            logger.error(f"PDF extraction failed: {e}")
            raise ExtractionError(f"Failed to extract from PDF: {str(e)}")
        
        finally:
            self.stats.end_time = datetime.now()
            if self.stats.start_time:
                self.stats.processing_time = (
                    self.stats.end_time - self.stats.start_time
                ).total_seconds()
    
    def extract_with_hooks(self, source: Path, **kwargs) -> List[ProductData]:
        """Extract with pre/post processing hooks"""
        return self.extract(source, **kwargs)
    
    def _process_table(self, table, source_path: Path, table_number: int) -> List[ProductData]:
        """Process a single table and extract product data"""
        products = []
        
        try:
            df = table.df
            logger.info(f"Table shape: {df.shape}")
            
            # Find header row (contains Finnish field names)
            header_row = self._find_header_row(df)
            if header_row is None:
                logger.warning("No header row found, skipping table")
                return products
            
            logger.info(f"Found headers at row {header_row}")
            
            # Extract column mapping
            column_mapping = self._extract_column_mapping(df, header_row)
            logger.info(f"Column mapping: {column_mapping}")
            
            # Process data rows (after header)
            data_start_row = header_row + 2  # Skip header and any separator rows
            
            current_product = {}
            
            for row_idx in range(data_start_row, len(df)):
                row_data = df.iloc[row_idx].tolist()
                
                # Check if this is a new product row (has model code)
                model_code = self._extract_model_code(row_data, column_mapping)
                
                if model_code:
                    # Save previous product if exists
                    if current_product:
                        product = self._create_product_data(current_product, source_path, table_number)
                        if product:
                            products.append(product)
                    
                    # Start new product
                    current_product = self._extract_product_data(row_data, column_mapping)
                    current_product['model_code'] = model_code
                    
                else:
                    # This might be a continuation row (for track specs, colors, etc.)
                    if current_product:
                        self._merge_continuation_row(current_product, row_data, column_mapping)
            
            # Don't forget the last product
            if current_product:
                product = self._create_product_data(current_product, source_path, table_number)
                if product:
                    products.append(product)
            
            logger.info(f"Extracted {len(products)} products from table {table_number}")
            return products
            
        except Exception as e:
            logger.error(f"Error processing table: {e}")
            return products
    
    def _find_header_row(self, df) -> Optional[int]:
        """Find row containing Finnish field headers"""
        finnish_headers = ['Tuotenro', 'Malli', 'Paketti', 'Moottori', 'Telamatto', 
                          'Käynnistin', 'Mittaristo', 'Kevätoptiot', 'Väri', 'Suositushinta']
        
        for row_idx in range(min(10, len(df))):  # Check first 10 rows
            row_text = ' '.join(str(cell) for cell in df.iloc[row_idx] if str(cell) != 'nan')
            
            found_headers = sum(1 for header in finnish_headers if header in row_text)
            if found_headers >= 5:  # Found most headers
                return row_idx
        
        return None
    
    def _extract_column_mapping(self, df, header_row: int) -> Dict[str, int]:
        """Extract column mapping from header row"""
        mapping = {}
        
        # Check both header row and the row below (might be split)
        header_rows = [header_row]
        if header_row + 1 < len(df):
            header_rows.append(header_row + 1)
        
        for col_idx in range(len(df.columns)):
            col_text = ""
            for h_row in header_rows:
                cell_value = df.iloc[h_row, col_idx]
                if str(cell_value) != 'nan':
                    col_text += str(cell_value) + " "
            
            col_text = col_text.strip()
            
            # Map Finnish headers to column indices
            if 'Tuotenro' in col_text or 'nro' in col_text:
                mapping['model_code'] = col_idx
            elif 'Malli' in col_text:
                mapping['malli'] = col_idx
            elif 'Paketti' in col_text:
                mapping['paketti'] = col_idx
            elif 'Moottori' in col_text:
                mapping['moottori'] = col_idx
            elif 'Telamatto' in col_text:
                mapping['telamatto'] = col_idx
            elif 'Käynnistin' in col_text:
                mapping['kaynnistin'] = col_idx
            elif 'Mittaristo' in col_text:
                mapping['mittaristo'] = col_idx
            elif 'Kevätoptiot' in col_text or 'optiot' in col_text:
                mapping['kevatoptiot'] = col_idx
            elif 'Väri' in col_text:
                mapping['vari'] = col_idx
            elif 'Suositushinta' in col_text or 'ALV' in col_text:
                mapping['price'] = col_idx
        
        return mapping
    
    def _extract_model_code(self, row_data: List, column_mapping: Dict[str, int]) -> Optional[str]:
        """Extract model code from row if present"""
        if 'model_code' not in column_mapping:
            return None
        
        model_code_col = column_mapping['model_code']
        if model_code_col < len(row_data):
            model_code = str(row_data[model_code_col]).strip()
            
            # Check if this looks like a model code (4 uppercase letters)
            if re.match(r'^[A-Z]{4}$', model_code):
                return model_code
        
        return None
    
    def _extract_product_data(self, row_data: List, column_mapping: Dict[str, int]) -> Dict[str, str]:
        """Extract all product data from a row"""
        product = {}
        
        for field, col_idx in column_mapping.items():
            if col_idx < len(row_data):
                value = str(row_data[col_idx]).strip()
                if value and value != 'nan':
                    product[field] = value
        
        return product
    
    def _merge_continuation_row(self, current_product: Dict, row_data: List, column_mapping: Dict[str, int]):
        """Merge continuation row data (for multi-row specifications)"""
        for field, col_idx in column_mapping.items():
            if col_idx < len(row_data):
                value = str(row_data[col_idx]).strip()
                if value and value != 'nan':
                    if field in current_product:
                        # Append to existing value
                        current_product[field] += " " + value
                    else:
                        # Set new value
                        current_product[field] = value
    
    def _create_product_data(self, product_dict: Dict, source_path: Path, table_number: int) -> Optional[ProductData]:
        """Create ProductData object from extracted dictionary"""
        try:
            # Parse price
            price = 0.0
            if 'price' in product_dict:
                price_str = re.sub(r'[^\d,.]', '', product_dict['price'])
                price_str = price_str.replace(',', '.')
                try:
                    price = float(price_str)
                except:
                    logger.warning(f"Could not parse price: {product_dict.get('price')}")
            
            # Create ProductData object
            product = ProductData(
                model_code=product_dict.get('model_code', ''),
                brand='SKI-DOO',  # Default brand
                year=2026,  # Default year
                malli=product_dict.get('malli', '').strip(),
                paketti=product_dict.get('paketti', '').strip(),
                moottori=product_dict.get('moottori', '').strip(),
                telamatto=product_dict.get('telamatto', '').strip(),
                kaynnistin=product_dict.get('kaynnistin', '').strip(),
                mittaristo=product_dict.get('mittaristo', '').strip(),
                kevatoptiot=product_dict.get('kevatoptiot', '').strip(),
                vari=product_dict.get('vari', '').strip(),
                price=price,
                currency='EUR',
                market='FINLAND',
                extraction_metadata={
                    'extractor': 'PDFExtractor_Camelot',
                    'extraction_method': 'camelot_stream',
                    'source_file': str(source_path),
                    'source_page': table_number,
                    'extracted_at': datetime.now().isoformat(),
                    'parser_version': self.config['parser_version']
                }
            )
            
            return product
            
        except Exception as e:
            logger.error(f"Error creating product data: {e}")
            return None
    
    def _save_to_database(self, products: List[ProductData], source_path: Path):
        """Save extracted products to raw_pricelist_data table"""
        if not products:
            return
        
        try:
            db_path = self.config['db_path']
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            price_list_id = f"{source_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            for product in products:
                # Generate unique ID
                record_id = str(uuid.uuid4())
                
                # Create normalized fields
                normalized_model = self._normalize_text(product.malli or '')
                normalized_package = self._normalize_text(product.paketti or '')
                normalized_engine = self._normalize_text(product.moottori or '')
                normalized_telamatto = self._normalize_text(product.telamatto or '')
                normalized_mittaristo = self._normalize_text(product.mittaristo or '')
                
                cursor.execute("""
                    INSERT INTO raw_pricelist_data (
                        id, model_code, malli, paketti, moottori, telamatto, 
                        kaynnistin, mittaristo, kevatoptiot, vari, price, currency,
                        price_list_id, brand, model_year, market, source_catalog_page,
                        extraction_timestamp, extraction_method, parser_version,
                        normalized_model_name, normalized_package_name, normalized_engine_spec,
                        normalized_telamatto, normalized_mittaristo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_id,
                    product.model_code,
                    product.malli,
                    product.paketti,
                    product.moottori,
                    product.telamatto,
                    product.kaynnistin,
                    product.mittaristo,
                    product.kevatoptiot,
                    product.vari,
                    product.price,
                    product.currency,
                    price_list_id,
                    product.brand,
                    product.year,
                    product.market,
                    product.extraction_metadata.get('source_page'),
                    datetime.now().isoformat(),
                    'camelot_stream',
                    self.config['parser_version'],
                    normalized_model,
                    normalized_package,
                    normalized_engine,
                    normalized_telamatto,
                    normalized_mittaristo
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Saved {len(products)} products to database")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            raise
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching purposes"""
        if not text:
            return ""
        
        # Convert to lowercase, remove extra spaces, special chars
        normalized = re.sub(r'[^\w\s-]', ' ', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return {
            'total_processed': self.stats.total_processed,
            'successful': self.stats.successful,
            'failed': self.stats.failed,
            'success_rate': self.stats.success_rate,
            'processing_time': self.stats.processing_time,
            'stage': self.stats.stage.value if hasattr(self.stats.stage, 'value') else str(self.stats.stage),
            'extraction_method': 'camelot_stream'
        }