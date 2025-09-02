"""
Phase 5 Debug: End-to-End Sample Trace
Traces one specific example through the entire pipeline
"""

import sqlite3
import fitz
from pathlib import Path
from modular_parser import CatalogExtractor
from matching_engine import MatchingEngine, TextNormalizer
from data_models import DualParserConfig, PriceListEntry, CatalogVehicle

def trace_end_to_end_sample():
    print("=== PHASE 5: END-TO-END SAMPLE TRACE ===\n")
    
    print("TRACING: Finnish 'Summit X with Expert Pkg' -> English 'SUMMIT X WITH EXPERT PACKAGE'\n")
    print("=" * 80)
    
    # STEP 1: Extract from price list database
    print("\nSTEP 1: PRICE LIST DATABASE EXTRACTION")
    print("-" * 50)
    
    conn = sqlite3.connect("snowmobile_reconciliation.db")
    cursor = conn.cursor()
    
    # Find a Summit X with Expert Package entry
    cursor.execute("""
        SELECT model_code, malli, paketti, moottori, vari, price, 
               normalized_model_name, normalized_package_name, normalized_engine_spec
        FROM price_entries 
        WHERE malli = 'Summit' AND paketti LIKE '%Expert%'
        LIMIT 1
    """)
    
    price_row = cursor.fetchone()
    conn.close()
    
    if price_row:
        print(f"Found price entry:")
        print(f"  Model Code: {price_row[0]}")
        print(f"  Raw Data:")
        print(f"    malli: '{price_row[1]}'")
        print(f"    paketti: '{price_row[2]}'")  
        print(f"    moottori: '{price_row[3]}'")
        print(f"    vari: '{price_row[4]}'")
        print(f"    price: {price_row[5]} EUR")
        print(f"  Normalized Data:")
        print(f"    model: '{price_row[6]}'")
        print(f"    package: '{price_row[7]}'")
        print(f"    engine: '{price_row[8]}'")
        
        # Create PriceListEntry object
        price_entry = PriceListEntry(
            model_code=price_row[0],
            malli=price_row[1],
            paketti=price_row[2], 
            moottori=price_row[3],
            vari=price_row[4],
            price=price_row[5],
            normalized_model_name=price_row[6],
            normalized_package_name=price_row[7],
            normalized_engine_spec=price_row[8]
        )
        
    else:
        print("No Summit X with Expert Package found in database")
        # Create a test entry
        price_entry = PriceListEntry(
            model_code="TGTP",
            malli="Summit",
            paketti="X with Expert Pkg",
            moottori="850 E-TEC",
            normalized_model_name="SUMMIT",
            normalized_package_name="X WITH EXPERT PKG",
            normalized_engine_spec="850 ETEC"
        )
        print("Using test price entry:")
        print(f"  malli: '{price_entry.malli}' + paketti: '{price_entry.paketti}'")
        print(f"  normalized: '{price_entry.normalized_model_name}' + '{price_entry.normalized_package_name}'")
    
    # STEP 2: PDF catalog extraction  
    print(f"\nSTEP 2: PDF CATALOG EXTRACTION")
    print("-" * 50)
    
    # Find the PDF
    docs_folder = Path("docs")
    pdf_path = list(docs_folder.glob("*SKIDOO*2026*PRODUCT*SPEC*.pdf"))[0]
    
    print(f"Processing PDF: {pdf_path.name}")
    
    # Extract table of contents first (page 4 has the vehicle listing)
    with fitz.open(pdf_path) as pdf:
        toc_page = pdf[3]  # Page 4 (0-indexed)
        toc_text = toc_page.get_text()
        
        print(f"Table of Contents extraction:")
        toc_lines = [line.strip() for line in toc_text.split('\n') if line.strip()]
        
        vehicle_mapping = {}
        for line in toc_lines:
            # Look for pattern: VEHICLE NAME followed by page number
            if 'SUMMIT X WITH EXPERT PACKAGE' in line:
                print(f"  Found: '{line}'")
                # Extract page number (usually at end of line)
                parts = line.split()
                if parts and parts[-1].isdigit():
                    page_num = int(parts[-1])
                    vehicle_mapping[page_num] = 'SUMMIT X WITH EXPERT PACKAGE'
                    print(f"  Mapped to page: {page_num}")
        
        # Now extract from the actual vehicle page
        if vehicle_mapping:
            vehicle_page_num = list(vehicle_mapping.keys())[0]
            vehicle_name = list(vehicle_mapping.values())[0]
            
            print(f"\nExtracting from page {vehicle_page_num}: {vehicle_name}")
            
            vehicle_page = pdf[vehicle_page_num - 1]  # Convert to 0-indexed
            page_text = vehicle_page.get_text()
            
            # Create catalog vehicle object
            config = DualParserConfig()
            extractor = CatalogExtractor(config)
            
            # Manual extraction with known name
            catalog_vehicle = CatalogVehicle(
                name=vehicle_name,
                model_family="SUMMIT",
                package_name="Expert Package",
                page_number=vehicle_page_num
            )
            
            # Extract specs from the page
            specs = extractor._extract_specifications(page_text)
            catalog_vehicle.specifications = specs
            
            print(f"Catalog Vehicle Created:")
            print(f"  name: '{catalog_vehicle.name}'")
            print(f"  model_family: '{catalog_vehicle.model_family}'")
            print(f"  package_name: '{catalog_vehicle.package_name}'")
            print(f"  engine: '{specs.engine}'")
            print(f"  page: {catalog_vehicle.page_number}")
            
        else:
            print("Could not find SUMMIT X WITH EXPERT PACKAGE in table of contents")
            # Create test catalog vehicle
            catalog_vehicle = CatalogVehicle(
                name="SUMMIT X WITH EXPERT PACKAGE",
                model_family="SUMMIT",
                package_name="Expert Package"
            )
    
    # STEP 3: Matching algorithm
    print(f"\nSTEP 3: MATCHING ALGORITHM")
    print("-" * 50)
    
    config = DualParserConfig.from_database("snowmobile_reconciliation.db")
    matching_engine = MatchingEngine(config)
    
    print(f"Matching Configuration:")
    print(f"  exact_threshold: {config.exact_match_threshold}")
    print(f"  normalized_threshold: {config.normalized_match_threshold}")
    print(f"  fuzzy_threshold: {config.fuzzy_match_threshold}")
    
    print(f"\nInput Comparison:")
    print(f"  Price Entry: '{price_entry.malli}' + '{price_entry.paketti}'")
    print(f"  Catalog Vehicle: '{catalog_vehicle.name}'")
    print(f"  Normalized Price: '{price_entry.normalized_model_name}' + '{price_entry.normalized_package_name}'")
    print(f"  Normalized Catalog: '{catalog_vehicle.model_family}' + '{catalog_vehicle.package_name}'")
    
    # Perform matching
    match, result = matching_engine.match_price_to_catalog(price_entry, [catalog_vehicle])
    
    print(f"\nMatching Results:")
    print(f"  Tier 1 (Exact): {result.tier_1_exact_match} (confidence: {result.tier_1_confidence:.3f})")
    print(f"  Tier 2 (Normalized): {result.tier_2_normalized_match} (confidence: {result.tier_2_confidence:.3f})")
    print(f"  Tier 3 (Fuzzy): {result.tier_3_fuzzy_match} (confidence: {result.tier_3_confidence:.3f})")
    print(f"  Final Method: '{result.final_matching_method}'")
    print(f"  Overall Confidence: {result.overall_confidence:.3f}")
    print(f"  Match Found: {match is not None}")
    print(f"  Needs Review: {result.requires_human_review}")
    
    # STEP 4: Manual matching analysis
    print(f"\nSTEP 4: MANUAL MATCHING ANALYSIS")
    print("-" * 50)
    
    normalizer = TextNormalizer()
    
    # Test exact matching logic
    price_model = price_entry.malli or ""
    catalog_family = catalog_vehicle.model_family
    catalog_name = catalog_vehicle.name
    
    print(f"Exact Match Tests:")
    print(f"  '{price_model}' in '{catalog_family}': {price_model.upper() in catalog_family.upper()}")
    print(f"  '{price_model}' in '{catalog_name}': {price_model.upper() in catalog_name.upper()}")
    
    # Test normalized matching
    norm_price_model = normalizer.normalize_model_name(price_entry.malli or "")
    norm_price_package = normalizer.normalize_package_name(price_entry.paketti or "")
    norm_catalog_family = normalizer.normalize_model_name(catalog_vehicle.model_family)
    norm_catalog_name = normalizer.normalize_model_name(catalog_vehicle.name)
    
    print(f"\nNormalized Match Tests:")
    print(f"  Price model normalized: '{price_entry.malli}' -> '{norm_price_model}'")
    print(f"  Price package normalized: '{price_entry.paketti}' -> '{norm_price_package}'")
    print(f"  Catalog family normalized: '{catalog_vehicle.model_family}' -> '{norm_catalog_family}'")
    print(f"  Catalog name normalized: '{catalog_vehicle.name}' -> '{norm_catalog_name}'")
    print(f"  Model match: '{norm_price_model}' in '{norm_catalog_family}': {norm_price_model in norm_catalog_family}")
    print(f"  Model match: '{norm_price_model}' in '{norm_catalog_name}': {norm_price_model in norm_catalog_name}")
    
    # STEP 5: Final result
    print(f"\nSTEP 5: FINAL PIPELINE RESULT")  
    print("-" * 50)
    
    if match:
        print(f"SUCCESS: Match found!")
        print(f"  Finnish: {price_entry.model_code} - '{price_entry.malli} {price_entry.paketti}'")
        print(f"  English: '{match.name}'")
        print(f"  Method: {result.final_matching_method}")
        print(f"  Confidence: {result.overall_confidence:.3f}")
        print(f"  Quality: {'AUTO-ACCEPT' if not result.requires_human_review else 'NEEDS REVIEW'}")
    else:
        print(f"FAILURE: No match found")
        print(f"  Best confidence: {result.overall_confidence:.3f}")
        print(f"  Reason: No matching algorithm succeeded")
    
    print(f"\n" + "=" * 80)
    print("END-TO-END TRACE COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    trace_end_to_end_sample()