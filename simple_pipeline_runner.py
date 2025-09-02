#!/usr/bin/env python3
"""
Simple Pipeline Runner
Runs the TEST_DUAL_PARSER_PIPELINE components directly without import issues
"""
import sys
import os
from pathlib import Path

# Add paths for imports
sys.path.append('TEST_DUAL_PARSER_PIPELINE')
sys.path.append('TEST_DUAL_PARSER_PIPELINE/core')
sys.path.append('TEST_DUAL_PARSER_PIPELINE/pipeline')

# Now try to import and run pipeline components
def run_simple_extraction():
    """Run a simple extraction to populate the database"""
    
    print("="*60)
    print("SIMPLE PIPELINE RUNNER")
    print("="*60)
    
    # Import what we need
    try:
        from TEST_DUAL_PARSER_PIPELINE.core.models import ProductData
        from TEST_DUAL_PARSER_PIPELINE.core.database import DatabaseManager
        from TEST_DUAL_PARSER_PIPELINE.pipeline.stage1_extraction.pdf_extractor import PDFExtractor
        
        print("✅ Imports successful")
        
        # Initialize database
        db_path = "TEST_DUAL_PARSER_PIPELINE/test_pipeline.db"
        database = DatabaseManager(db_path)
        
        print(f"✅ Database initialized: {db_path}")
        
        # Initialize PDF extractor
        extractor = PDFExtractor()
        
        print("✅ PDF Extractor initialized")
        
        # Extract from a PDF
        pdf_path = Path("data/SKI-DOO_2026-PRICE_LIST.pdf")  # Use price list instead of spec book
        
        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            return
        
        print(f"📄 Processing PDF: {pdf_path}")
        print(f"   File size: {pdf_path.stat().st_size:,} bytes")
        
        # Extract products
        products = extractor.extract(pdf_path)
        
        print(f"✅ Extracted {len(products)} products")
        
        # Save to database
        if products:
            database.save_product_data(products, clear_existing=True)
            print(f"✅ Saved {len(products)} products to database")
            
            # Show sample product
            sample = products[0]
            print(f"\n📋 Sample product:")
            print(f"   Model Code: {sample.model_code}")
            print(f"   Brand: {sample.brand}")
            print(f"   Price: {sample.price} {sample.currency}")
            print(f"   Model: {sample.malli}")
        
        print(f"\n✅ Pipeline execution completed!")
        print(f"   Database: {db_path}")
        print(f"   Products: {len(products)}")
        
        return db_path, products
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, []


if __name__ == "__main__":
    run_simple_extraction()