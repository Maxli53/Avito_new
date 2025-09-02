import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from ..models.domain import (
    PriceList, Catalog, ProcessingJob, JobType, JobStatus, ProcessingStatus
)
from ..repositories.database import DatabaseRepository
from ..services.price_extractor import PriceListExtractor
from ..services.catalog_extractor import CatalogExtractor
from ..services.matching_service import MatchingService
from ..services.claude_inheritance import ClaudeInheritanceService


logger = logging.getLogger(__name__)


class MainPipeline:
    """Main orchestrator for the snowmobile processing pipeline"""
    
    def __init__(
        self,
        db_repo: DatabaseRepository,
        price_extractor: PriceListExtractor,
        catalog_extractor: CatalogExtractor,
        matching_service: MatchingService,
        claude_service: ClaudeInheritanceService
    ):
        self.db_repo = db_repo
        self.price_extractor = price_extractor
        self.catalog_extractor = catalog_extractor
        self.matching_service = matching_service
        self.claude_service = claude_service
    
    async def process_new_documents(self) -> Dict[str, Any]:
        """
        Process any new uploaded documents (price lists and catalogs)
        
        Returns:
            Processing summary with statistics
        """
        logger.info("Starting new document processing pipeline")
        
        summary = {
            'price_lists_processed': 0,
            'catalogs_processed': 0,
            'products_generated': 0,
            'errors': [],
            'start_time': datetime.now(),
            'end_time': None
        }
        
        try:
            # Phase 1: Extract from price lists
            price_list_results = await self.extract_price_lists()
            summary['price_lists_processed'] = len(price_list_results)
            
            # Phase 2: Extract from catalogs
            catalog_results = await self.extract_catalogs()
            summary['catalogs_processed'] = len(catalog_results)
            
            # Phase 3: Match price entries to base models
            matching_results = await self.run_matching()
            
            # Phase 4: Generate products using Claude inheritance
            product_results = await self.generate_all_products()
            summary['products_generated'] = len(product_results)
            
            summary['end_time'] = datetime.now()
            summary['total_duration'] = (summary['end_time'] - summary['start_time']).total_seconds()
            
            logger.info(f"Pipeline completed: {summary['products_generated']} products generated in {summary['total_duration']:.1f}s")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            summary['errors'].append(str(e))
            summary['end_time'] = datetime.now()
        
        return summary
    
    async def upload_and_process_price_list(
        self, 
        pdf_path: Path, 
        brand: str, 
        market: str, 
        model_year: int
    ) -> UUID:
        """
        Upload and process a new price list PDF
        
        Args:
            pdf_path: Path to the price list PDF
            brand: Brand name (e.g., "Lynx")
            market: Market code (e.g., "FI")
            model_year: Model year (e.g., 2026)
            
        Returns:
            UUID of the created price list
        """
        logger.info(f"Uploading price list: {pdf_path.name} for {brand} {market} {model_year}")
        
        try:
            # Create price list record
            price_list = PriceList(
                id=uuid4(),
                filename=pdf_path.name,
                brand=brand,
                market=market,
                model_year=model_year,
                status=ProcessingStatus.PENDING,
                uploaded_at=datetime.now()
            )
            
            # Store in database
            stored_price_list = await self.db_repo.create_price_list(price_list)
            
            # Create processing job
            job = ProcessingJob(
                id=uuid4(),
                job_type=JobType.PRICE_EXTRACTION,
                price_list_id=stored_price_list.id,
                status=JobStatus.QUEUED,
                created_at=datetime.now()
            )
            
            await self.db_repo.create_processing_job(job)
            
            # Process asynchronously
            asyncio.create_task(self._process_price_list_async(pdf_path, stored_price_list.id))
            
            logger.info(f"Price list {stored_price_list.id} uploaded and queued for processing")
            
            return stored_price_list.id
            
        except Exception as e:
            logger.error(f"Failed to upload price list {pdf_path.name}: {e}")
            raise
    
    async def upload_and_process_catalog(
        self, 
        pdf_path: Path, 
        brand: str, 
        model_year: int,
        document_type: str = "product_spec_book",
        language: str = "FI"
    ) -> UUID:
        """
        Upload and process a new catalog PDF
        
        Args:
            pdf_path: Path to the catalog PDF
            brand: Brand name (e.g., "Lynx")
            model_year: Model year (e.g., 2026)
            document_type: Type of document (default: "product_spec_book")
            language: Language code (default: "FI")
            
        Returns:
            UUID of the created catalog
        """
        logger.info(f"Uploading catalog: {pdf_path.name} for {brand} {model_year}")
        
        try:
            # Create catalog record
            catalog = Catalog(
                id=uuid4(),
                filename=pdf_path.name,
                brand=brand,
                model_year=model_year,
                document_type=document_type,
                language=language,
                status=ProcessingStatus.PENDING,
                uploaded_at=datetime.now()
            )
            
            # Store in database
            stored_catalog = await self.db_repo.create_catalog(catalog)
            
            # Create processing job
            job = ProcessingJob(
                id=uuid4(),
                job_type=JobType.CATALOG_EXTRACTION,
                catalog_id=stored_catalog.id,
                status=JobStatus.QUEUED,
                created_at=datetime.now()
            )
            
            await self.db_repo.create_processing_job(job)
            
            # Process asynchronously
            asyncio.create_task(self._process_catalog_async(pdf_path, stored_catalog.id))
            
            logger.info(f"Catalog {stored_catalog.id} uploaded and queued for processing")
            
            return stored_catalog.id
            
        except Exception as e:
            logger.error(f"Failed to upload catalog {pdf_path.name}: {e}")
            raise
    
    async def extract_price_lists(self) -> List[Dict[str, Any]]:
        """Extract data from all pending price lists"""
        
        # Get pending price lists
        pending_price_lists = await self.db_repo.get_pending_price_lists()
        
        if not pending_price_lists:
            logger.info("No pending price lists found")
            return []
        
        logger.info(f"Processing {len(pending_price_lists)} pending price lists")
        
        results = []
        
        for price_list in pending_price_lists:
            try:
                # Update status to processing
                await self.db_repo.update_price_list_stats(
                    price_list.id,
                    status=ProcessingStatus.PROCESSING
                )
                
                # For demo purposes, assume PDF files are in data/pdfs/
                pdf_path = Path("data/pdfs") / price_list.filename
                
                if not pdf_path.exists():
                    logger.warning(f"PDF file not found: {pdf_path}")
                    await self.db_repo.update_price_list_stats(
                        price_list.id,
                        status=ProcessingStatus.FAILED
                    )
                    continue
                
                # Extract data
                result = await self.price_extractor.extract_from_pdf(pdf_path, price_list.id)
                
                results.append({
                    'price_list_id': price_list.id,
                    'filename': price_list.filename,
                    'success': result.success,
                    'entries_extracted': result.entries_extracted,
                    'processing_time_ms': result.processing_time_ms
                })
                
            except Exception as e:
                logger.error(f"Failed to process price list {price_list.filename}: {e}")
                await self.db_repo.update_price_list_stats(
                    price_list.id,
                    status=ProcessingStatus.FAILED
                )
                
                results.append({
                    'price_list_id': price_list.id,
                    'filename': price_list.filename,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    async def extract_catalogs(self) -> List[Dict[str, Any]]:
        """Extract data from all pending catalogs"""
        
        # Get pending catalogs
        pending_catalogs = await self.db_repo.get_pending_catalogs()
        
        if not pending_catalogs:
            logger.info("No pending catalogs found")
            return []
        
        logger.info(f"Processing {len(pending_catalogs)} pending catalogs")
        
        results = []
        
        for catalog in pending_catalogs:
            try:
                # Update status to processing
                await self.db_repo.update_catalog_stats(
                    catalog.id,
                    status=ProcessingStatus.PROCESSING
                )
                
                # For demo purposes, assume PDF files are in data/pdfs/
                pdf_path = Path("data/pdfs") / catalog.filename
                
                if not pdf_path.exists():
                    logger.warning(f"PDF file not found: {pdf_path}")
                    await self.db_repo.update_catalog_stats(
                        catalog.id,
                        status=ProcessingStatus.FAILED
                    )
                    continue
                
                # Extract data
                result = await self.catalog_extractor.extract_from_pdf(pdf_path, catalog.id)
                
                results.append({
                    'catalog_id': catalog.id,
                    'filename': catalog.filename,
                    'success': result.success,
                    'models_extracted': result.entries_extracted,
                    'processing_time_ms': result.processing_time_ms
                })
                
            except Exception as e:
                logger.error(f"Failed to process catalog {catalog.filename}: {e}")
                await self.db_repo.update_catalog_stats(
                    catalog.id,
                    status=ProcessingStatus.FAILED
                )
                
                results.append({
                    'catalog_id': catalog.id,
                    'filename': catalog.filename,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    async def run_matching(self) -> Dict[str, Any]:
        """Run matching process for all unmatched price entries"""
        
        logger.info("Starting matching process")
        
        try:
            # Match all unmatched entries
            matching_results = await self.matching_service.match_all_unmatched_entries()
            
            # Get statistics
            stats = await self.matching_service.get_matching_statistics()
            
            logger.info(f"Matching completed: {stats['matched_entries']}/{stats['total_price_entries']} entries matched ({stats['match_rate_percentage']:.1f}%)")
            
            return {
                'total_processed': len(matching_results),
                'successful_matches': sum(1 for r in matching_results if r.matched),
                'failed_matches': sum(1 for r in matching_results if not r.matched),
                'match_rate_percentage': stats['match_rate_percentage'],
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Matching process failed: {e}")
            return {
                'total_processed': 0,
                'successful_matches': 0,
                'failed_matches': 0,
                'error': str(e)
            }
    
    async def generate_all_products(self) -> List[Dict[str, Any]]:
        """Generate products for all matched price entries that don't have products yet"""
        
        logger.info("Starting product generation")
        
        try:
            # Get matched price entries without products
            unprocessed_entries = await self.db_repo.get_matched_entries_without_products()
            
            if not unprocessed_entries:
                logger.info("No unprocessed matched entries found")
                return []
            
            logger.info(f"Generating products for {len(unprocessed_entries)} entries")
            
            results = []
            
            for entry in unprocessed_entries:
                try:
                    # Get matching result to find base model
                    base_model = await self.db_repo.get_matched_base_model_for_entry(entry.id)
                    
                    if not base_model:
                        logger.warning(f"No base model found for matched entry {entry.id}")
                        continue
                    
                    # Generate product using Claude
                    product = await self.claude_service.generate_product(entry.id, base_model.id)
                    
                    results.append({
                        'price_entry_id': entry.id,
                        'product_id': product.id,
                        'sku': product.sku,
                        'success': True,
                        'confidence_score': float(product.confidence_score),
                        'processing_time_ms': product.claude_processing_ms,
                        'cost_usd': float(product.total_cost_usd)
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to generate product for entry {entry.id}: {e}")
                    results.append({
                        'price_entry_id': entry.id,
                        'product_id': None,
                        'success': False,
                        'error': str(e)
                    })
            
            successful_products = sum(1 for r in results if r['success'])
            total_cost = sum(r.get('cost_usd', 0) for r in results if r['success'])
            
            logger.info(f"Product generation completed: {successful_products}/{len(results)} products generated (total cost: ${total_cost:.4f})")
            
            return results
            
        except Exception as e:
            logger.error(f"Product generation failed: {e}")
            return []
    
    async def _process_price_list_async(self, pdf_path: Path, price_list_id: UUID):
        """Process price list asynchronously"""
        try:
            logger.info(f"Starting async processing of price list {price_list_id}")
            
            # Update job status
            job = await self.db_repo.get_processing_job_by_price_list(price_list_id)
            if job:
                await self.db_repo.update_processing_job_status(job.id, JobStatus.RUNNING)
            
            # Extract data
            result = await self.price_extractor.extract_from_pdf(pdf_path, price_list_id)
            
            # Update job status
            if job:
                if result.success:
                    await self.db_repo.update_processing_job_status(job.id, JobStatus.COMPLETED)
                else:
                    await self.db_repo.update_processing_job_status(
                        job.id, 
                        JobStatus.FAILED, 
                        error_message=result.error_message
                    )
            
            logger.info(f"Async processing of price list {price_list_id} completed: {result.success}")
            
        except Exception as e:
            logger.error(f"Async processing of price list {price_list_id} failed: {e}")
            
            # Update job status to failed
            if job:
                await self.db_repo.update_processing_job_status(
                    job.id, 
                    JobStatus.FAILED, 
                    error_message=str(e)
                )
    
    async def _process_catalog_async(self, pdf_path: Path, catalog_id: UUID):
        """Process catalog asynchronously"""
        try:
            logger.info(f"Starting async processing of catalog {catalog_id}")
            
            # Update job status
            job = await self.db_repo.get_processing_job_by_catalog(catalog_id)
            if job:
                await self.db_repo.update_processing_job_status(job.id, JobStatus.RUNNING)
            
            # Extract data
            result = await self.catalog_extractor.extract_from_pdf(pdf_path, catalog_id)
            
            # Update job status
            if job:
                if result.success:
                    await self.db_repo.update_processing_job_status(job.id, JobStatus.COMPLETED)
                else:
                    await self.db_repo.update_processing_job_status(
                        job.id, 
                        JobStatus.FAILED, 
                        error_message=result.error_message
                    )
            
            logger.info(f"Async processing of catalog {catalog_id} completed: {result.success}")
            
        except Exception as e:
            logger.error(f"Async processing of catalog {catalog_id} failed: {e}")
            
            # Update job status to failed
            if job:
                await self.db_repo.update_processing_job_status(
                    job.id, 
                    JobStatus.FAILED, 
                    error_message=str(e)
                )
    
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and statistics"""
        try:
            # Get processing statistics
            price_list_stats = await self.db_repo.get_price_list_statistics()
            catalog_stats = await self.db_repo.get_catalog_statistics()
            product_stats = await self.db_repo.get_product_statistics()
            matching_stats = await self.matching_service.get_matching_statistics()
            generation_stats = await self.claude_service.get_generation_statistics()
            
            return {
                'price_lists': price_list_stats,
                'catalogs': catalog_stats,
                'products': product_stats,
                'matching': matching_stats,
                'generation': generation_stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def cleanup_failed_jobs(self, older_than_hours: int = 24):
        """Clean up failed processing jobs older than specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            cleaned_count = await self.db_repo.cleanup_failed_jobs(cutoff_time)
            
            logger.info(f"Cleaned up {cleaned_count} failed jobs older than {older_than_hours} hours")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup failed jobs: {e}")
            return 0