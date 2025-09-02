#!/usr/bin/env python3
"""
Snowmobile Dual Parser Pipeline - Main Entry Point

This is the main entry point for the snowmobile product data reconciliation system.
It provides both CLI and API interfaces for processing PDF documents.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional
import argparse
import uvicorn

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import settings, validate_environment
from src.repositories.database import DatabaseRepository
from src.services.price_extractor import PriceListExtractor
from src.services.catalog_extractor import CatalogExtractor
from src.services.matching_service import MatchingService
from src.services.claude_inheritance import ClaudeInheritanceService
from src.pipeline.main_pipeline import MainPipeline


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/pipeline.log')
        ]
    )


async def initialize_services() -> MainPipeline:
    """Initialize all services and return main pipeline"""
    logger = logging.getLogger(__name__)
    
    logger.info("Initializing Snowmobile Dual Parser Pipeline")
    
    # Initialize database repository
    db_repo = DatabaseRepository(settings.database_url)
    await db_repo.initialize()
    logger.info("Database repository initialized")
    
    # Initialize services
    price_extractor = PriceListExtractor(db_repo)
    catalog_extractor = CatalogExtractor(db_repo)
    matching_service = MatchingService(db_repo)
    claude_service = ClaudeInheritanceService(db_repo, settings.claude_api_key)
    
    # Initialize main pipeline
    pipeline = MainPipeline(
        db_repo=db_repo,
        price_extractor=price_extractor,
        catalog_extractor=catalog_extractor,
        matching_service=matching_service,
        claude_service=claude_service
    )
    
    logger.info("All services initialized successfully")
    return pipeline


async def run_cli_pipeline(args):
    """Run pipeline via CLI interface"""
    logger = logging.getLogger(__name__)
    
    try:
        pipeline = await initialize_services()
        
        if args.command == "process":
            logger.info("Starting full pipeline processing")
            result = await pipeline.process_new_documents()
            
            print("\n" + "="*60)
            print("PIPELINE PROCESSING COMPLETE")
            print("="*60)
            print(f"Price Lists Processed: {result['price_lists_processed']}")
            print(f"Catalogs Processed: {result['catalogs_processed']}")
            print(f"Products Generated: {result['products_generated']}")
            print(f"Total Duration: {result.get('total_duration', 0):.2f} seconds")
            
            if result['errors']:
                print(f"Errors: {len(result['errors'])}")
                for error in result['errors']:
                    print(f"  - {error}")
        
        elif args.command == "upload-price-list":
            if not args.pdf_path or not args.brand or not args.market or not args.year:
                print("Error: --pdf-path, --brand, --market, and --year are required for upload-price-list")
                return 1
            
            pdf_path = Path(args.pdf_path)
            if not pdf_path.exists():
                print(f"Error: PDF file not found: {pdf_path}")
                return 1
            
            logger.info(f"Uploading price list: {pdf_path}")
            price_list_id = await pipeline.upload_and_process_price_list(
                pdf_path, args.brand, args.market, args.year
            )
            
            print(f"Price list uploaded successfully!")
            print(f"Price List ID: {price_list_id}")
            print(f"Status: Queued for processing")
        
        elif args.command == "upload-catalog":
            if not args.pdf_path or not args.brand or not args.year:
                print("Error: --pdf-path, --brand, and --year are required for upload-catalog")
                return 1
            
            pdf_path = Path(args.pdf_path)
            if not pdf_path.exists():
                print(f"Error: PDF file not found: {pdf_path}")
                return 1
            
            logger.info(f"Uploading catalog: {pdf_path}")
            catalog_id = await pipeline.upload_and_process_catalog(
                pdf_path, args.brand, args.year
            )
            
            print(f"Catalog uploaded successfully!")
            print(f"Catalog ID: {catalog_id}")
            print(f"Status: Queued for processing")
        
        elif args.command == "status":
            logger.info("Getting pipeline status")
            status = await pipeline.get_pipeline_status()
            
            print("\n" + "="*60)
            print("PIPELINE STATUS")
            print("="*60)
            print(f"Price Lists: {status.get('price_lists', {})}")
            print(f"Catalogs: {status.get('catalogs', {})}")
            print(f"Products: {status.get('products', {})}")
            print(f"Matching: {status.get('matching', {})}")
            print(f"Generation: {status.get('generation', {})}")
        
        return 0
        
    except Exception as e:
        logger.error(f"CLI pipeline failed: {e}")
        print(f"Error: {e}")
        return 1


def run_api_server():
    """Run API server"""
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting API server on {settings.api_host}:{settings.api_port}")
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower()
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Snowmobile Dual Parser Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run API server
  python main.py api
  
  # Process all new documents
  python main.py cli process
  
  # Upload a price list
  python main.py cli upload-price-list --pdf-path price_list.pdf --brand Lynx --market FI --year 2026
  
  # Upload a catalog
  python main.py cli upload-catalog --pdf-path catalog.pdf --brand Lynx --year 2026
  
  # Get pipeline status
  python main.py cli status
        """
    )
    
    subparsers = parser.add_subparsers(dest='mode', help='Operating mode')
    
    # API mode
    api_parser = subparsers.add_parser('api', help='Run API server')
    
    # CLI mode
    cli_parser = subparsers.add_parser('cli', help='Run CLI interface')
    cli_subparsers = cli_parser.add_subparsers(dest='command', help='CLI commands')
    
    # Process command
    process_parser = cli_subparsers.add_parser('process', help='Process all new documents')
    
    # Upload price list command
    upload_price_parser = cli_subparsers.add_parser('upload-price-list', help='Upload price list PDF')
    upload_price_parser.add_argument('--pdf-path', required=True, help='Path to PDF file')
    upload_price_parser.add_argument('--brand', required=True, help='Brand name (e.g., Lynx)')
    upload_price_parser.add_argument('--market', required=True, help='Market code (e.g., FI)')
    upload_price_parser.add_argument('--year', type=int, required=True, help='Model year (e.g., 2026)')
    
    # Upload catalog command
    upload_catalog_parser = cli_subparsers.add_parser('upload-catalog', help='Upload catalog PDF')
    upload_catalog_parser.add_argument('--pdf-path', required=True, help='Path to PDF file')
    upload_catalog_parser.add_argument('--brand', required=True, help='Brand name (e.g., Lynx)')
    upload_catalog_parser.add_argument('--year', type=int, required=True, help='Model year (e.g., 2026)')
    
    # Status command
    status_parser = cli_subparsers.add_parser('status', help='Get pipeline status')
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging()
    
    # Validate environment
    try:
        validate_environment()
    except RuntimeError as e:
        print(f"Configuration Error: {e}")
        return 1
    
    if args.mode == 'api':
        run_api_server()
        return 0
    
    elif args.mode == 'cli':
        if not args.command:
            cli_parser.print_help()
            return 1
        
        return asyncio.run(run_cli_pipeline(args))
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)