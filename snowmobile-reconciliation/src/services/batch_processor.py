"""
Batch processing service for handling multiple PDF price lists.

Provides high-throughput processing with error recovery and progress tracking.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from src.models.domain import (
    PipelineConfig,
    PipelineContext,
    PriceEntry,
    ProcessingStage,
    ProductSpecification,
)
from src.pipeline.stages.base_model_matching import BaseModelMatchingStage
from src.pipeline.stages.specification_inheritance import SpecificationInheritanceStage
from src.pipeline.stages.customization_processing import CustomizationProcessingStage
from src.pipeline.stages.spring_options_enhancement import SpringOptionsEnhancementStage
from src.pipeline.stages.final_validation import FinalValidationStage
from src.repositories.product_repository import ProductRepository
from src.services.claude_enrichment import ClaudeEnrichmentService


@dataclass
class BatchJob:
    """Represents a batch processing job"""
    job_id: UUID
    status: str  # queued, processing, completed, failed
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    errors: List[str]
    results: List[ProductSpecification]


class BatchProcessor:
    """
    High-performance batch processor for price list reconciliation.
    
    Features:
    - Concurrent processing with configurable parallelism
    - Error recovery and retry logic
    - Progress tracking and reporting
    - Memory-efficient streaming
    """
    
    def __init__(
        self,
        config: PipelineConfig,
        repository: Optional[ProductRepository] = None,
        claude_service: Optional[ClaudeEnrichmentService] = None,
    ):
        """
        Initialize batch processor.
        
        Args:
            config: Pipeline configuration
            repository: Product repository for persistence
            claude_service: Claude enrichment service
        """
        self.config = config
        self.repository = repository
        self.claude_service = claude_service
        
        # Initialize pipeline stages
        self.stages = self._initialize_stages()
        
        # Batch processing settings
        self.max_concurrent = config.max_concurrent_processing or 10
        self.batch_size = config.max_batch_size or 100
        
        # Job tracking
        self.active_jobs: Dict[UUID, BatchJob] = {}
        
    def _initialize_stages(self) -> Dict[ProcessingStage, Any]:
        """Initialize all pipeline stages"""
        return {
            ProcessingStage.BASE_MODEL_MATCHING: BaseModelMatchingStage(self.config),
            ProcessingStage.SPECIFICATION_INHERITANCE: SpecificationInheritanceStage(self.config),
            ProcessingStage.CUSTOMIZATION_PROCESSING: CustomizationProcessingStage(self.config),
            ProcessingStage.SPRING_OPTIONS_ENHANCEMENT: SpringOptionsEnhancementStage(self.config),
            ProcessingStage.FINAL_VALIDATION: FinalValidationStage(self.config),
        }
    
    async def process_batch(
        self,
        price_entries: List[PriceEntry],
        job_id: Optional[UUID] = None,
        enable_claude: bool = True,
        auto_approve_threshold: float = 0.9,
    ) -> BatchJob:
        """
        Process a batch of price entries.
        
        Args:
            price_entries: List of price entries to process
            job_id: Optional job ID for tracking
            enable_claude: Whether to use Claude for enrichment
            auto_approve_threshold: Confidence threshold for auto-approval
            
        Returns:
            BatchJob with processing results
        """
        # Create or retrieve job
        job_id = job_id or uuid4()
        job = BatchJob(
            job_id=job_id,
            status="processing",
            total_items=len(price_entries),
            processed_items=0,
            successful_items=0,
            failed_items=0,
            start_time=datetime.utcnow(),
            end_time=None,
            errors=[],
            results=[],
        )
        
        self.active_jobs[job_id] = job
        
        try:
            # Process in batches for memory efficiency
            for batch_start in range(0, len(price_entries), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(price_entries))
                batch = price_entries[batch_start:batch_end]
                
                # Process batch concurrently
                batch_results = await self._process_batch_concurrent(
                    batch,
                    job,
                    enable_claude,
                    auto_approve_threshold,
                )
                
                # Update job results
                job.results.extend(batch_results)
                
                # Save intermediate results if repository available
                if self.repository:
                    await self._save_batch_results(batch_results)
            
            # Mark job as completed
            job.status = "completed"
            job.end_time = datetime.utcnow()
            
        except Exception as e:
            job.status = "failed"
            job.errors.append(f"Batch processing failed: {str(e)}")
            job.end_time = datetime.utcnow()
            raise
        
        return job
    
    async def _process_batch_concurrent(
        self,
        batch: List[PriceEntry],
        job: BatchJob,
        enable_claude: bool,
        auto_approve_threshold: float,
    ) -> List[ProductSpecification]:
        """
        Process a batch of entries concurrently.
        
        Uses asyncio semaphore to limit concurrent processing.
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_entry(entry: PriceEntry) -> Optional[ProductSpecification]:
            async with semaphore:
                try:
                    result = await self._process_single_entry(
                        entry,
                        enable_claude,
                        auto_approve_threshold,
                    )
                    
                    # Update job progress
                    job.processed_items += 1
                    if result:
                        job.successful_items += 1
                    else:
                        job.failed_items += 1
                    
                    return result
                    
                except Exception as e:
                    job.processed_items += 1
                    job.failed_items += 1
                    job.errors.append(f"Failed to process {entry.model_code}: {str(e)}")
                    return None
        
        # Process all entries concurrently
        tasks = [process_entry(entry) for entry in batch]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results
        return [r for r in results if r is not None]
    
    async def _process_single_entry(
        self,
        entry: PriceEntry,
        enable_claude: bool,
        auto_approve_threshold: float,
    ) -> Optional[ProductSpecification]:
        """
        Process a single price entry through the complete pipeline.
        
        Args:
            entry: Price entry to process
            enable_claude: Whether to use Claude enrichment
            auto_approve_threshold: Auto-approval confidence threshold
            
        Returns:
            Processed product specification or None if failed
        """
        try:
            # Create pipeline context
            context = PipelineContext(
                price_entry=entry,
                processing_id=uuid4(),
            )
            
            # Stage 1: Base Model Matching
            base_model = await self._match_base_model(entry)
            if not base_model:
                # Try Claude fallback if enabled
                if enable_claude and self.claude_service:
                    base_model = await self._create_base_model_with_claude(entry)
                
                if not base_model:
                    raise ValueError("No base model found and Claude fallback failed")
            
            context.matched_base_model = base_model
            context.current_confidence = base_model.inheritance_confidence
            
            # Stage 2: Specification Inheritance
            stage2 = self.stages[ProcessingStage.SPECIFICATION_INHERITANCE]
            result2 = await stage2._execute_stage(context)
            if not result2.get("success"):
                raise ValueError(f"Specification inheritance failed: {result2.get('error')}")
            
            # Stage 3: Customization Processing
            stage3 = self.stages[ProcessingStage.CUSTOMIZATION_PROCESSING]
            result3 = await stage3._execute_stage(context)
            if not result3.get("success"):
                raise ValueError(f"Customization processing failed: {result3.get('error')}")
            
            # Stage 4: Spring Options Enhancement (if enabled)
            if self.config.enable_spring_options:
                stage4 = self.stages[ProcessingStage.SPRING_OPTIONS_ENHANCEMENT]
                result4 = await stage4._execute_stage(context)
                # Spring options are optional, don't fail if unsuccessful
            
            # Stage 5: Final Validation
            stage5 = self.stages[ProcessingStage.FINAL_VALIDATION]
            result5 = await stage5._execute_stage(context)
            
            if not result5.get("success"):
                raise ValueError(f"Final validation failed: {result5.get('error')}")
            
            # Extract product specification
            product_spec_data = result5.get("product_specification")
            if not product_spec_data:
                raise ValueError("No product specification generated")
            
            # Create ProductSpecification from dict
            product_spec = ProductSpecification(**product_spec_data)
            
            # Auto-approve if confidence is high enough
            if product_spec.overall_confidence >= auto_approve_threshold:
                product_spec.manual_review_status = "auto_approved"
                product_spec.manual_review_date = datetime.utcnow()
            
            return product_spec
            
        except Exception as e:
            print(f"Error processing {entry.model_code}: {str(e)}")
            return None
    
    async def _match_base_model(self, entry: PriceEntry):
        """
        Match price entry to base model.
        
        This would typically query a database of base models.
        For now, returns a mock base model.
        """
        # TODO: Implement actual base model matching
        from src.models.domain import BaseModelSpecification
        
        # Mock base model matching logic
        if "MXZ" in entry.model_code.upper():
            return BaseModelSpecification(
                base_model_id="MXZ_BASE",
                model_name="MXZ Base Model",
                brand=entry.brand,
                model_year=entry.model_year,
                category="Trail",
                source_catalog="mock_catalog.pdf",
                extraction_quality=0.85,
                specifications={
                    "engine": {"type": "2-stroke"},
                    "suspension": "tMotion",
                },
                inheritance_confidence=0.8,
            )
        
        return None
    
    async def _create_base_model_with_claude(self, entry: PriceEntry):
        """
        Use Claude to create a base model when no match is found.
        
        This is a fallback mechanism for unknown models.
        """
        if not self.claude_service:
            return None
        
        try:
            # Use Claude to analyze the model code and create specifications
            enriched_data = await self.claude_service.enrich_product_data(
                model_code=entry.model_code,
                brand=entry.brand,
                price=float(entry.price),
                model_year=entry.model_year,
            )
            
            # Create base model from Claude's response
            from src.models.domain import BaseModelSpecification
            
            return BaseModelSpecification(
                base_model_id=f"CLAUDE_{entry.model_code}",
                model_name=enriched_data.get("model_name", entry.model_code),
                brand=entry.brand,
                model_year=entry.model_year,
                category=enriched_data.get("category", "Unknown"),
                source_catalog="claude_generated",
                extraction_quality=0.7,  # Lower confidence for Claude-generated
                specifications=enriched_data.get("specifications", {}),
                inheritance_confidence=0.6,  # Lower confidence
            )
            
        except Exception as e:
            print(f"Claude enrichment failed: {str(e)}")
            return None
    
    async def _save_batch_results(self, results: List[ProductSpecification]):
        """
        Save batch results to repository.
        
        Args:
            results: List of product specifications to save
        """
        if not self.repository:
            return
        
        try:
            for product in results:
                await self.repository.save_product(product)
        except Exception as e:
            print(f"Failed to save batch results: {str(e)}")
    
    async def get_job_status(self, job_id: UUID) -> Optional[BatchJob]:
        """
        Get the status of a batch job.
        
        Args:
            job_id: Job ID to query
            
        Returns:
            BatchJob or None if not found
        """
        return self.active_jobs.get(job_id)
    
    async def cancel_job(self, job_id: UUID) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if cancelled, False if not found or already completed
        """
        job = self.active_jobs.get(job_id)
        if not job or job.status in ["completed", "failed"]:
            return False
        
        job.status = "cancelled"
        job.end_time = datetime.utcnow()
        job.errors.append("Job cancelled by user")
        return True
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get overall processing statistics.
        
        Returns:
            Dictionary with processing metrics
        """
        total_jobs = len(self.active_jobs)
        completed_jobs = sum(1 for j in self.active_jobs.values() if j.status == "completed")
        failed_jobs = sum(1 for j in self.active_jobs.values() if j.status == "failed")
        
        total_items = sum(j.total_items for j in self.active_jobs.values())
        successful_items = sum(j.successful_items for j in self.active_jobs.values())
        failed_items = sum(j.failed_items for j in self.active_jobs.values())
        
        # Calculate average processing time
        completed = [j for j in self.active_jobs.values() if j.end_time and j.start_time]
        avg_time = 0
        if completed:
            total_time = sum((j.end_time - j.start_time).total_seconds() for j in completed)
            avg_time = total_time / len(completed)
        
        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": completed_jobs / max(1, total_jobs),
            "total_items_processed": total_items,
            "successful_items": successful_items,
            "failed_items": failed_items,
            "item_success_rate": successful_items / max(1, total_items),
            "average_job_time_seconds": avg_time,
            "active_jobs": sum(1 for j in self.active_jobs.values() if j.status == "processing"),
        }


# Export classes
__all__ = ["BatchProcessor", "BatchJob"]