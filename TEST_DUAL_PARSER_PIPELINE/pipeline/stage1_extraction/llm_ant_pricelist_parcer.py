#!/usr/bin/env python3
"""
Complete Price List Extractor System

This system processes Finnish snowmobile price list PDFs and extracts product information
to a SQLite database. It uses Claude Sonnet 4's native PDF processing capabilities with
multiple fallback extraction methods for robustness.

Key Features:
- Claude Sonnet 4 native PDF processing (primary method)
- Camelot table extraction fallback
- Page-by-page text extraction fallback
- Direct database storage (no JSON intermediaries)
- Finnish header mapping to database schema
- Comprehensive error handling and logging
- Processing status tracking

Architecture:
- Composition-based design with clear separation of concerns
- DatabaseManager: handles all SQLite operations
- ClaudeAPIManager: manages Anthropic API calls
- CamelotTableExtractor: fallback table extraction
- PDFProcessor: basic PDF operations
- PriceListExtractor: main orchestrator

Author: Your Team
Version: Production-ready
Dependencies: anthropic, camelot-py[cv], pymupdf, pandas, python-dotenv
"""

import os
import json
import base64
import time
import sqlite3
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
# Expects ANTHROPIC_API_KEY to be set
load_dotenv()


@dataclass
class ExtractionStats:
    """
    Data class for tracking extraction operation statistics.

    Used for monitoring performance, debugging, and reporting on
    extraction runs. All counters start at zero.

    Attributes:
        total_articles: Total number of articles processed
        new_articles: Number of newly created articles
        updated_articles: Number of articles that were updated
        failed_articles: Number of articles that failed processing
        tokens_used: Estimated Claude API tokens consumed
        pages_processed: Total PDF pages processed
        pdfs_processed: Total PDF files processed
    """
    total_articles: int = 0
    new_articles: int = 0
    updated_articles: int = 0
    failed_articles: int = 0
    tokens_used: int = 0
    pages_processed: int = 0
    pdfs_processed: int = 0


@dataclass
class ExtractionConfig:
    """
    Configuration settings for the extraction system.

    Centralizes file paths and database settings to make the system
    more configurable and easier to deploy in different environments.

    Attributes:
        pdf_directory: Path to directory containing price list PDFs
        database_file: SQLite database file path for storing extracted data
    """
    pdf_directory: str = "docs/Price_lists"
    database_file: str = "dual_db.db"


