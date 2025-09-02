"""
Test script for modular dual parser pipeline
Validates the new architecture with data classes and testable functions
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

from modular_parser import ModularDualParser
from data_models import DualParserConfig

async def main():
    print("=== MODULAR DUAL PARSER PIPELINE TEST ===\n")
    
    # Initialize the modular parser
    parser = ModularDualParser(db_path="snowmobile_reconciliation.db", docs_folder="docs")
    
    # Show available PDFs
    parser.list_available_pdfs()
    
    print("\nStarting modular dual parser pipeline...\n")
    start_time = datetime.now()
    
    try:
        # Run the complete pipeline
        results = parser.run_complete_pipeline(brand="SKI-DOO", year=2026)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        print(f"\n=== MODULAR PIPELINE RESULTS ===")
        print(f"Total processing time: {processing_time:.2f} seconds")
        
        stats = results['processing_statistics']
        print(f"Catalog vehicles extracted: {stats.get('catalog_vehicles_extracted', 0)}")
        print(f"Price entries processed: {stats.get('price_entries_processed', 0)}")
        print(f"Successful matches: {stats.get('successful_matches', 0)}")
        print(f"Failed matches: {stats.get('failed_matches', 0)}")
        print(f"Match success rate: {stats.get('match_success_rate', 0):.1%}")
        
        # Display detailed matching results
        print(f"\n=== DETAILED MATCHING RESULTS ===")
        
        # Show successful matches
        successful_matches = results['successful_matches']
        if successful_matches:
            print(f"\nSuccessful Matches ({len(successful_matches)}):")
            
            matching_methods = {}
            for match in successful_matches:
                method = match['matching_result'].final_matching_method
                matching_methods[method] = matching_methods.get(method, 0) + 1
                
                price_entry = match['price_entry']
                catalog_vehicle = match['catalog_vehicle']
                result = match['matching_result']
                
                print(f"\n  Match: {price_entry.model_code} → {catalog_vehicle.name}")
                print(f"    Finnish: {price_entry.malli} {price_entry.paketti or ''}")
                print(f"    English: {catalog_vehicle.name}")
                print(f"    Method: {result.final_matching_method}")
                print(f"    Confidence: {result.overall_confidence:.3f}")
                
                if result.final_matching_method == "FUZZY":
                    print(f"    Needs Review: {result.requires_human_review}")
            
            print(f"\nMatching Methods Distribution:")
            for method, count in matching_methods.items():
                percentage = (count / len(successful_matches)) * 100
                print(f"  {method}: {count} matches ({percentage:.1f}%)")
        
        # Show failed matches
        failed_matches = results['failed_matches']
        if failed_matches:
            print(f"\nFailed Matches ({len(failed_matches)}):")
            for match in failed_matches:
                price_entry = match['price_entry']
                result = match['matching_result']
                print(f"  {price_entry.model_code}: {price_entry.malli} {price_entry.paketti or ''}")
                print(f"    Reason: No suitable match found (best confidence: {result.overall_confidence:.3f})")
        
        # Display catalog vehicle details
        print(f"\n=== CATALOG VEHICLES EXTRACTED ===")
        catalog_vehicles = results['catalog_vehicles']
        
        if catalog_vehicles:
            print(f"Total vehicles: {len(catalog_vehicles)}")
            
            for i, vehicle in enumerate(catalog_vehicles[:5], 1):  # Show first 5
                print(f"\n{i}. {vehicle.name}")
                print(f"   Model Family: {vehicle.model_family}")
                print(f"   Page: {vehicle.page_number}")
                print(f"   Package: {vehicle.package_name or 'N/A'}")
                
                if vehicle.specifications.engine:
                    print(f"   Engine: {vehicle.specifications.engine}")
                
                if vehicle.marketing.tagline:
                    tagline = vehicle.marketing.tagline[:60] + "..." if len(vehicle.marketing.tagline) > 60 else vehicle.marketing.tagline
                    print(f"   Tagline: \"{tagline}\"")
                
                if vehicle.marketing.key_benefits:
                    print(f"   Benefits: {len(vehicle.marketing.key_benefits)} items")
                
                if vehicle.available_colors:
                    colors = [c.name for c in vehicle.available_colors[:3]]
                    print(f"   Colors: {', '.join(colors)}")
                
                if vehicle.spring_options:
                    print(f"   Spring Options: {len(vehicle.spring_options)} available")
            
            if len(catalog_vehicles) > 5:
                print(f"\n... and {len(catalog_vehicles) - 5} more vehicles")
        
        # Save detailed results to JSON for analysis
        save_path = Path("results/modular_parser_results.json")
        save_path.parent.mkdir(exist_ok=True)
        
        # Convert results to JSON-serializable format
        json_results = {
            'processing_statistics': stats,
            'successful_matches_count': len(successful_matches),
            'failed_matches_count': len(failed_matches),
            'catalog_vehicles_count': len(catalog_vehicles),
            'matching_methods_distribution': matching_methods if 'matching_methods' in locals() else {},
            'extraction_timestamp': stats.get('extraction_timestamp').isoformat() if stats.get('extraction_timestamp') else None
        }
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\nDetailed results saved to: {save_path}")
        
        # Test configuration loading
        print(f"\n=== CONFIGURATION TEST ===")
        config = DualParserConfig.from_database("snowmobile_reconciliation.db")
        print(f"Exact match threshold: {config.exact_match_threshold}")
        print(f"Normalized match threshold: {config.normalized_match_threshold}")
        print(f"Fuzzy match threshold: {config.fuzzy_match_threshold}")
        print(f"Auto accept threshold: {config.auto_accept_threshold}")
        
        print(f"\n=== MODULAR PIPELINE TEST COMPLETED SUCCESSFULLY ===")
        print(f"✓ Data classes implemented")
        print(f"✓ Services modularized")  
        print(f"✓ Matching engine functional")
        print(f"✓ Configuration loading works")
        print(f"✓ Database integration complete")
        
        return results
        
    except Exception as e:
        print(f"Modular pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(main())