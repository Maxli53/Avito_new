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
            'camelot_flavor': 'stream',
            'camelot_pages': 'all',
            'parser_version': '2.0_camelot_direct',
            'db_path': 'TEST_DUAL_PARSER_PIPELINE/dual_db.db'
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
            
            # Direct extraction to raw_pricelist_data table
            total_products = self._extract_and_save_raw_data(tables, source)
            
            # Parse raw data into clean products
            parsed_products = self._parse_raw_data()
            
            self.stats.successful = len(parsed_products)
            self.stats.total_processed = total_products
            
            logger.info(f"Successfully extracted {total_products} raw records and parsed {len(parsed_products)} products")
            return parsed_products
            
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
    
    def _extract_and_save_raw_data(self, tables, source: Path) -> int:
        """Extract raw data from all tables and save to database - direct row-to-record mapping"""
        
        db_path = self.config['db_path']
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        price_list_id = f"{source.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        total_products = 0
        
        # Process each table
        for table_idx, table in enumerate(tables):
            df = table.df
            logger.info(f"Processing table {table_idx + 1} (shape: {df.shape}, accuracy: {table.accuracy:.2f})")
            
            # Find header row
            header_row = None
            for row_idx in range(min(10, len(df))):
                row_text = ' '.join(str(cell) for cell in df.iloc[row_idx] if str(cell) != 'nan')
                if 'Malli' in row_text and 'Paketti' in row_text:
                    header_row = row_idx
                    break
            
            if header_row is None:
                logger.warning(f"No header found in table {table_idx + 1}, skipping")
                continue
            
            logger.info(f"Header found at row {header_row}")
            
            # Extract column mapping
            column_mapping = {}
            for col_idx in range(len(df.columns)):
                col_text = ""
                # Check header row and next row
                for h_row in [header_row, header_row + 1]:
                    if h_row < len(df):
                        cell_value = df.iloc[h_row, col_idx]
                        if str(cell_value) != 'nan':
                            col_text += str(cell_value) + " "
                
                col_text = col_text.strip()
                
                # Map columns
                if 'Tuotenro' in col_text or 'nro' in col_text:
                    column_mapping['model_code'] = col_idx
                elif 'Malli' in col_text:
                    column_mapping['malli'] = col_idx
                elif 'Paketti' in col_text:
                    column_mapping['paketti'] = col_idx
                elif 'Moottori' in col_text:
                    column_mapping['moottori'] = col_idx
                elif 'Telamatto' in col_text:
                    column_mapping['telamatto'] = col_idx
                elif 'Käynnistin' in col_text:
                    column_mapping['kaynnistin'] = col_idx
                elif 'Mittaristo' in col_text:
                    column_mapping['mittaristo'] = col_idx
                elif 'Kevätoptiot' in col_text or 'optiot' in col_text:
                    column_mapping['kevatoptiot'] = col_idx
                elif 'Väri' in col_text:
                    column_mapping['vari'] = col_idx
                elif 'Suositushinta' in col_text or 'ALV' in col_text:
                    column_mapping['price'] = col_idx
            
            logger.info(f"Column mapping: {column_mapping}")
            
            # Extract products - simple row-to-record mapping
            table_products = 0
            
            for row_idx in range(header_row + 2, len(df)):
                row_data = df.iloc[row_idx].tolist()
                
                # Extract all fields from this row using column mapping
                product = {}
                for field, col_idx in column_mapping.items():
                    if col_idx < len(row_data):
                        value = str(row_data[col_idx]).strip()
                        if value and value != 'nan':
                            product[field] = value
                
                # Save each row as a separate record
                if product:  # Only save if we extracted any data
                    self._save_raw_product_to_db(cursor, product, price_list_id, table_idx + 1)
                    table_products += 1
            
            logger.info(f"Products extracted from table {table_idx + 1}: {table_products}")
            total_products += table_products
        
        # Commit and close
        conn.commit()
        conn.close()
        
        logger.info(f"Total raw records saved: {total_products}")
        return total_products
    
    def _save_raw_product_to_db(self, cursor, product_dict: Dict[str, str], price_list_id: str, page_num: int):
        """Save raw product record to database"""
        
        # Parse price
        price = 0.0
        if 'price' in product_dict:
            # Extract only digits, commas, and dots
            price_str = re.sub(r'[^\d,.]', '', product_dict['price'])
            # Replace comma with dot for decimal separator
            price_str = price_str.replace(',', '.')
            try:
                price = float(price_str)
                if price <= 0:
                    logger.warning(f"Invalid price for {product_dict.get('model_code', 'UNKNOWN')}: {price}")
            except:
                logger.warning(f"Price parsing failed for {product_dict.get('model_code', 'UNKNOWN')}: {product_dict.get('price', 'N/A')}")
        
        # Normalize fields
        def normalize(text):
            if not text:
                return ""
            return re.sub(r'[^\w\s-]', ' ', text.lower().strip())
        
        cursor.execute("""
            INSERT INTO raw_pricelist_data (
                model_code, malli, paketti, moottori, telamatto, 
                kaynnistin, mittaristo, kevatoptiot, vari, price, currency,
                price_list_id, brand, model_year, market, source_catalog_page,
                extraction_timestamp, extraction_method, parser_version,
                normalized_model_name, normalized_package_name, normalized_engine_spec,
                normalized_telamatto, normalized_mittaristo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_dict.get('model_code', ''),
            product_dict.get('malli', ''),
            product_dict.get('paketti', ''),
            product_dict.get('moottori', ''),
            product_dict.get('telamatto', ''),
            product_dict.get('kaynnistin', ''),
            product_dict.get('mittaristo', ''),
            product_dict.get('kevatoptiot', ''),
            product_dict.get('vari', ''),
            price,
            'EUR',
            price_list_id,
            'SKI-DOO',
            2026,
            'FINLAND',
            page_num,
            datetime.now().isoformat(),
            'camelot_stream_direct',
            self.config['parser_version'],
            normalize(product_dict.get('malli', '')),
            normalize(product_dict.get('paketti', '')),
            normalize(product_dict.get('moottori', '')),
            normalize(product_dict.get('telamatto', '')),
            normalize(product_dict.get('mittaristo', ''))
        ))
    
    def _parse_raw_data(self) -> List[ProductData]:
        """Parse raw extracted data into clean products"""
        
        logger.info("Parsing raw data into clean products")
        
        try:
            db_path = self.config['db_path']
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create raw_pricelist_data_parsed table
            cursor.execute("DROP TABLE IF EXISTS raw_pricelist_data_parsed")
            cursor.execute("""
                CREATE TABLE raw_pricelist_data_parsed (
                    model_code TEXT NOT NULL,
                    malli TEXT,
                    paketti TEXT,
                    moottori TEXT,
                    telamatto TEXT,
                    kaynnistin TEXT,
                    mittaristo TEXT,
                    kevatoptiot TEXT,
                    vari TEXT,
                    price REAL,
                    currency TEXT DEFAULT 'EUR',
                    price_list_id TEXT,
                    brand TEXT NOT NULL,
                    model_year INTEGER,
                    market TEXT DEFAULT 'FINLAND',
                    source_catalog_page INTEGER,
                    extraction_timestamp TEXT,
                    extraction_method TEXT,
                    parser_version TEXT,
                    normalized_model_name TEXT,
                    normalized_package_name TEXT,
                    normalized_engine_spec TEXT,
                    normalized_telamatto TEXT,
                    normalized_mittaristo TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Read all raw data ordered by page and creation time
            cursor.execute("""
                SELECT * FROM raw_pricelist_data 
                ORDER BY source_catalog_page, created_at
            """)
            
            raw_records = cursor.fetchall()
            column_names = [description[0] for description in cursor.description]
            
            logger.info(f"Processing {len(raw_records)} raw records...")
            
            current_product = None
            parsed_count = 0
            
            for record in raw_records:
                record_dict = dict(zip(column_names, record))
                model_code = record_dict.get('model_code', '').strip()
                
                # Check if this is a new product (4-character model code)
                if model_code and len(model_code) == 4:
                    # Save previous product if exists
                    if current_product:
                        self._save_parsed_product(cursor, current_product)
                        parsed_count += 1
                    
                    # Start new product
                    current_product = record_dict.copy()
                    logger.debug(f"New product: {model_code}")
                
                elif current_product and model_code and not self._is_header_row(model_code):
                    # This is a continuation row with data - merge it
                    logger.debug(f"Merging continuation: {model_code}")
                    self._merge_continuation_data(current_product, record_dict)
                
                elif current_product and self._has_useful_data(record_dict):
                    # Row with no model code but has useful data - merge it
                    logger.debug(f"Merging no-code row")
                    self._merge_continuation_data(current_product, record_dict)
            
            # Don't forget the last product
            if current_product:
                self._save_parsed_product(cursor, current_product)
                parsed_count += 1
            
            conn.commit()
            
            # Convert to ProductData objects
            cursor.execute("SELECT * FROM raw_pricelist_data_parsed ORDER BY model_code")
            parsed_records = cursor.fetchall()
            column_names = [description[0] for description in cursor.description]
            
            products = []
            for record in parsed_records:
                record_dict = dict(zip(column_names, record))
                
                product = ProductData(
                    model_code=record_dict.get('model_code', ''),
                    brand=record_dict.get('brand', 'SKI-DOO'),
                    year=record_dict.get('model_year', 2026),
                    malli=record_dict.get('malli', ''),
                    paketti=record_dict.get('paketti', ''),
                    moottori=record_dict.get('moottori', ''),
                    telamatto=record_dict.get('telamatto', ''),
                    kaynnistin=record_dict.get('kaynnistin', ''),
                    mittaristo=record_dict.get('mittaristo', ''),
                    kevatoptiot=record_dict.get('kevatoptiot', ''),
                    vari=record_dict.get('vari', ''),
                    price=record_dict.get('price', 0.0),
                    currency=record_dict.get('currency', 'EUR'),
                    market=record_dict.get('market', 'FINLAND'),
                    extraction_metadata={
                        'extractor': 'PDFExtractor',
                        'extraction_method': record_dict.get('extraction_method', 'camelot_stream'),
                        'price_list_id': record_dict.get('price_list_id', ''),
                        'source_page': record_dict.get('source_catalog_page', 0),
                        'extracted_at': record_dict.get('extraction_timestamp', ''),
                        'parser_version': record_dict.get('parser_version', '')
                    }
                )
                products.append(product)
            
            conn.close()
            
            logger.info(f"PARSING COMPLETED! Parsed products: {parsed_count}")
            return products
            
        except Exception as e:
            logger.error(f"PARSING ERROR: {e}")
            raise
    
    def _is_header_row(self, model_code: str) -> bool:
        """Check if this is a header/category row"""
        headers = ['Mid-sized', 'Trail', 'Deep Snow', 'Utility', 'Crossover']
        return model_code in headers
    
    def _has_useful_data(self, record_dict: Dict[str, Any]) -> bool:
        """Check if record has any useful data to merge"""
        useful_fields = ['malli', 'paketti', 'moottori', 'telamatto', 'kaynnistin', 'mittaristo', 'vari']
        return any(record_dict.get(field) for field in useful_fields)
    
    def _merge_continuation_data(self, current_product: Dict[str, Any], new_record: Dict[str, Any]):
        """Merge continuation row data into current product"""
        merge_fields = ['malli', 'paketti', 'moottori', 'telamatto', 'kaynnistin', 'mittaristo', 'kevatoptiot', 'vari']
        
        for field in merge_fields:
            new_value = str(new_record.get(field, '')).strip()
            if new_value and new_value != 'nan':
                current_value = str(current_product.get(field, '')).strip()
                if current_value and current_value != new_value:
                    # Append new value
                    current_product[field] = f"{current_value} {new_value}"
                elif not current_value:
                    # Set new value
                    current_product[field] = new_value
    
    def _save_parsed_product(self, cursor, product: Dict[str, Any]):
        """Save parsed product to database"""
        
        def normalize(text):
            if not text:
                return ""
            return re.sub(r'[^\w\s-]', ' ', str(text).lower().strip())
        
        cursor.execute("""
            INSERT INTO raw_pricelist_data_parsed (
                model_code, malli, paketti, moottori, telamatto, 
                kaynnistin, mittaristo, kevatoptiot, vari, price, currency,
                price_list_id, brand, model_year, market, source_catalog_page,
                extraction_timestamp, extraction_method, parser_version,
                normalized_model_name, normalized_package_name, normalized_engine_spec,
                normalized_telamatto, normalized_mittaristo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product.get('model_code', ''),
            product.get('malli', ''),
            product.get('paketti', ''),
            product.get('moottori', ''),
            product.get('telamatto', ''),
            product.get('kaynnistin', ''),
            product.get('mittaristo', ''),
            product.get('kevatoptiot', ''),
            product.get('vari', ''),
            product.get('price', 0),
            'EUR',
            product.get('price_list_id', ''),
            product.get('brand', 'SKI-DOO'),
            product.get('model_year', 2026),
            'FINLAND',
            product.get('source_catalog_page', 0),
            datetime.now().isoformat(),
            'camelot_parsed',
            '2.0_parsed',
            normalize(product.get('malli', '')),
            normalize(product.get('paketti', '')),
            normalize(product.get('moottori', '')),
            normalize(product.get('telamatto', '')),
            normalize(product.get('mittaristo', ''))
        ))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return {
            'total_processed': self.stats.total_processed,
            'successful': self.stats.successful,
            'failed': self.stats.failed,
            'success_rate': self.stats.success_rate,
            'processing_time': self.stats.processing_time,
            'stage': self.stats.stage.value if hasattr(self.stats.stage, 'value') else str(self.stats.stage),
            'extraction_method': 'camelot_stream_direct'
        }