class DatabaseManager:
    """
    Handles all database operations for price list data storage and retrieval.

    This class encapsulates all SQLite operations, providing a clean interface
    for the extraction system. It manages schema creation, data insertion,
    querying, and statistics generation.

    The database schema matches the final_pricelist table structure expected
    by the business logic, with proper indexing for performance.
    """

    def __init__(self, db_file: str = "price_extraction.db"):
        """
        Initialize database manager and create schema if needed.

        Args:
            db_file: Path to SQLite database file
        """
        self.db_file = db_file
        self.init_database()

    def init_database(self):
        """
        Create database tables and indexes if they don't exist.

        Creates two main tables:
        1. final_pricelist: Stores extracted product data
        2. processing_log: Tracks which PDFs have been processed

        Also creates performance indexes on commonly queried columns.

        Raises:
            Exception: If database creation fails
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                # Create final_pricelist table matching exact business schema
                # This table stores all extracted snowmobile product information
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS final_pricelist
                               (
                                   id
                                   INTEGER
                                   PRIMARY
                                   KEY
                                   AUTOINCREMENT,
                                   brand
                                   TEXT
                                   NOT
                                   NULL, -- SKI-DOO, LYNX
                                   year
                                   INTEGER
                                   NOT
                                   NULL, -- Model year (2024, 2025, etc.)
                                   model_code
                                   TEXT
                                   NOT
                                   NULL, -- Product SKU/code from Tuotenro
                                   model_name
                                   TEXT, -- Model name from Malli
                                   package
                                   TEXT, -- Variant package from Paketti
                                   engine
                                   TEXT, -- Engine spec from Moottori
                                   track
                                   TEXT, -- Track spec from Telamatto
                                   starter_type
                                   TEXT, -- Starter type from Käynnistin
                                   gauge_type
                                   TEXT, -- Display type from Mittaristo
                                   spring_options
                                   TEXT, -- Spring config from Kevätoptiot
                                   color
                                   TEXT, -- Color from Väri
                                   price_eur
                                   REAL, -- Price from Suositushinta
                                   source_file
                                   TEXT, -- Source PDF filename
                                   created_at
                                   TIMESTAMP
                                   DEFAULT
                                   CURRENT_TIMESTAMP,
                                   UNIQUE
                               (
                                   brand,
                                   year,
                                   model_code
                               ) -- Prevent duplicates
                                   )
                               ''')

                # Create processing log to track which PDFs have been processed
                # Prevents reprocessing and enables incremental updates
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS processing_log
                               (
                                   id
                                   INTEGER
                                   PRIMARY
                                   KEY
                                   AUTOINCREMENT,
                                   pdf_filename
                                   TEXT
                                   UNIQUE,     -- PDF filename (unique constraint)
                                   brand
                                   TEXT,       -- Brand extracted from filename
                                   year
                                   INTEGER,    -- Year extracted from filename
                                   articles_count
                                   INTEGER,    -- Number of articles extracted
                                   extraction_method
                                   TEXT,       -- Method used (claude_native, etc.)
                                   processed_at
                                   TIMESTAMP
                                   DEFAULT
                                   CURRENT_TIMESTAMP,
                                   status
                                   TEXT
                                   DEFAULT
                                   'completed' -- Processing status
                               )
                               ''')

                # Create performance indexes for common queries
                # These speed up lookups by brand/year and model searches
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_brand_year ON final_pricelist(brand, year)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_model_code ON final_pricelist(model_code)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_model_name ON final_pricelist(model_name)')

                conn.commit()
                print(f"Database initialized: {self.db_file}")

        except Exception as e:
            print(f"Database initialization error: {e}")
            raise

    def get_article_by_model_code(self, model_code: str, brand: str, year: str) -> Optional[Dict]:
        """
        Retrieve existing article by model code, brand, and year.

        Used to check if an article already exists before insertion
        and to support upsert operations.

        Args:
            model_code: Product SKU/code
            brand: Product brand (SKI-DOO, LYNX)
            year: Model year

        Returns:
            Dictionary with article data if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Use Row factory to get dictionary-like results
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('''
                               SELECT *
                               FROM final_pricelist
                               WHERE model_code = ? AND brand = ? AND year = ?
                               ''', (model_code, brand, year))

                row = cursor.fetchone()
                return dict(row) if row else None

        except Exception as e:
            print(f"Error fetching article {model_code}: {e}")
            return None

    def insert_final_pricelist_item(self, data: Dict) -> bool:
        """
        Insert or replace item in final_pricelist table.

        Uses INSERT OR REPLACE to handle duplicates gracefully.
        This ensures that reprocessing a PDF will update existing records
        rather than creating duplicates or failing.

        Args:
            data: Dictionary containing article data with database field names

        Returns:
            True if insertion successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                # Insert or replace to handle duplicates
                # The UNIQUE constraint on (brand, year, model_code) triggers replacement
                cursor.execute('''
                    INSERT OR REPLACE INTO final_pricelist (
                        brand, year, model_code, model_name, package, engine,
                        track, starter_type, gauge_type, spring_options, 
                        color, price_eur, source_file, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('brand', ''),  # Default to empty string if missing
                    data.get('year', 2024),  # Default to 2024 if missing
                    data.get('model_code', ''),  # Required field
                    data.get('model_name', ''),
                    data.get('package', ''),
                    data.get('engine', ''),
                    data.get('track', ''),
                    data.get('starter_type', ''),
                    data.get('gauge_type', ''),
                    data.get('spring_options', ''),
                    data.get('color', ''),
                    data.get('price_eur'),  # Can be None/NULL for missing prices
                    data.get('source_file', ''),
                    data.get('created_at', datetime.now().isoformat())
                ))

                conn.commit()
                return True

        except Exception as e:
            print(f"Error inserting article {data.get('model_code', 'UNKNOWN')}: {e}")
            return False

    def is_pdf_processed(self, pdf_filename: str) -> bool:
        """
        Check if a PDF file has already been processed.

        Prevents reprocessing of PDFs unless explicitly requested.
        This is important for incremental updates and avoiding
        unnecessary API calls.

        Args:
            pdf_filename: Name of PDF file to check

        Returns:
            True if PDF was already processed, False otherwise
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM processing_log WHERE pdf_filename = ?', (pdf_filename,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception:
            # If there's any error checking, assume not processed (safer)
            return False

    def mark_pdf_processed(self, pdf_filename: str, brand: str, year: str,
                           articles_count: int, method: str):
        """
        Mark a PDF as successfully processed in the processing log.

        Records processing metadata for tracking and preventing reprocessing.
        Also useful for debugging and performance analysis.

        Args:
            pdf_filename: Name of processed PDF file
            brand: Extracted brand name
            year: Extracted model year
            articles_count: Number of articles successfully extracted
            method: Extraction method used (claude_native, camelot_stream, etc.)
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO processing_log 
                    (pdf_filename, brand, year, articles_count, extraction_method)
                    VALUES (?, ?, ?, ?, ?)
                ''', (pdf_filename, brand, int(year), articles_count, method))
                conn.commit()
        except Exception as e:
            print(f"Error marking PDF as processed: {e}")

    def count_existing_articles(self, brand: str, year: str) -> int:
        """
        Count existing articles for a specific brand and year.

        Used for reporting and to show how many articles are already
        in the database for a given brand/year combination.

        Args:
            brand: Brand to count (SKI-DOO, LYNX)
            year: Model year to count

        Returns:
            Number of existing articles for brand/year
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM final_pricelist WHERE brand = ? AND year = ?',
                               (brand, year))
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def get_extraction_stats(self) -> Dict[str, Any]:
        """
        Generate comprehensive database statistics for reporting.

        Provides overview of database contents, processing history,
        and extraction method effectiveness. Used for monitoring
        and business intelligence.

        Returns:
            Dictionary containing:
            - total_articles: Total number of articles in database
            - by_brand: Article count by brand
            - by_year: Article count by year
            - pdfs_processed: Total PDFs processed
            - by_method: Processing count by extraction method
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                # Get total article count
                cursor.execute('SELECT COUNT(*) FROM final_pricelist')
                total_count = cursor.fetchone()[0]

                # Get count by brand for business intelligence
                cursor.execute('SELECT brand, COUNT(*) FROM final_pricelist GROUP BY brand ORDER BY brand')
                by_brand = dict(cursor.fetchall())

                # Get count by year for trend analysis
                cursor.execute('SELECT year, COUNT(*) FROM final_pricelist GROUP BY year ORDER BY year')
                by_year = dict(cursor.fetchall())

                # Get processing status from log
                cursor.execute('SELECT COUNT(*) FROM processing_log')
                pdfs_processed = cursor.fetchone()[0]

                # Get extraction method effectiveness
                cursor.execute('SELECT extraction_method, COUNT(*) FROM processing_log GROUP BY extraction_method')
                by_method = dict(cursor.fetchall())

                return {
                    'total_articles': total_count,
                    'by_brand': by_brand,
                    'by_year': by_year,
                    'pdfs_processed': pdfs_processed,
                    'by_method': by_method
                }

        except Exception as e:
            print(f"Error getting database stats: {e}")
            # Return safe default values if stats query fails
            return {'total_articles': 0, 'by_brand': {}, 'by_year': {}, 'pdfs_processed': 0}


class CamelotTableExtractor:
    """
    Fallback table extraction using Camelot library.

    This class provides table extraction capabilities when Claude's
    native PDF processing fails or is unavailable. Camelot is specifically
    designed for extracting tables from PDFs and can handle structured
    data that might be difficult for text-based extraction.

    Uses the 'stream' method which works better for simple, well-structured
    tables common in price lists.
    """

    def __init__(self):
        """
        Initialize Camelot extractor and check availability.

        Camelot has heavy dependencies (OpenCV, etc.) so we gracefully
        handle cases where it's not installed.
        """
        self.available = self._check_camelot_availability()

    def _check_camelot_availability(self) -> bool:
        """
        Check if Camelot library is properly installed and available.

        Camelot requires additional system dependencies (OpenCV, Ghostscript)
        so installation can fail. This method provides graceful degradation.

        Returns:
            True if Camelot is available, False otherwise
        """
        try:
            import camelot
            print("Camelot table extractor: AVAILABLE")
            return True
        except ImportError:
            print("WARNING: camelot-py not installed. Install with: pip install camelot-py[cv]")
            return False

    def extract_tables_from_pdf(self, pdf_path: str, brand: str, year: str) -> List[Dict]:
        """
        Extract table data from PDF using Camelot's stream method.

        The stream method works well for simple tables without heavy formatting.
        It's more reliable than lattice method for price lists that don't
        have strong border lines.

        Args:
            pdf_path: Path to PDF file
            brand: Brand name for metadata
            year: Model year for metadata

        Returns:
            List of dictionaries containing extracted article data
        """
        if not self.available:
            return []

        try:
            import camelot

            print(f"    Using Camelot to extract tables from {Path(pdf_path).name}")

            # Extract all tables from PDF using stream method
            # Stream method is better for simple tables without strong borders
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')

            print(f"    Camelot found {len(tables)} tables across all pages")

            if not tables:
                return []

            # Process each discovered table
            all_articles = []
            for table_idx, table in enumerate(tables):
                try:
                    df = table.df
                    print(f"    Processing table {table_idx + 1}: {df.shape[0]} rows x {df.shape[1]} columns")

                    # Convert table DataFrame to article format
                    articles = self._convert_table_to_articles(df, brand, year, pdf_path)
                    all_articles.extend(articles)

                    print(f"      Extracted {len(articles)} articles from table {table_idx + 1}")

                except Exception as e:
                    print(f"      Error processing table {table_idx + 1}: {e}")
                    continue

            print(f"    Camelot extraction completed: {len(all_articles)} total articles")
            return all_articles

        except Exception as e:
            print(f"    Camelot extraction failed: {e}")
            return []

    def _convert_table_to_articles(self, df: pd.DataFrame, brand: str, year: str, pdf_path: str) -> List[Dict]:
        """
        Convert Camelot-extracted DataFrame to standardized article format.

        This method handles the complex task of mapping Finnish headers
        to database fields and converting table rows to dictionaries.

        Args:
            df: Pandas DataFrame from Camelot extraction
            brand: Brand name for metadata
            year: Model year for metadata
            pdf_path: Source PDF path for metadata

        Returns:
            List of article dictionaries ready for database insertion
        """
        articles = []

        try:
            # Find the header row (may not be first row due to PDF formatting)
            header_row = self._find_header_row(df)
            if header_row is None:
                print(f"      Could not identify header row")
                return []

            # Create mapping from DataFrame columns to database fields
            column_mapping = self._map_finnish_headers(df.iloc[header_row].tolist())

            if not column_mapping:
                print(f"      Could not map Finnish headers")
                return []

            print(f"      Mapped columns: {list(column_mapping.keys())}")

            # Process each data row after the header
            for idx in range(header_row + 1, len(df)):
                try:
                    row = df.iloc[idx]
                    article = self._convert_row_to_article(row, column_mapping, brand, year, pdf_path)

                    # Only include articles with valid model codes
                    if article and article.get('model_code'):
                        articles.append(article)

                except Exception as e:
                    print(f"        Error processing row {idx}: {e}")
                    continue

            return articles

        except Exception as e:
            print(f"      Error converting table: {e}")
            return []

    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """
        Locate the header row containing Finnish column names.

        PDF extraction can result in metadata rows before the actual
        table headers. This method searches for Finnish keywords
        to identify the correct header row.

        Args:
            df: DataFrame to search

        Returns:
            Row index of headers, or None if not found
        """
        # Finnish keywords that should appear in price list headers
        finnish_keywords = ['tuotenro', 'malli', 'paketti', 'moottori', 'väri', 'hinta']

        # Check first 5 rows for header patterns
        for idx in range(min(5, len(df))):
            row_text = ' '.join(str(df.iloc[idx]).lower().split())
            matches = sum(1 for keyword in finnish_keywords if keyword in row_text)

            # If we find at least 3 Finnish keywords, this is likely the header
            if matches >= 3:
                return idx

        return None

    def _map_finnish_headers(self, headers: List[str]) -> Dict[int, str]:
        """
        Map Finnish column headers to database field names.

        This is critical for correctly interpreting table data.
        Finnish headers from PDFs need to be mapped to the standardized
        database schema fields.

        Args:
            headers: List of header strings from DataFrame

        Returns:
            Dictionary mapping column index to database field name
        """
        mapping = {}

        # Define patterns for each database field
        # Multiple patterns handle variations in header text
        header_patterns = {
            'model_code': ['tuotenro', 'tuote', 'koodi'],  # Product code/SKU
            'model_name': ['malli', 'model'],  # Model name
            'package': ['paketti', 'package'],  # Package/variant
            'engine': ['moottori', 'engine', 'motor'],  # Engine specification
            'track': ['telamatto', 'track'],  # Track specification
            'starter_type': ['käynnistin', 'starter'],  # Starter type
            'spring_options': ['kevätoptiot', 'spring', 'jousitus'],  # Spring options
            'gauge_type': ['mittaristo', 'gauge', 'näyttö'],  # Gauge/display type
            'color': ['väri', 'color'],  # Color specification
            'price_eur': ['hinta', 'price', 'suositus']  # Price (including VAT)
        }

        # Map each column to a database field
        for col_idx, header in enumerate(headers):
            if not header or pd.isna(header):
                continue

            header_lower = str(header).lower().strip()

            # Check each database field's patterns
            for db_field, patterns in header_patterns.items():
                for pattern in patterns:
                    if pattern in header_lower:
                        mapping[col_idx] = db_field
                        break
                if col_idx in mapping:
                    break

        return mapping

    def _convert_row_to_article(self, row: pd.Series, column_mapping: Dict[int, str],
                                brand: str, year: str, pdf_path: str) -> Optional[Dict]:
        """
        Convert a DataFrame row to article dictionary format.

        Maps table row data to database schema using the column mapping.
        Handles data cleaning and validation.

        Args:
            row: Pandas Series representing table row
            column_mapping: Mapping from column index to database field
            brand: Brand name for metadata
            year: Model year for metadata
            pdf_path: Source PDF path for metadata

        Returns:
            Article dictionary or None if invalid
        """
        try:
            # Initialize article with metadata
            article = {
                'brand': brand,
                'year': year,
                'source_file': Path(pdf_path).name
            }

            # Map columns using the established mapping
            for col_idx, db_field in column_mapping.items():
                if col_idx < len(row):
                    value = row.iloc[col_idx]

                    # Clean and format value, handling NaN and empty values
                    if pd.notna(value):
                        article[db_field] = str(value).strip()
                    else:
                        article[db_field] = ""

            # Validate that we have minimum required data
            if not article.get('model_code'):
                return None

            return article

        except Exception as e:
            print(f"        Error converting row: {e}")
            return None


class ClaudeAPIManager:
    """
    Manages all interactions with the Claude Sonnet 4 API.

    This class encapsulates API authentication, connection testing,
    and PDF processing using Claude's native document understanding
    capabilities. It handles the conversion of PDFs to base64 and
    manages API responses.

    Claude Sonnet 4 can directly process PDF documents without
    requiring separate text extraction, making it ideal for
    structured document processing.
    """

    def __init__(self):
        """
        Initialize Claude API client and test connection.

        Sets up the Anthropic client and verifies that the API
        is accessible with the provided credentials.
        """
        self.client = None
        self.available = False
        self._init_client()

    def _init_client(self):
        """
        Initialize the Anthropic Claude client.

        Requires ANTHROPIC_API_KEY environment variable to be set.
        Handles import errors gracefully if anthropic package not installed.
        """
        try:
            import anthropic

            # Get API key from environment
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                print("ERROR: ANTHROPIC_API_KEY not found in environment")
                return

            # Initialize client and test connection
            self.client = anthropic.Anthropic(api_key=api_key)
            self.available = self._test_connection()

        except ImportError:
            print("ERROR: anthropic package not installed. Run: pip install anthropic")
        except Exception as e:
            print(f"ERROR initializing Claude client: {e}")

    def _test_connection(self) -> bool:
        """
        Test the Claude API connection with a simple request.

        Verifies that the API key is valid and the service is accessible.
        Uses minimal tokens for the test to avoid unnecessary costs.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,  # Minimal tokens for test
                messages=[{"role": "user", "content": "Test connection. Reply OK."}]
            )

            result = bool(response.content[0].text.strip())
            if result:
                print("Claude Sonnet 4 API: CONNECTED")
            else:
                print("Claude API: FAILED - No response")

            return result

        except Exception as e:
            print(f"Claude API test failed: {e}")
            return False

    def extract_from_pdf_native(self, pdf_path: str, system_prompt: str,
                                user_prompt: str) -> Tuple[bool, str, int]:
        """
        Extract data from PDF using Claude's native document processing.

        This is the primary extraction method. Claude Sonnet 4 can directly
        understand PDF documents without requiring separate text extraction,
        making it highly effective for structured documents like price lists.

        Args:
            pdf_path: Path to PDF file
            system_prompt: System instructions for Claude
            user_prompt: User query/instructions

        Returns:
            Tuple of (success, response_content, estimated_tokens)
        """
        if not self.available:
            return False, "Claude API not available", 0

        try:
            # Read PDF file and convert to base64 for API transmission
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

            print(f"    Sending PDF to Claude ({len(pdf_base64)} base64 chars)...")

            # Create Claude request with PDF document
            # Uses document type for native PDF processing
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,  # Enough for large price lists
                temperature=0.1,  # Low temperature for consistent extraction
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt
                        },
                        {
                            "type": "document",  # Native PDF processing
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        }
                    ]
                }]
            )

            content = response.content[0].text.strip()

            # Estimate token usage (Claude doesn't provide exact counts)
            # Rough estimation: 1 token ≈ 4 characters
            estimated_tokens = (len(system_prompt) + len(user_prompt) + len(content)) // 4

            print(f"    Claude PDF processing: SUCCESS (~{estimated_tokens} tokens)")
            return True, content, estimated_tokens

        except Exception as e:
            print(f"    Claude PDF processing failed: {e}")
            return False, str(e), 0


