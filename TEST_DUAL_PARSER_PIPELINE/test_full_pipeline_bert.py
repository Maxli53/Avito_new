"""
Test Full Pipeline with BERT-Enhanced Matching
Tests the complete modular dual parser with BERT Tier 3 semantic matching
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from bert_matching_engine import BERTEnhancedMatchingEngine
from data_models import DualParserConfig

# Import original modular parser and replace matching engine
from modular_parser import ModularDualParser

class BERTEnhancedDualParser(ModularDualParser):
    """Enhanced dual parser with BERT semantic matching"""
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db", docs_folder: str = "docs"):
        super().__init__(db_path, docs_folder)
        
        # Replace the matching engine with BERT-enhanced version
        self.matching_engine = BERTEnhancedMatchingEngine(self.config)
        print("Dual parser initialized with BERT-enhanced matching engine")

async def main():
    print("=== FULL PIPELINE WITH BERT-ENHANCED MATCHING ===\n")
    
    # Initialize the BERT-enhanced parser
    parser = BERTEnhancedDualParser(db_path="snowmobile_reconciliation.db", docs_folder="docs")
    
    # Show available PDFs
    print("Available PDFs:")
    parser.list_available_pdfs()
    
    print("\nStarting BERT-enhanced dual parser pipeline...\n")
    start_time = datetime.now()
    
    try:
        # Run the complete pipeline with BERT matching
        results = parser.run_complete_pipeline(brand="SKI-DOO", year=2026)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        print(f"\n=== BERT-ENHANCED PIPELINE RESULTS ===")
        print(f"Total processing time: {processing_time:.2f} seconds")
        
        stats = results['processing_statistics']
        print(f"Catalog vehicles extracted: {stats.get('catalog_vehicles_extracted', 0)}")
        print(f"Price entries processed: {stats.get('price_entries_processed', 0)}")
        print(f"Successful matches: {stats.get('successful_matches', 0)}")
        print(f"Failed matches: {stats.get('failed_matches', 0)}")
        print(f"Match success rate: {stats.get('match_success_rate', 0):.1%}")
        
        # Show improvement vs original
        print(f"\n=== IMPROVEMENT ANALYSIS ===")
        original_success_rate = 0.0  # From our previous tests
        new_success_rate = stats.get('match_success_rate', 0)
        improvement = new_success_rate - original_success_rate
        
        print(f"Original pipeline success rate: {original_success_rate:.1%}")
        print(f"BERT-enhanced success rate: {new_success_rate:.1%}")
        print(f"Improvement: +{improvement:.1%}")
        
        # Display detailed matching results
        print(f"\n=== MATCHING METHOD BREAKDOWN ===")
        
        successful_matches = results['successful_matches']
        if successful_matches:
            matching_methods = {}
            for match in successful_matches:
                method = match['matching_result'].final_matching_method
                matching_methods[method] = matching_methods.get(method, 0) + 1
            
            print(f"Total successful matches: {len(successful_matches)}")
            for method, count in matching_methods.items():
                percentage = (count / len(successful_matches)) * 100
                print(f"  {method}: {count} matches ({percentage:.1f}%)")
            
            # Show sample successful matches
            print(f"\n=== SAMPLE SUCCESSFUL MATCHES ===")
            for i, match in enumerate(successful_matches[:5], 1):  # Show first 5
                price_entry = match['price_entry']
                catalog_vehicle = match['catalog_vehicle'] 
                result = match['matching_result']
                
                print(f"\n{i}. {price_entry.model_code}: {price_entry.malli} {price_entry.paketti or ''}")
                print(f"   -> {catalog_vehicle.name}")
                print(f"   Method: {result.final_matching_method}")
                print(f"   Confidence: {result.overall_confidence:.3f}")
                print(f"   Review needed: {'Yes' if result.requires_human_review else 'No'}")
        
        # Show failed matches for analysis
        failed_matches = results['failed_matches']
        if failed_matches and len(failed_matches) <= 10:  # Only show if few failures
            print(f"\n=== FAILED MATCHES (for improvement) ===")
            for i, match in enumerate(failed_matches[:5], 1):  # Show first 5
                price_entry = match['price_entry']
                result = match['matching_result']
                print(f"{i}. {price_entry.model_code}: {price_entry.malli} {price_entry.paketti or ''}")
                print(f"   Best confidence: {result.overall_confidence:.3f}")
                print(f"   Method attempted: {result.final_matching_method}")
        
        # Save enhanced results
        save_path = Path("results/bert_enhanced_pipeline_results.json")
        save_path.parent.mkdir(exist_ok=True)
        
        # Convert results to JSON-serializable format
        json_results = {
            'bert_enhanced_pipeline': True,
            'processing_statistics': stats,
            'successful_matches_count': len(successful_matches),
            'failed_matches_count': len(failed_matches),
            'match_success_rate': stats.get('match_success_rate', 0),
            'matching_methods_distribution': matching_methods if 'matching_methods' in locals() else {},
            'processing_time_seconds': processing_time,
            'improvement_vs_original': improvement,
            'extraction_timestamp': datetime.now().isoformat()
        }
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\nBERT-enhanced results saved to: {save_path}")
        
        print(f"\n=== BERT INTEGRATION SUCCESS ===")
        if stats.get('match_success_rate', 0) > 0.5:  # If >50% success
            print(f"[SUCCESS] BERT semantic matching significantly improved pipeline performance!")
            print(f"[SUCCESS] Match success rate: {stats.get('match_success_rate', 0):.1%}")
            print(f"[SUCCESS] Semantic understanding working correctly")
        elif stats.get('match_success_rate', 0) > 0.1:  # If >10% success
            print(f"[PARTIAL SUCCESS] BERT matching working, but still room for improvement")
            print(f"[ANALYSIS NEEDED] Success rate: {stats.get('match_success_rate', 0):.1%}")
        else:
            print(f"[NEEDS INVESTIGATION] BERT integration may need tuning")
            print(f"[DEBUG REQUIRED] Success rate: {stats.get('match_success_rate', 0):.1%}")
        
        return results
        
    except Exception as e:
        print(f"BERT-enhanced pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(main())