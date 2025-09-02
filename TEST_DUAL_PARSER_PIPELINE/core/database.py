"""
Database Manager for Avito Pipeline
Provides unified database access and management for all pipeline stages
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
from contextlib import contextmanager

from .models import ProductData, CatalogData, ValidationResult, MatchResult, PipelineStats
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Centralized database manager for the Avito pipeline
    
    Handles all database operations including:
    - Product data storage and retrieval
    - Catalog data management  
    - Validation results tracking
    - Match results storage
    - Pipeline statistics
    """
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.logger = logger
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Ensure database and tables exist"""
        try:
            with self.get_connection() as conn:
                # Create main tables if they don't exist
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS price_entries (
                        id TEXT PRIMARY KEY,
                        price_list_id TEXT,
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
                        market TEXT DEFAULT 'FINLAND',
                        brand TEXT NOT NULL,
                        model_year INTEGER,
                        catalog_lookup_key TEXT,
                        status TEXT DEFAULT 'extracted',
                        extraction_timestamp TEXT,
                        extraction_method TEXT,
                        parser_version TEXT,
                        source_catalog_page INTEGER,
                        normalized_model_name TEXT,
                        normalized_package_name TEXT,
                        normalized_engine_spec TEXT,
                        matching_method TEXT,
                        matching_confidence REAL,
                        confidence_description TEXT,
                        validation_status TEXT,
                        validation_errors TEXT,
                        validation_warnings TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS catalog_entries (
                        id TEXT PRIMARY KEY,
                        model_family TEXT NOT NULL,
                        brand TEXT NOT NULL,
                        year INTEGER,
                        specifications TEXT,
                        features TEXT,
                        available_engines TEXT,
                        available_tracks TEXT,
                        marketing_data TEXT,
                        images TEXT,
                        extraction_method TEXT,
                        source_catalog_name TEXT,
                        price_list_model_code TEXT,
                        matching_method TEXT,
                        matching_confidence REAL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS validation_results (
                        id TEXT PRIMARY KEY,
                        product_id TEXT NOT NULL,
                        validation_stage TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        errors TEXT,
                        warnings TEXT,
                        suggestions TEXT,
                        confidence_score REAL,
                        validation_metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (product_id) REFERENCES price_entries(id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS match_results (
                        id TEXT PRIMARY KEY,
                        product_id TEXT NOT NULL,
                        catalog_id TEXT,
                        match_type TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        matched BOOLEAN NOT NULL,
                        match_details TEXT,
                        processing_time REAL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (product_id) REFERENCES price_entries(id),
                        FOREIGN KEY (catalog_id) REFERENCES catalog_entries(id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS pipeline_stats (
                        id TEXT PRIMARY KEY,
                        stage TEXT NOT NULL,
                        total_processed INTEGER DEFAULT 0,
                        successful INTEGER DEFAULT 0,
                        failed INTEGER DEFAULT 0,
                        processing_time REAL,
                        start_time TEXT,
                        end_time TEXT,
                        metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_price_entries_model_code ON price_entries(model_code);
                    CREATE INDEX IF NOT EXISTS idx_price_entries_brand_year ON price_entries(brand, model_year);
                    CREATE INDEX IF NOT EXISTS idx_catalog_entries_model_family ON catalog_entries(model_family);
                    CREATE INDEX IF NOT EXISTS idx_validation_results_product_id ON validation_results(product_id);
                    CREATE INDEX IF NOT EXISTS idx_match_results_product_id ON match_results(product_id);
                """)
                
                self.logger.info(f"Database initialized at {self.db_path}")
                
        except Exception as e:
            raise DatabaseError(
                message="Failed to initialize database",
                database_path=str(self.db_path),
                original_exception=e
            )
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise DatabaseError(
                message="Database connection error",
                database_path=str(self.db_path),
                original_exception=e
            )
        finally:
            if conn:
                conn.close()
    
    def save_product_data(self, products: List[ProductData], clear_existing: bool = False) -> int:
        """
        Save product data to database
        
        Args:
            products: List of ProductData objects to save
            clear_existing: Whether to clear existing data first
            
        Returns:
            Number of products saved
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if clear_existing:
                    cursor.execute("DELETE FROM price_entries")
                    self.logger.info("Cleared existing price entries")
                
                saved_count = 0
                for product in products:
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO price_entries (
                                id, model_code, brand, model_year, malli, paketti, moottori,
                                telamatto, kaynnistin, mittaristo, vari, price, currency,
                                market, extraction_timestamp, extraction_method,
                                normalized_model_name, normalized_package_name, 
                                normalized_engine_spec, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            f"{product.brand}_{product.model_code}_{product.year}",
                            product.model_code,
                            product.brand,
                            product.year,
                            product.malli,
                            product.paketti,
                            product.moottori,
                            product.telamatto,
                            product.kaynnistin,
                            product.mittaristo,
                            product.vari,
                            product.price,
                            product.currency,
                            product.market,
                            datetime.now().isoformat(),
                            product.extraction_metadata.get('method', 'unknown'),
                            product.malli.upper() if product.malli else None,
                            product.paketti.upper() if product.paketti else None,
                            product.moottori.upper() if product.moottori else None,
                            datetime.now().isoformat()
                        ))
                        saved_count += 1
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to save product {product.model_code}: {e}")
                
                conn.commit()
                self.logger.info(f"Saved {saved_count} products to database")
                return saved_count
                
        except Exception as e:
            raise DatabaseError(
                message="Failed to save product data",
                table_name="price_entries",
                original_exception=e
            )
    
    def load_product_data(
        self, 
        brand: Optional[str] = None, 
        year: Optional[int] = None,
        extraction_method: Optional[str] = None
    ) -> List[ProductData]:
        """
        Load product data from database
        
        Args:
            brand: Filter by brand
            year: Filter by model year
            extraction_method: Filter by extraction method
            
        Returns:
            List of ProductData objects
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with filters
                query = "SELECT * FROM price_entries WHERE 1=1"
                params = []
                
                if brand:
                    query += " AND brand = ?"
                    params.append(brand)
                
                if year:
                    query += " AND model_year = ?"
                    params.append(year)
                
                if extraction_method:
                    query += " AND extraction_method = ?"
                    params.append(extraction_method)
                
                query += " ORDER BY brand, model_year, model_code"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                products = []
                for row in rows:
                    try:
                        product = ProductData(
                            model_code=row['model_code'],
                            brand=row['brand'],
                            year=row['model_year'],
                            malli=row['malli'],
                            paketti=row['paketti'],
                            moottori=row['moottori'],
                            telamatto=row['telamatto'],
                            kaynnistin=row['kaynnistin'],
                            mittaristo=row['mittaristo'],
                            vari=row['vari'],
                            price=row['price'],
                            currency=row['currency'] or 'EUR',
                            market=row['market'] or 'FINLAND'
                        )
                        
                        # Add extraction metadata
                        product.extraction_metadata = {
                            'method': row['extraction_method'],
                            'timestamp': row['extraction_timestamp'],
                            'source_page': row['source_catalog_page']
                        }
                        
                        products.append(product)
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to load product {row['model_code']}: {e}")
                
                self.logger.info(f"Loaded {len(products)} products from database")
                return products
                
        except Exception as e:
            raise DatabaseError(
                message="Failed to load product data",
                table_name="price_entries",
                original_exception=e
            )
    
    def save_validation_result(self, product_id: str, result: ValidationResult, stage: str = "internal") -> bool:
        """Save validation result to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO validation_results (
                        id, product_id, validation_stage, success, errors, warnings,
                        suggestions, confidence_score, validation_metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"{product_id}_{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    product_id,
                    stage,
                    result.success,
                    json.dumps(result.errors),
                    json.dumps(result.warnings),
                    json.dumps(result.suggestions),
                    result.confidence,
                    json.dumps(result.metadata),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save validation result: {e}")
            return False
    
    def save_match_result(self, result: MatchResult) -> bool:
        """Save match result to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                product_id = f"{result.product_data.brand}_{result.product_data.model_code}_{result.product_data.year}"
                catalog_id = None
                if result.catalog_data:
                    catalog_id = f"{result.catalog_data.model_family}_{result.product_data.brand}_{result.product_data.year}"
                
                cursor.execute("""
                    INSERT INTO match_results (
                        id, product_id, catalog_id, match_type, confidence_score,
                        matched, match_details, processing_time, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"{product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    product_id,
                    catalog_id,
                    result.match_type.value,
                    result.confidence_score,
                    result.matched,
                    json.dumps(result.match_details),
                    result.processing_time,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save match result: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Product statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_products,
                        COUNT(DISTINCT brand) as unique_brands,
                        COUNT(DISTINCT model_year) as unique_years,
                        COUNT(DISTINCT model_code) as unique_models
                    FROM price_entries
                """)
                product_stats = cursor.fetchone()
                stats['products'] = dict(product_stats)
                
                # Brand breakdown
                cursor.execute("""
                    SELECT brand, model_year, COUNT(*) as count
                    FROM price_entries
                    GROUP BY brand, model_year
                    ORDER BY brand, model_year
                """)
                brand_stats = cursor.fetchall()
                stats['by_brand_year'] = [dict(row) for row in brand_stats]
                
                # Validation statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_validations,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_validations,
                        AVG(confidence_score) as avg_confidence
                    FROM validation_results
                """)
                validation_stats = cursor.fetchone()
                if validation_stats and validation_stats['total_validations'] > 0:
                    stats['validation'] = dict(validation_stats)
                
                # Match statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_matches,
                        SUM(CASE WHEN matched = 1 THEN 1 ELSE 0 END) as successful_matches,
                        AVG(confidence_score) as avg_match_confidence
                    FROM match_results
                """)
                match_stats = cursor.fetchone()
                if match_stats and match_stats['total_matches'] > 0:
                    stats['matching'] = dict(match_stats)
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def cleanup_old_data(self, days_old: int = 30) -> Dict[str, int]:
        """Clean up old data from database"""
        try:
            cutoff_date = datetime.now().replace(day=datetime.now().day - days_old)
            cutoff_str = cutoff_date.isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cleanup_stats = {}
                
                # Clean up old validation results
                cursor.execute("DELETE FROM validation_results WHERE created_at < ?", (cutoff_str,))
                cleanup_stats['validation_results'] = cursor.rowcount
                
                # Clean up old match results
                cursor.execute("DELETE FROM match_results WHERE created_at < ?", (cutoff_str,))
                cleanup_stats['match_results'] = cursor.rowcount
                
                # Clean up old pipeline stats
                cursor.execute("DELETE FROM pipeline_stats WHERE created_at < ?", (cutoff_str,))
                cleanup_stats['pipeline_stats'] = cursor.rowcount
                
                conn.commit()
                
                total_cleaned = sum(cleanup_stats.values())
                self.logger.info(f"Cleaned up {total_cleaned} old records")
                
                return cleanup_stats
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            return {}