class PDFProcessor:
    """
    Handles basic PDF operations using PyMuPDF.

    Provides fallback capabilities for page-by-page text extraction
    if Claude's native PDF processing fails. Also provides utility
    functions like page counting for processing optimization.
    """

    def __init__(self):
        """
        Initialize PDF processor and check PyMuPDF availability.

        PyMuPDF (fitz) is used for basic PDF operations. It's more
        lightweight than Camelot and good for text extraction.
        """
        try:
            import fitz  # PyMuPDF
            self.fitz = fitz
            self.available = True
        except ImportError:
            print("WARNING: PyMuPDF not installed. Run: pip install pymupdf")
            self.available = False

    def get_page_count(self, pdf_path: str) -> int:
        """
        Get total number of pages in PDF.

        Used for processing optimization and progress reporting.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages, or 0 if error
        """
        if not self.available:
            return 0

        try:
            doc = self.fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0

    def extract_page_text(self, pdf_path: str, page_num: int) -> str:
        """
        Extract plain text from a specific PDF page.

        Used as fallback when Claude native processing fails.
        Handles encoding issues that can occur with Finnish text.

        Args:
            pdf_path: Path to PDF file
            page_num: Zero-based page number

        Returns:
            Extracted text string, or empty string if error
        """
        if not self.available:
            return ""

        try:
            doc = self.fitz.open(pdf_path)

            if page_num >= len(doc):
                doc.close()
                return ""

            page = doc[page_num]
            text = page.get_text()

            # Handle potential encoding issues with Finnish characters
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
            doc.close()

            return text

        except Exception as e:
            print(f"Error extracting page {page_num + 1}: {e}")
            return ""


