import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
import asyncpg
import os

from ..models.domain import (
    PriceList, PriceEntry, Catalog, BaseModel, Product, 
    ProcessingJob, SpringOption, MatchingResult,
    ProcessingStatus, ValidationStatus, JobStatus
)


logger = logging.getLogger(__name__)


class DatabaseRepository:
    """Database repository for all data access operations"""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv("DATABASE_URL")
        self.connection_pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Database connection pool closed")
    
    # Price Lists
    async def create_price_list(self, price_list: PriceList) -> PriceList:
        """Create a new price list"""
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO price_lists (id, filename, brand, market, model_year, status, uploaded_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, price_list.id, price_list.filename, price_list.brand, 
                price_list.market, price_list.model_year, 
                price_list.status.value, price_list.uploaded_at)
            
            return price_list
    
    async def get_price_list(self, price_list_id: UUID) -> Optional[PriceList]:
        """Get price list by ID"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM price_lists WHERE id = $1
            """, price_list_id)
            
            if row:
                return PriceList(
                    id=row['id'],
                    filename=row['filename'],
                    brand=row['brand'],
                    market=row['market'],
                    model_year=row['model_year'],
                    total_entries=row['total_entries'],
                    processed_entries=row['processed_entries'],
                    failed_entries=row['failed_entries'],
                    status=ProcessingStatus(row['status']),
                    uploaded_at=row['uploaded_at'],
                    processed_at=row['processed_at']
                )
            return None
    
    async def get_pending_price_lists(self) -> List[PriceList]:
        """Get all price lists with pending status"""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM price_lists WHERE status = 'pending'
                ORDER BY uploaded_at ASC
            """)
            
            return [PriceList(
                id=row['id'],
                filename=row['filename'],
                brand=row['brand'],
                market=row['market'],
                model_year=row['model_year'],
                total_entries=row['total_entries'],
                processed_entries=row['processed_entries'],
                failed_entries=row['failed_entries'],
                status=ProcessingStatus(row['status']),
                uploaded_at=row['uploaded_at'],
                processed_at=row['processed_at']
            ) for row in rows]
    
    async def update_price_list_stats(
        self, 
        price_list_id: UUID, 
        total_entries: Optional[int] = None,
        processed_entries: Optional[int] = None,
        failed_entries: Optional[int] = None,
        status: Optional[ProcessingStatus] = None
    ):
        """Update price list statistics"""
        async with self.connection_pool.acquire() as conn:
            updates = []
            values = []
            param_count = 1
            
            if total_entries is not None:
                updates.append(f"total_entries = ${param_count}")
                values.append(total_entries)
                param_count += 1
            
            if processed_entries is not None:
                updates.append(f"processed_entries = ${param_count}")
                values.append(processed_entries)
                param_count += 1
            
            if failed_entries is not None:
                updates.append(f"failed_entries = ${param_count}")
                values.append(failed_entries)
                param_count += 1
            
            if status is not None:
                updates.append(f"status = ${param_count}")
                values.append(status.value)
                param_count += 1
                
                if status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                    updates.append(f"processed_at = ${param_count}")
                    values.append(datetime.now())
                    param_count += 1
            
            if updates:
                query = f"UPDATE price_lists SET {', '.join(updates)} WHERE id = ${param_count}"
                values.append(price_list_id)
                await conn.execute(query, *values)
    
    # Price Entries
    async def create_price_entry(self, price_entry: PriceEntry) -> PriceEntry:
        """Create a new price entry"""
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO price_entries (
                    id, price_list_id, model_code, malli, paketti, moottori, 
                    telamatto, kaynnistin, mittaristo, kevatoptiot, vari,
                    price, currency, market, brand, model_year, status, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                )
            """, price_entry.id, price_entry.price_list_id, price_entry.model_code,
                price_entry.malli, price_entry.paketti, price_entry.moottori,
                price_entry.telamatto, price_entry.kaynnistin, price_entry.mittaristo,
                price_entry.kevatoptiot, price_entry.vari, price_entry.price,
                price_entry.currency, price_entry.market, price_entry.brand,
                price_entry.model_year, price_entry.status.value, price_entry.created_at)
            
            return price_entry
    
    async def get_price_entry(self, price_entry_id: UUID) -> Optional[PriceEntry]:
        """Get price entry by ID"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM price_entries WHERE id = $1
            """, price_entry_id)
            
            if row:
                return self._row_to_price_entry(row)
            return None
    
    async def get_unmatched_price_entries(self) -> List[PriceEntry]:
        """Get all price entries that haven't been matched yet"""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT pe.* FROM price_entries pe
                LEFT JOIN products p ON pe.id = p.price_entry_id
                WHERE p.id IS NULL AND pe.status = 'extracted'
                ORDER BY pe.created_at ASC
            """)
            
            return [self._row_to_price_entry(row) for row in rows]
    
    async def update_price_entry_status(self, price_entry_id: UUID, status: ProcessingStatus):
        """Update price entry status"""
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                UPDATE price_entries SET status = $1, updated_at = $2 WHERE id = $3
            """, status.value, datetime.now(), price_entry_id)
    
    def _row_to_price_entry(self, row) -> PriceEntry:
        """Convert database row to PriceEntry object"""
        return PriceEntry(
            id=row['id'],
            price_list_id=row['price_list_id'],
            model_code=row['model_code'],
            malli=row['malli'],
            paketti=row['paketti'],
            moottori=row['moottori'],
            telamatto=row['telamatto'],
            kaynnistin=row['kaynnistin'],
            mittaristo=row['mittaristo'],
            kevatoptiot=row['kevatoptiot'],
            vari=row['vari'],
            price=row['price'],
            currency=row['currency'],
            market=row['market'],
            brand=row['brand'],
            model_year=row['model_year'],
            catalog_lookup_key=row['catalog_lookup_key'],
            status=ProcessingStatus(row['status']),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    # Catalogs
    async def create_catalog(self, catalog: Catalog) -> Catalog:
        """Create a new catalog"""
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO catalogs (
                    id, filename, brand, model_year, document_type, 
                    language, status, uploaded_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, catalog.id, catalog.filename, catalog.brand, catalog.model_year,
                catalog.document_type, catalog.language, catalog.status.value, 
                catalog.uploaded_at)
            
            return catalog
    
    async def get_catalog(self, catalog_id: UUID) -> Optional[Catalog]:
        """Get catalog by ID"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM catalogs WHERE id = $1
            """, catalog_id)
            
            if row:
                return self._row_to_catalog(row)
            return None
    
    async def get_pending_catalogs(self) -> List[Catalog]:
        """Get all catalogs with pending status"""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM catalogs WHERE status = 'pending'
                ORDER BY uploaded_at ASC
            """)
            
            return [self._row_to_catalog(row) for row in rows]
    
    async def update_catalog_stats(
        self, 
        catalog_id: UUID,
        total_pages: Optional[int] = None,
        total_models_extracted: Optional[int] = None,
        status: Optional[ProcessingStatus] = None
    ):
        """Update catalog statistics"""
        async with self.connection_pool.acquire() as conn:
            updates = []
            values = []
            param_count = 1
            
            if total_pages is not None:
                updates.append(f"total_pages = ${param_count}")
                values.append(total_pages)
                param_count += 1
            
            if total_models_extracted is not None:
                updates.append(f"total_models_extracted = ${param_count}")
                values.append(total_models_extracted)
                param_count += 1
            
            if status is not None:
                updates.append(f"status = ${param_count}")
                values.append(status.value)
                param_count += 1
                
                if status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                    updates.append(f"processed_at = ${param_count}")
                    values.append(datetime.now())
                    param_count += 1
            
            if updates:
                query = f"UPDATE catalogs SET {', '.join(updates)} WHERE id = ${param_count}"
                values.append(catalog_id)
                await conn.execute(query, *values)
    
    def _row_to_catalog(self, row) -> Catalog:
        """Convert database row to Catalog object"""
        return Catalog(
            id=row['id'],
            filename=row['filename'],
            brand=row['brand'],
            model_year=row['model_year'],
            document_type=row['document_type'],
            language=row['language'],
            total_pages=row['total_pages'],
            total_models_extracted=row['total_models_extracted'],
            status=ProcessingStatus(row['status']),
            uploaded_at=row['uploaded_at'],
            processed_at=row['processed_at']
        )
    
    # Base Models
    async def create_base_model(self, base_model: BaseModel) -> BaseModel:
        """Create a new base model"""
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO base_models_catalog (
                    id, catalog_id, lookup_key, brand, model_family, model_year,
                    engine_options, track_options, suspension_options, starter_options,
                    dimensions, features, full_specifications, marketing_description,
                    source_pages, extraction_confidence, completeness_score, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                )
            """, base_model.id, base_model.catalog_id, base_model.lookup_key,
                base_model.brand, base_model.model_family, base_model.model_year,
                base_model.engine_options, base_model.track_options, 
                base_model.suspension_options, base_model.starter_options,
                base_model.dimensions, base_model.features, 
                base_model.full_specifications, base_model.marketing_description,
                base_model.source_pages, base_model.extraction_confidence,
                base_model.completeness_score, base_model.created_at)
            
            return base_model
    
    async def get_base_model(self, base_model_id: UUID) -> Optional[BaseModel]:
        """Get base model by ID"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM base_models_catalog WHERE id = $1
            """, base_model_id)
            
            if row:
                return self._row_to_base_model(row)
            return None
    
    async def get_base_model_by_lookup_key(self, lookup_key: str) -> Optional[BaseModel]:
        """Get base model by lookup key"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM base_models_catalog WHERE lookup_key = $1
            """, lookup_key)
            
            if row:
                return self._row_to_base_model(row)
            return None
    
    async def get_base_models_by_brand_year(self, brand: str, year: int) -> List[BaseModel]:
        """Get base models by brand and year"""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM base_models_catalog 
                WHERE brand = $1 AND model_year = $2
                ORDER BY model_family ASC
            """, brand, year)
            
            return [self._row_to_base_model(row) for row in rows]
    
    def _row_to_base_model(self, row) -> BaseModel:
        """Convert database row to BaseModel object"""
        return BaseModel(
            id=row['id'],
            catalog_id=row['catalog_id'],
            lookup_key=row['lookup_key'],
            brand=row['brand'],
            model_family=row['model_family'],
            model_year=row['model_year'],
            engine_options=row['engine_options'],
            track_options=row['track_options'],
            suspension_options=row['suspension_options'],
            starter_options=row['starter_options'],
            dimensions=row['dimensions'],
            features=row['features'],
            full_specifications=row['full_specifications'],
            marketing_description=row['marketing_description'],
            source_pages=row['source_pages'],
            extraction_confidence=row['extraction_confidence'],
            completeness_score=row['completeness_score'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    # Products
    async def create_product(self, product: Product) -> Product:
        """Create a new product"""
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO products (
                    id, sku, model_code, brand, model_family, model_year,
                    market, price, currency, price_entry_id, base_model_id,
                    resolved_specifications, inheritance_adjustments, selected_variations,
                    html_content, html_generated_at, confidence_score, validation_status,
                    auto_approved, claude_api_calls, claude_processing_ms, total_cost_usd,
                    created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, 
                    $17, $18, $19, $20, $21, $22, $23
                )
            """, product.id, product.sku, product.model_code, product.brand,
                product.model_family, product.model_year, product.market,
                product.price, product.currency, product.price_entry_id,
                product.base_model_id, product.resolved_specifications,
                product.inheritance_adjustments, product.selected_variations,
                product.html_content, product.html_generated_at,
                product.confidence_score, product.validation_status.value,
                product.auto_approved, product.claude_api_calls,
                product.claude_processing_ms, product.total_cost_usd,
                product.created_at)
            
            return product
    
    # Statistics and utilities
    async def count_price_entries(self) -> int:
        """Count total price entries"""
        async with self.connection_pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM price_entries")
    
    async def count_matched_price_entries(self) -> int:
        """Count price entries that have been matched"""
        async with self.connection_pool.acquire() as conn:
            return await conn.fetchval("""
                SELECT COUNT(*) FROM price_entries pe
                JOIN products p ON pe.id = p.price_entry_id
            """)
    
    async def count_unmatched_price_entries(self) -> int:
        """Count price entries that haven't been matched"""
        async with self.connection_pool.acquire() as conn:
            return await conn.fetchval("""
                SELECT COUNT(*) FROM price_entries pe
                LEFT JOIN products p ON pe.id = p.price_entry_id
                WHERE p.id IS NULL
            """)
    
    # Processing Jobs
    async def create_processing_job(self, job: ProcessingJob) -> ProcessingJob:
        """Create a new processing job"""
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO processing_jobs (
                    id, job_type, price_list_id, catalog_id, status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, job.id, job.job_type.value, job.price_list_id, 
                job.catalog_id, job.status.value, job.created_at)
            
            return job
    
    async def get_processing_job_by_price_list(self, price_list_id: UUID) -> Optional[ProcessingJob]:
        """Get processing job by price list ID"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM processing_jobs WHERE price_list_id = $1
                ORDER BY created_at DESC LIMIT 1
            """, price_list_id)
            
            if row:
                return self._row_to_processing_job(row)
            return None
    
    async def get_processing_job_by_catalog(self, catalog_id: UUID) -> Optional[ProcessingJob]:
        """Get processing job by catalog ID"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM processing_jobs WHERE catalog_id = $1
                ORDER BY created_at DESC LIMIT 1
            """, catalog_id)
            
            if row:
                return self._row_to_processing_job(row)
            return None
    
    async def update_processing_job_status(
        self, 
        job_id: UUID, 
        status: JobStatus, 
        error_message: Optional[str] = None
    ):
        """Update processing job status"""
        async with self.connection_pool.acquire() as conn:
            now = datetime.now()
            if status == JobStatus.RUNNING:
                await conn.execute("""
                    UPDATE processing_jobs 
                    SET status = $1, started_at = $2 
                    WHERE id = $3
                """, status.value, now, job_id)
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                await conn.execute("""
                    UPDATE processing_jobs 
                    SET status = $1, completed_at = $2, error_message = $3
                    WHERE id = $4
                """, status.value, now, error_message, job_id)
    
    def _row_to_processing_job(self, row) -> ProcessingJob:
        """Convert database row to ProcessingJob object"""
        from ..models.domain import JobType, JobStatus
        return ProcessingJob(
            id=row['id'],
            job_type=JobType(row['job_type']),
            price_list_id=row['price_list_id'],
            catalog_id=row['catalog_id'],
            status=JobStatus(row['status']),
            progress_percentage=row['progress_percentage'],
            total_items=row['total_items'],
            processed_items=row['processed_items'],
            successful_items=row['successful_items'],
            failed_items=row['failed_items'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            duration_ms=row['duration_ms'],
            error_message=row['error_message'],
            error_details=row['error_details'],
            created_at=row['created_at']
        )