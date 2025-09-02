"""
Pipeline Orchestrator - Main Entry Point
Coordinates the entire 5-stage pipeline with error handling, monitoring, and statistics
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from core import DatabaseManager, ProductData, PipelineStats, PipelineStage
from config import get_config
from pipeline.stage1_extraction import PDFExtractor, LLMExtractor
from pipeline.stage2_matching import BERTMatcher
from pipeline.stage3_validation import InternalValidator
from pipeline.stage4_generation import AvitoXMLGenerator
from pipeline.stage5_upload import FTPUploader, ProcessingMonitor

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Complete pipeline execution result"""
    success: bool
    products_processed: int
    products_validated: int
    xml_generated: bool
    upload_successful: bool = False
    
    # Stage statistics
    extraction_stats: Optional[PipelineStats] = None
    matching_stats: Optional[PipelineStats] = None
    validation_stats: Optional[PipelineStats] = None
    generation_stats: Optional[PipelineStats] = None
    upload_stats: Optional[PipelineStats] = None
    
    # Results
    extracted_products: List[ProductData] = field(default_factory=list)
    validated_products: List[ProductData] = field(default_factory=list)
    generated_xml: Optional[str] = None
    output_file_path: Optional[Path] = None
    
    # Execution metadata
    total_processing_time: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class PipelineOrchestrator:
    """
    Main pipeline orchestrator coordinating all 5 stages
    
    Provides:
    - End-to-end pipeline execution
    - Error handling and recovery
    - Performance monitoring and statistics
    - Flexible configuration support
    - Database integration
    """
    
    def __init__(self, database_path: Optional[str] = None):
        """
        Initialize pipeline orchestrator
        
        Args:
            database_path: Optional custom database path
        """
        self.config = get_config()
        
        # Initialize database
        db_path = database_path or "snowmobile_reconciliation.db"
        self.database = DatabaseManager(db_path)
        
        # Initialize pipeline components
        self.extractor = PDFExtractor(config=self.config.extraction.__dict__)
        self.matcher = BERTMatcher(config=self.config.matching.__dict__)
        self.validator = InternalValidator(config=self.config.validation.__dict__)
        self.generator = AvitoXMLGenerator()
        self.uploader = FTPUploader()
        self.monitor = ProcessingMonitor()
        
        # Statistics tracking
        self.execution_history: List[PipelineResult] = []
        
        logger.info("Pipeline orchestrator initialized successfully")
    
    def execute_complete_pipeline(
        self,
        pdf_path: Path,
        extract_data: bool = True,
        upload_xml: bool = False,
        save_to_database: bool = True
    ) -> PipelineResult:
        """
        Execute the complete 5-stage pipeline
        
        Args:
            pdf_path: Path to input PDF file
            extract_data: Whether to extract data or use existing database data
            upload_xml: Whether to upload generated XML to Avito
            save_to_database: Whether to save results to database
            
        Returns:
            PipelineResult with comprehensive execution details
        """
        result = PipelineResult(
            success=False,
            products_processed=0,
            products_validated=0,
            xml_generated=False,
            start_time=datetime.now()
        )
        
        try:
            logger.info(f"Starting complete pipeline execution for {pdf_path}")
            
            # Stage 1: Data Extraction
            if extract_data:
                result = self._execute_extraction_stage(pdf_path, result)
                if not result.success:
                    return result
            else:
                logger.info("Skipping extraction - loading from database")
                result.extracted_products = self.database.load_product_data()
                if not result.extracted_products:
                    result.errors.append("No products found in database")
                    return result
            
            result.products_processed = len(result.extracted_products)
            
            # Stage 2: Matching Engine
            result = self._execute_matching_stage(result)
            if not result.success:
                return result
            
            # Stage 3: Validation
            result = self._execute_validation_stage(result)
            if not result.success:
                return result
            
            # Stage 4: XML Generation
            result = self._execute_generation_stage(result)
            if not result.success:
                return result
            
            # Stage 5: Upload Pipeline (optional)
            if upload_xml and result.generated_xml:
                result = self._execute_upload_stage(result)
            
            # Save results to database
            if save_to_database:
                self._save_results_to_database(result)
            
            # Finalize results
            result.end_time = datetime.now()
            result.total_processing_time = (
                result.end_time - result.start_time
            ).total_seconds()
            
            result.success = True
            
            # Add to execution history
            self.execution_history.append(result)
            
            logger.info(
                f"Pipeline execution completed successfully: "
                f"{result.products_validated}/{result.products_processed} products validated "
                f"in {result.total_processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            result.errors.append(f"Pipeline execution failed: {str(e)}")
            result.end_time = datetime.now()
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            return result
    
    def _execute_extraction_stage(self, pdf_path: Path, result: PipelineResult) -> PipelineResult:
        """Execute Stage 1: Data Extraction"""
        try:
            logger.info("Stage 1: Starting data extraction")
            
            # Extract products from PDF
            products = self.extractor.extract_with_hooks(pdf_path)
            
            if not products:
                result.errors.append("No products extracted from PDF")
                return result
            
            result.extracted_products = products
            result.extraction_stats = self.extractor.get_stats()
            
            logger.info(f"Stage 1 completed: {len(products)} products extracted")
            return result
            
        except Exception as e:
            result.errors.append(f"Extraction stage failed: {str(e)}")
            logger.error(f"Stage 1 failed: {e}")
            return result
    
    def _execute_matching_stage(self, result: PipelineResult) -> PipelineResult:
        """Execute Stage 2: Matching Engine"""
        try:
            logger.info("Stage 2: Starting semantic matching")
            
            # Load catalog data
            catalog_data = self.database.load_catalog_data()  # This method would need to be added
            if catalog_data:
                self.matcher.load_catalog_data(catalog_data)
                
                # Match products
                match_results = self.matcher.match_products(result.extracted_products)
                result.matching_stats = self.matcher.get_stats()
                
                logger.info(
                    f"Stage 2 completed: {result.matching_stats.successful} successful matches"
                )
            else:
                result.warnings.append("No catalog data available for matching")
            
            return result
            
        except Exception as e:
            result.errors.append(f"Matching stage failed: {str(e)}")
            logger.error(f"Stage 2 failed: {e}")
            return result
    
    def _execute_validation_stage(self, result: PipelineResult) -> PipelineResult:
        """Execute Stage 3: Validation"""
        try:
            logger.info("Stage 3: Starting validation")
            
            # Validate all products
            validation_results = self.validator.validate_products(result.extracted_products)
            
            # Filter validated products
            result.validated_products = [
                product for product, validation in zip(result.extracted_products, validation_results)
                if validation.success
            ]
            
            result.products_validated = len(result.validated_products)
            result.validation_stats = self.validator.get_stats()
            
            if not result.validated_products:
                result.errors.append("No products passed validation")
                return result
            
            logger.info(
                f"Stage 3 completed: {result.products_validated} products validated "
                f"({result.validation_stats.success_rate:.1f}% success rate)"
            )
            
            return result
            
        except Exception as e:
            result.errors.append(f"Validation stage failed: {str(e)}")
            logger.error(f"Stage 3 failed: {e}")
            return result
    
    def _execute_generation_stage(self, result: PipelineResult) -> PipelineResult:
        """Execute Stage 4: XML Generation"""
        try:
            logger.info("Stage 4: Starting XML generation")
            
            # Generate XML for validated products
            xml_strings = self.generator.generate_xml_for_products(result.validated_products)
            
            if not xml_strings:
                result.errors.append("No XML generated")
                return result
            
            # Combine XML strings
            result.generated_xml = "\\n".join(xml_strings)
            result.xml_generated = True
            result.generation_stats = self.generator.get_stats()
            
            # Save XML to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"avito_snowmobiles_{timestamp}.xml"
            result.output_file_path = Path(output_filename)
            
            with open(result.output_file_path, 'w', encoding='utf-8') as f:
                f.write(result.generated_xml)
            
            logger.info(
                f"Stage 4 completed: XML generated with {len(xml_strings)} products "
                f"({len(result.generated_xml)} characters) -> {result.output_file_path}"
            )
            
            return result
            
        except Exception as e:
            result.errors.append(f"Generation stage failed: {str(e)}")
            logger.error(f"Stage 4 failed: {e}")
            return result
    
    def _execute_upload_stage(self, result: PipelineResult) -> PipelineResult:
        """Execute Stage 5: Upload Pipeline"""
        try:
            logger.info("Stage 5: Starting FTP upload")
            
            # Upload XML content
            filename = result.output_file_path.name if result.output_file_path else "snowmobile_catalog.xml"
            upload_success = self.uploader.upload_xml_content(result.generated_xml, filename)
            
            result.upload_successful = upload_success
            result.upload_stats = self.uploader.get_stats()
            
            if upload_success:
                # Record upload in monitoring system
                self.monitor.record_upload(filename, datetime.now(), True)
                
                # Show processing window information
                processing_info = self.monitor.wait_for_processing()
                result.warnings.append(
                    f"Upload successful. {processing_info['message']}"
                )
                
                logger.info("Stage 5 completed: Upload successful")
            else:
                result.warnings.append("Upload failed")
                logger.warning("Stage 5: Upload failed")
            
            return result
            
        except Exception as e:
            result.errors.append(f"Upload stage failed: {str(e)}")
            logger.error(f"Stage 5 failed: {e}")
            return result
    
    def _save_results_to_database(self, result: PipelineResult) -> None:
        """Save pipeline results to database"""
        try:
            # Save extracted products
            if result.extracted_products:
                self.database.save_product_data(result.extracted_products, clear_existing=True)
            
            # Save validation results would be implemented here
            # Save match results would be implemented here
            
            logger.info("Pipeline results saved to database")
            
        except Exception as e:
            logger.error(f"Failed to save results to database: {e}")
            result.warnings.append(f"Database save failed: {str(e)}")
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        if not self.execution_history:
            return {"message": "No pipeline executions recorded"}
        
        recent_executions = self.execution_history[-10:]  # Last 10 executions
        
        total_executions = len(self.execution_history)
        successful_executions = len([r for r in self.execution_history if r.success])
        
        avg_processing_time = sum(
            r.total_processing_time for r in recent_executions 
            if r.total_processing_time
        ) / len(recent_executions)
        
        avg_products_processed = sum(r.products_processed for r in recent_executions) / len(recent_executions)
        avg_validation_rate = sum(
            (r.products_validated / r.products_processed) * 100 
            for r in recent_executions if r.products_processed > 0
        ) / len(recent_executions)
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": (successful_executions / total_executions) * 100,
            "average_processing_time": avg_processing_time,
            "average_products_processed": avg_products_processed,
            "average_validation_rate": avg_validation_rate,
            "recent_executions": len(recent_executions),
            "last_execution": self.execution_history[-1].start_time.isoformat() if self.execution_history else None
        }
    
    def print_execution_summary(self, result: PipelineResult) -> None:
        """Print formatted execution summary"""
        print("\\n" + "="*80)
        print("AVITO PIPELINE EXECUTION SUMMARY")
        print("="*80)
        
        # Overall status
        status = "SUCCESS" if result.success else "FAILED"
        print(f"Status: {status}")
        print(f"Processing Time: {result.total_processing_time:.2f}s")
        print()
        
        # Stage breakdown
        print("STAGE BREAKDOWN:")
        stages = [
            ("Extraction", result.extraction_stats),
            ("Matching", result.matching_stats), 
            ("Validation", result.validation_stats),
            ("Generation", result.generation_stats),
            ("Upload", result.upload_stats)
        ]
        
        for stage_name, stats in stages:
            if stats:
                print(f"  {stage_name:12}: {stats.successful}/{stats.total_processed} successful ({stats.success_rate:.1f}%)")
            else:
                print(f"  {stage_name:12}: Not executed")
        
        print()
        
        # Results
        print("RESULTS:")
        print(f"  Products Extracted: {len(result.extracted_products)}")
        print(f"  Products Validated: {result.products_validated}")
        print(f"  XML Generated: {'Yes' if result.xml_generated else 'No'}")
        print(f"  Upload Successful: {'Yes' if result.upload_successful else 'No'}")
        
        if result.output_file_path:
            print(f"  Output File: {result.output_file_path}")
        
        # Warnings and errors
        if result.warnings:
            print(f"\\n  Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"    • {warning}")
        
        if result.errors:
            print(f"\\n  Errors ({len(result.errors)}):")
            for error in result.errors:
                print(f"    • {error}")
        
        print("="*80)


def main():
    """Main pipeline execution function"""
    import sys
    import argparse
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Avito Snowmobile Pipeline")
    parser.add_argument("pdf_path", type=Path, help="Path to PDF file to process")
    parser.add_argument("--extract", action="store_true", default=True, help="Extract data from PDF")
    parser.add_argument("--upload", action="store_true", default=False, help="Upload XML to Avito")
    parser.add_argument("--database", type=str, help="Database path")
    
    args = parser.parse_args()
    
    # Validate input
    if not args.pdf_path.exists():
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    try:
        # Initialize and execute pipeline
        orchestrator = PipelineOrchestrator(args.database)
        result = orchestrator.execute_complete_pipeline(
            pdf_path=args.pdf_path,
            extract_data=args.extract,
            upload_xml=args.upload
        )
        
        # Display results
        orchestrator.print_execution_summary(result)
        
        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
        
    except Exception as e:
        print(f"Pipeline execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()