class PriceListExtractor:
    """
    Main orchestrator class for price list extraction.

    This class coordinates all extraction methods and handles the complete
    workflow from PDF discovery to database storage. It implements a
    fallback strategy with multiple extraction methods for robustness.

    Extraction Strategy:
    1. Primary: Claude native PDF processing
    2. Fallback 1: Camelot table extraction
    3. Fallback 2: Page-by-page text processing with Claude

    All extracted data is written directly to the database without
    intermediate JSON files for efficiency and reliability.
    """

    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        Initialize the main extractor with all required components.

        Sets up database connection, API clients, and processing components.
        Validates that required directories exist and APIs are accessible.

        Args:
            config: Optional configuration override
        """
        self.config = config or ExtractionConfig()

        # Initialize all required components
        self.db = DatabaseManager(self.config.database_file)
        self.claude = ClaudeAPIManager()
        self.camelot = CamelotTableExtractor()
        self.pdf_processor = PDFProcessor()

        # Set up PDF directory path
        self.pdf_dir = Path(self.config.pdf_directory)

        # Initialize statistics tracking
        self.stats = ExtractionStats()

        # Print initialization status
        print(f"PriceListExtractor initialized")
        print(f"  Database: {self.config.database_file}")
        print(f"  PDF directory: {self.pdf_dir}")
        print(f"  Claude API: {'Available' if self.claude.available else 'Not available'}")
        print(f"  Camelot: {'Available' if self.camelot.available else 'Not available'}")

    def extract_single_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract articles from a single PDF using multi-method fallback strategy.

        This method implements the core extraction logic with fallback methods:
        1. Try Claude native PDF processing (fastest and most accurate)
        2. Fall back to Camelot table extraction if native fails
        3. Fall back to page-by-page text processing as last resort

        Args:
            pdf_path: Path to PDF file to process

        Returns:
            Dictionary with extraction results and metadata
        """
        try:
            pdf_path_obj = Path(pdf_path)

            # Validate file exists
            if not pdf_path_obj.exists():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")

            # Parse brand and year from filename using established patterns
            brand, year = self._parse_filename(pdf_path_obj.name)
            print(f"Processing: {pdf_path_obj.name} (Brand: {brand}, Year: {year})")

            # Skip if already processed (prevents duplicate work)
            if self.db.is_pdf_processed(pdf_path_obj.name):
                print(f"  SKIPPING: {pdf_path_obj.name} already processed")
                existing_count = self.db.count_existing_articles(brand, year)
                return {
                    'articles_in_db': existing_count,
                    'newly_extracted': 0,
                    'brand': brand,
                    'year': year,
                    'method': 'skipped',
                    'status': 'already_processed'
                }

            # METHOD 1: Page-by-page processing (preferred - fastest)
            print(f"  METHOD 1: Trying page-by-page extraction...")
            articles = self._extract_page_by_page(pdf_path_obj, brand, year)
            extraction_method = "page_by_page"

            # METHOD 2: Camelot table extraction fallback
            if not articles and self.camelot.available:
                print(f"  METHOD 2: Falling back to Camelot table extraction...")
                articles = self.camelot.extract_tables_from_pdf(str(pdf_path_obj), brand, year)
                extraction_method = "camelot_stream"

            # METHOD 3: Claude native PDF processing fallback
            if not articles:
                print(f"  METHOD 3: Falling back to Claude native PDF processing...")
                articles = self._extract_with_claude_pdf(pdf_path_obj, brand, year)
                extraction_method = "claude_native"

            # Save extracted articles to database
            saved_count = 0
            if articles:
                saved_count = self._save_articles_to_db(articles, brand, year, pdf_path_obj.name)

                # Mark PDF as processed to prevent reprocessing
                self.db.mark_pdf_processed(pdf_path_obj.name, brand, year, saved_count, extraction_method)

                print(f"  SUCCESS: {saved_count} articles saved using {extraction_method}")
            else:
                print(f"  FAILED: No articles extracted with any method")

            return {
                'articles_in_db': saved_count,
                'newly_extracted': len(articles),
                'brand': brand,
                'year': year,
                'pdf_file': pdf_path_obj.name,
                'method': extraction_method,
                'status': 'completed' if articles else 'no_data'
            }

        except Exception as e:
            print(f"Error extracting from {pdf_path}: {e}")
            return {'error': str(e), 'status': 'failed'}

    def process_all_pdfs(self) -> Dict[str, Any]:
        """
        Process all PRICE_LIST PDFs in the configured directory.

        Discovers all PDF files matching the PRICE_LIST pattern,
        processes each one using the multi-method fallback strategy,
        and provides comprehensive reporting on results.

        Returns:
            Dictionary with complete processing results and statistics
        """
        print("=" * 80)
        print(" PROCESSING ALL PRICE LISTS - MULTI-METHOD EXTRACTION")
        print("=" * 80)

        # Verify Claude API is available (required for all methods)
        if not self.claude.available:
            print("ERROR: Claude API not available")
            return {'error': 'Claude API not available'}

        # Discover all PRICE_LIST PDFs in the directory
        price_lists = list(self.pdf_dir.glob("*PRICE_LIST*.pdf"))
        if not price_lists:
            print(f"ERROR: No PRICE_LIST PDFs found in {self.pdf_dir}")
            return {'error': 'No PDFs found'}

        # Show discovered files
        print(f"Found {len(price_lists)} PRICE_LIST PDFs:")
        for pdf in price_lists:
            print(f"  - {pdf.name}")

        # Show available extraction methods
        print(f"\nExtraction methods available:")
        print(f"  1. Claude native PDF processing: {'✓' if self.claude.available else '✗'}")
        print(f"  2. Camelot table extraction: {'✓' if self.camelot.available else '✗'}")
        print(f"  3. Page-by-page Claude: {'✓' if self.pdf_processor.available else '✗'}")

        # Process each PDF with progress tracking
        total_new_articles = 0
        processing_results = []
        method_usage = {}

        for i, pdf_path in enumerate(price_lists):
            print(f"\n[{i + 1}/{len(price_lists)}] Processing: {pdf_path.name}")

            # Process single PDF with fallback methods
            result = self.extract_single_pdf(str(pdf_path))

            # Accumulate statistics
            total_new_articles += result.get('newly_extracted', 0)
            processing_results.append(result)

            # Track which extraction methods are being used
            method = result.get('method', 'unknown')
            method_usage[method] = method_usage.get(method, 0) + 1

            # Show immediate progress feedback
            status = result.get('status', 'unknown')
            if status == 'completed':
                print(f"    ✓ COMPLETED: {result.get('newly_extracted', 0)} articles saved via {method}")
            elif status == 'already_processed':
                print(f"    ↻ SKIPPED: Already processed ({result.get('articles_in_db', 0)} existing)")
            else:
                print(f"    ✗ FAILED: {result.get('error', 'Unknown error')}")

        # Generate final database statistics
        db_stats = self.db.get_extraction_stats()

        # Print comprehensive summary report
        self._print_final_summary(db_stats, total_new_articles, processing_results, method_usage)

        return {
            'total_in_database': db_stats.get('total_articles', 0),
            'newly_extracted': total_new_articles,
            'processing_results': processing_results,
            'method_usage': method_usage,
            'database_stats': db_stats
        }

    def _extract_with_claude_pdf(self, pdf_path: Path, brand: str, year: str) -> List[Dict]:
        """
        Primary extraction method using Claude's native PDF processing.

        This method leverages Claude Sonnet 4's ability to directly understand
        PDF documents. It sends the entire PDF to Claude with specific
        instructions for extracting Finnish price list data.

        Args:
            pdf_path: Path object for PDF file
            brand: Brand name (SKI-DOO, LYNX)
            year: Model year

        Returns:
            List of extracted article dictionaries
        """
        try:
            # Create specialized prompts for Finnish price list extraction
            system_prompt = self._create_system_prompt(brand, year)
            user_prompt = self._create_user_prompt(brand, year, pdf_path.name)

            # Send PDF to Claude for processing
            success, response, tokens = self.claude.extract_from_pdf_native(
                str(pdf_path), system_prompt, user_prompt
            )

            if not success:
                print(f"    Claude PDF extraction failed: {response}")
                return []

            # Parse Claude's JSON response into article list
            articles = self._parse_json_response(response)

            if articles:
                print(f"    Claude native: Extracted {len(articles)} articles")
                self.stats.tokens_used += tokens
                return articles
            else:
                print(f"    Claude native: No articles extracted")
                return []

        except Exception as e:
            print(f"    Claude native extraction error: {e}")
            return []

    def _extract_page_by_page(self, pdf_path: Path, brand: str, year: str) -> List[Dict]:
        """
        Last resort extraction using page-by-page text processing.

        When both Claude native and Camelot fail, this method extracts
        text from each page individually and sends it to Claude for
        processing. This is the most token-intensive method but can
        handle PDFs that other methods cannot process.

        Args:
            pdf_path: Path object for PDF file
            brand: Brand name
            year: Model year

        Returns:
            List of extracted article dictionaries from all pages
        """
        try:
            # Get total pages for progress tracking
            total_pages = self.pdf_processor.get_page_count(str(pdf_path))
            if total_pages == 0:
                return []

            print(f"    Processing {total_pages} pages sequentially...")

            all_articles = []
            system_prompt = self._create_system_prompt(brand, year)

            # Process each page individually
            for page_num in range(total_pages):
                try:
                    # Extract text from current page
                    page_text = self.pdf_processor.extract_page_text(str(pdf_path), page_num)
                    if not page_text.strip():
                        continue  # Skip empty pages

                    # Create page-specific extraction prompt
                    user_prompt = f"""Extract ALL article information from page {page_num + 1} of this {brand} {year} price list.

PAGE {page_num + 1} CONTENT:
{page_text}

Return JSON array with all products found on this page."""

                    # Send page text to Claude for processing
                    response = self.claude.client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4000,  # Smaller limit for single page
                        temperature=0.1,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )

                    # Parse page response and accumulate articles
                    content = response.content[0].text.strip()
                    page_articles = self._parse_json_response(content)
                    all_articles.extend(page_articles)

                    print(f"      Page {page_num + 1}: {len(page_articles)} articles")

                    # Estimate tokens used (rough calculation)
                    self.stats.tokens_used += (len(system_prompt) + len(user_prompt) + len(content)) // 4

                except Exception as e:
                    print(f"      Page {page_num + 1} failed: {e}")
                    continue

            print(f"    Page-by-page: Total {len(all_articles)} articles")
            return all_articles

        except Exception as e:
            print(f"    Page-by-page extraction failed: {e}")
            return []

    def _save_articles_to_db(self, articles: List[Dict], brand: str, year: str, source_file: str) -> int:
        """
        Save extracted articles directly to database with validation.

        This method handles data cleaning, price parsing, and database
        insertion. It provides detailed logging of the save process
        for debugging and verification.

        Args:
            articles: List of article dictionaries
            brand: Brand name for metadata
            year: Model year for metadata
            source_file: Source PDF filename for tracking

        Returns:
            Number of successfully saved articles
        """
        saved_count = 0

        print(f"    Saving {len(articles)} articles to database...")

        for i, article in enumerate(articles, 1):
            # Ensure all articles have required metadata
            article["brand"] = brand
            article["year"] = int(year)
            article["source_file"] = source_file
            article["created_at"] = datetime.now().isoformat()

            # Parse price text to numeric value (handles Finnish formatting)
            price_text = article.get("price_eur", "")
            article["price_eur"] = self._parse_price(price_text)

            # Validate that we have minimum required data
            model_code = article.get("model_code", "").strip()
            if not model_code:
                print(f"      Article {i}: Missing model_code, skipping")
                self.stats.failed_articles += 1
                continue

            # Insert into database using DatabaseManager
            if self.db.insert_final_pricelist_item(article):
                saved_count += 1

                # Show first few articles for verification
                if i <= 3:
                    price_display = f"€{article['price_eur']}" if article['price_eur'] else "No price"
                    print(
                        f"      ✓ {model_code}: {article.get('model_name', '')} {article.get('package', '')} - {price_display}")
            else:
                print(f"      ✗ Failed to save: {model_code}")
                self.stats.failed_articles += 1

        # Show summary if there were many articles
        if saved_count > 3:
            print(f"      ... and {saved_count - 3} more articles saved")

        return saved_count

    def _parse_filename(self, filename: str) -> Tuple[str, str]:
        """
        Extract brand and model year from PDF filename.

        Handles various filename patterns used for price list PDFs.
        This is critical for proper data categorization in the database.

        Expected patterns:
        - LYNX_2025_PRICE_LIST.pdf
        - SKI-DOO_MY26_PRICE_LIST.pdf
        - SKIDOO_2024_PRICE_LIST.pdf

        Args:
            filename: PDF filename to parse

        Returns:
            Tuple of (brand, year) as strings

        Raises:
            ValueError: If brand or year cannot be determined
        """
        try:
            # Extract brand from filename prefix
            filename_upper = filename.upper()
            if filename_upper.startswith("LYNX"):
                brand = "LYNX"
            elif "SKI-DOO" in filename_upper or "SKIDOO" in filename_upper:
                brand = "SKI-DOO"
            else:
                raise ValueError(f"Unknown brand in filename: {filename}")

            # Extract year using multiple regex patterns
            year_patterns = [
                r"MY(\d{2})",  # Model year format: MY24, MY25, MY26
                r"_?(20\d{2})",  # Direct year format: _2024, 2025, etc.
                r"(\d{4})"  # Any 4-digit year in filename
            ]

            year = "2024"  # Default fallback year
            for pattern in year_patterns:
                match = re.search(pattern, filename)
                if match:
                    year_str = match.group(1)
                    # Convert 2-digit years to 4-digit (MY24 -> 2024)
                    if len(year_str) == 2:
                        year = f"20{year_str}"
                    else:
                        year = year_str
                    break

            return brand, year

        except Exception as e:
            raise ValueError(f"Cannot parse filename {filename}: {e}")

    def _create_system_prompt(self, brand: str, year: str) -> str:
        """
        Create specialized system prompt for Claude extraction.

        This prompt is crucial for extraction quality. It provides:
        1. Clear mapping from Finnish headers to database fields
        2. Specific output format requirements
        3. Instructions for handling missing data
        4. Examples of expected JSON structure

        Args:
            brand: Brand name for context
            year: Model year for context

        Returns:
            Complete system prompt string
        """
        return f"""You are an expert Finnish snowmobile price list data extraction specialist with deep knowledge of {brand} product nomenclature and pricing structures.

EXPERTISE CONTEXT:
- {brand} {year} model year price list analysis
- BRP (Lynx/Skidoo) snowmobiles and powersports terminology expertise
- Structured data extraction and validation
- Quality control and completeness verification

FINNISH HEADER MAPPING (Critical Field Identification):
• Tuotenro → model_code (MUST be exactly 4 characters: ABCD format)
• Malli → model_name (Model series like "Renegade", "MXZ")
• Paketti → package (Trim/variant like "X-RS", "Sport", "STD")
• Moottori → engine (Engine specs like "850 E-TEC", "600 EFI")
• Telamatto → track (Track specs like "154in 3900mm")
• Käynnistin → starter_type (Starter type: "Electric", "Manual", "SHOT")
• Kevätoptiot → spring_options (Spring setup or empty if none)
• Mittaristo → gauge_type (Display type or empty for pre-2026)
• Väri → color (Color specification)
• Suositushinta → price_eur (Price in EUR, numeric only)

VALIDATION RULES:
1. model_code MUST be exactly 4 uppercase characters
2. price_eur must be numeric (extract numbers only, no currency symbols)
3. All text fields: preserve exact Finnish text, escape quotes properly
4. Empty fields: use "" (never null or undefined)

ERROR HANDLING:
- Skip rows without valid 4-character model_code
- Handle special characters (Ä, Ö, €) properly in JSON
- If price contains text, extract numeric portion only
- Maintain Finnish diacritics in text fields

JSON OUTPUT REQUIREMENTS:
- Start with [ and end with ]
- No markdown blocks, no explanations
- Properly escape all quotes and backslashes
- Valid JSON syntax only

EXAMPLE:
[{{"model_code":"LMSA","model_name":"Rave","package":"120","engine":"120","track":"67in","starter_type":"Manual Start","spring_options":"","gauge_type":"","color":"Viper Red","price_eur":"5000"}}]

Extract ALL valid products from THIS PAGE ONLY. Return pure JSON array."""

    def _create_user_prompt(self, brand: str, year: str, filename: str) -> str:
        """
        Create user prompt for specific PDF extraction request.

        Provides context about the specific document being processed
        and reinforces the requirement to process all pages.

        Args:
            brand: Brand name
            year: Model year
            filename: PDF filename for reference

        Returns:
            User prompt string
        """
        return f"""Extract ALL product articles from this {brand} {year} price list PDF document.

DOCUMENT DETAILS:
- Brand: {brand}
- Year: {year} 
- Source: {filename}

Process the complete PDF document and extract EVERY valid product row. Return complete JSON array with all products found."""

    def _parse_json_response(self, response: str) -> List[Dict]:
        """
        Parse and validate Claude's JSON response.

        Claude sometimes wraps JSON in markdown code blocks or returns
        nested structures. This method handles various response formats
        and extracts the article list reliably.

        Args:
            response: Raw response text from Claude

        Returns:
            List of article dictionaries, empty list if parsing fails
        """
        try:
            # Remove whitespace and normalize response
            clean_response = response.strip()

            # Handle markdown code block wrapping
            if clean_response.startswith('```json'):
                clean_response = clean_response.replace('```json', '').replace('```', '').strip()
            elif clean_response.startswith('```'):
                clean_response = clean_response.replace('```', '').strip()

            # Parse JSON with error handling
            data = json.loads(clean_response)

            # Handle different response structures
            if isinstance(data, list):
                # Direct array response (expected format)
                return data
            elif isinstance(data, dict) and "articles" in data:
                # Nested response with articles key
                return data["articles"]
            else:
                print(f"Unexpected response format: {type(data)}")
                return []

        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            print(f"Response preview: {response[:300]}...")
            return []
        except Exception as e:
            print(f"Error parsing response: {e}")
            return []

    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        Parse Finnish price text to numeric float value.

        Finnish price formats can include:
        - Currency symbols (€, EUR)
        - Comma as decimal separator (12.345,50)
        - Various whitespace characters
        - Additional text like "(sis ALV:n)"

        Args:
            price_text: Raw price string from PDF

        Returns:
            Parsed price as float, or None if parsing fails
        """
        if not price_text:
            return None

        try:
            # Remove currency symbols and normalize
            clean_price = str(price_text).strip()
            clean_price = clean_price.replace('€', '').replace('EUR', '').strip()
            clean_price = clean_price.replace(' ', '').replace('\xa0', '')  # Remove all types of spaces

            # Handle Finnish decimal formatting (comma as decimal separator)
            if ',' in clean_price and '.' not in clean_price:
                clean_price = clean_price.replace(',', '.')

            # Extract numeric portion using regex
            numeric_match = re.search(r'[\d.,]+', clean_price)
            if numeric_match:
                numeric_str = numeric_match.group().replace(',', '.')
                return float(numeric_str)

            return None

        except (ValueError, TypeError):
            # Return None for any parsing errors (will be stored as NULL in DB)
            return None

    def _print_final_summary(self, db_stats: Dict, new_articles: int,
                             processing_results: List[Dict], method_usage: Dict):
        """
        Print comprehensive final summary of extraction results.

        Provides detailed reporting on:
        - Database contents and statistics
        - Processing results by file
        - Extraction method effectiveness
        - Error summary for failed files

        Args:
            db_stats: Database statistics from get_extraction_stats()
            new_articles: Count of newly extracted articles
            processing_results: List of per-file processing results
            method_usage: Dictionary of extraction method usage counts
        """
        print(f"""
{'=' * 80}
 EXTRACTION COMPLETED - MULTI-METHOD APPROACH
{'=' * 80}
Database Results:
  Total articles in database: {db_stats.get('total_articles', 0):,}
  Newly extracted this run: {new_articles:,}""")

        # Show distribution by brand (business intelligence)
        print(f"\nBy Brand:")
        for brand, count in db_stats.get('by_brand', {}).items():
            print(f"  {brand}: {count:,} articles")

        # Show distribution by year (trend analysis)
        print(f"\nBy Year:")
        for year, count in db_stats.get('by_year', {}).items():
            print(f"  {year}: {count:,} articles")

        # Show extraction method effectiveness
        print(f"\nExtraction Methods Used:")
        for method, count in method_usage.items():
            print(f"  {method}: {count} PDFs")

        # Analyze processing results for summary statistics
        completed = [r for r in processing_results if r.get('status') == 'completed']
        skipped = [r for r in processing_results if r.get('status') == 'already_processed']
        failed = [r for r in processing_results if r.get('status') in ['failed', 'no_data']]

        print(f"\nProcessing Summary:")
        print(f"  PDFs completed: {len(completed)}")
        print(f"  PDFs skipped (already done): {len(skipped)}")
        print(f"  PDFs failed/no data: {len(failed)}")

        # Show details of failed PDFs for debugging
        if failed:
            print(f"\nFailed PDFs:")
            for result in failed:
                error_msg = result.get('error', 'No data extracted')
                print(f"  - {result.get('pdf_file', 'Unknown')}: {error_msg}")

        # Show file locations and resource usage
        print(f"\nDatabase file: {self.config.database_file}")
        print(f"Estimated tokens used: {self.stats.tokens_used:,}")
        print("=" * 80)


# Utility Functions for Database Operations and Testing

def query_database(db_file: str = "price_extraction.db", query: str = None) -> List[Dict]:
    """
    Execute SQL query against the extraction database.

    Utility function for testing and data analysis. Provides safe
    database querying with proper error handling.

    Args:
        db_file: Path to SQLite database file
        query: SQL query string, or None for default sample query

    Returns:
        List of dictionaries representing query results
    """
    try:
        with sqlite3.connect(db_file) as conn:
            # Use Row factory to get dictionary-like results
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Use provided query or default sample query
            if query:
                cursor.execute(query)
            else:
                # Default: show sample of articles ordered logically
                cursor.execute('SELECT * FROM final_pricelist ORDER BY brand, year, model_code LIMIT 10')

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        print(f"Database query error: {e}")
        return []


def show_database_sample(db_file: str = "price_extraction.db"):
    """
    Display a sample of extracted data for verification.

    Utility function for quickly checking extraction results.
    Shows article distribution and sample records for validation.

    Args:
        db_file: Path to SQLite database file
    """
    print("\n" + "=" * 80)
    print(" DATABASE SAMPLE WITH EXTRACTION METHODS")
    print("=" * 80)

    # Show sample articles with key information
    sample_data = query_database(db_file, '''
                                          SELECT brand, year, model_code, model_name, package, price_eur
                                          FROM final_pricelist
                                          ORDER BY brand, year, model_code
                                              LIMIT 10
                                          ''')

    if sample_data:
        print("Sample Articles:")
        for item in sample_data:
            price_str = f"€{item['price_eur']}" if item['price_eur'] else "No price"
            print(
                f"  {item['brand']} {item['year']} | {item['model_code']} | {item['model_name']} {item['package']} | {price_str}")

    # Show extraction method statistics for analysis
    try:
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT extraction_method, COUNT(*) FROM processing_log GROUP BY extraction_method')
            methods = cursor.fetchall()

            if methods:
                print(f"\nExtraction Methods Used:")
                for method, count in methods:
                    print(f"  {method}: {count} PDFs")
    except Exception:
        pass  # Gracefully handle missing extraction_method column in older databases

    # Show overall statistics
    stats = DatabaseManager(db_file).get_extraction_stats()
    print(f"\nDatabase Totals:")
    print(f"  Articles: {stats.get('total_articles', 0):,}")
    print(f"  PDFs processed: {stats.get('pdfs_processed', 0)}")
    print("=" * 80)


def main():
    """
    Main execution function for price list extraction system.

    This function orchestrates the complete extraction workflow:
    1. Validates environment setup (API keys, directories)
    2. Initializes extraction system
    3. Processes all available PDF files
    4. Reports final results and statistics

    Environment Requirements:
    - ANTHROPIC_API_KEY must be set in environment or .env file
    - PDF directory must exist with *PRICE_LIST*.pdf files

    Exit Codes:
    - 0: Successful completion
    - 1: Environment setup error (missing API key)
    - 2: No Claude API access
    """
    print("Starting Price List Extraction - MULTI-METHOD WITH DATABASE STORAGE")

    # Validate environment setup
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not found in environment")
        print("Please set your Claude API key in .env file or environment")
        return 1

    try:
        # Initialize extraction system with default configuration
        extractor = PriceListExtractor()
        
        # Check if we have the specific PDF file
        pdf_path = "docs/Price_lists/SKIDOO_LYNX_2024-2026_PRICE_LISTS.pdf"
        if Path(pdf_path).exists():
            print(f"Processing specific PDF: {pdf_path}")
            result = extractor.extract_single_pdf(pdf_path)
            print(f"Extraction result: {result}")
        else:
            # Process all available PDFs if specific one not found
            print("Processing all available price list PDFs...")
            results = extractor.process_all_pdfs()
            
            # Show final statistics
            print(f"\n{'='*60}")
            print("FINAL EXTRACTION SUMMARY")
            print(f"{'='*60}")
            print(f"Total articles in database: {results.get('total_in_database', 0):,}")
            print(f"Articles extracted this run: {results.get('newly_extracted', 0):,}")

        # Show sample of extracted data for verification
        show_database_sample(extractor.config.database_file)
        
        return 0

    except Exception as e:
        print(f"ERROR: Extraction failed: {e}")
        return 2


if __name__ == "__main__":
    exit(main())