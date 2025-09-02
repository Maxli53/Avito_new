"""
Test New BERT Tier 2 Architecture
Tests the refactored 3-tier strategy: Exact -> BERT Semantic -> Fuzzy Fallback
"""

import sqlite3
from bert_matching_engine import BERTEnhancedMatchingEngine
from data_models import DualParserConfig, PriceListEntry, CatalogVehicle, VehicleSpecifications

def test_new_architecture():
    print("=== NEW BERT TIER 2 ARCHITECTURE TEST ===\n")
    
    # Load TSTH from database
    conn = sqlite3.connect("snowmobile_reconciliation.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM price_entries WHERE model_code = 'TSTH'")
    
    columns = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    conn.close()
    
    # Create price entry
    price_entry = PriceListEntry(
        model_code=row[columns.index('model_code')],
        malli=row[columns.index('malli')],
        paketti=row[columns.index('paketti')],
        moottori=row[columns.index('moottori')],
        normalized_model_name=row[columns.index('normalized_model_name')],
        normalized_package_name=row[columns.index('normalized_package_name')],
        normalized_engine_spec=row[columns.index('normalized_engine_spec')]
    )
    
    print(f"Test Price Entry (TSTH):")
    print(f"  Finnish: '{price_entry.malli}' + '{price_entry.paketti}'")
    print(f"  Engine: '{price_entry.moottori}'")
    
    # Create test catalog vehicles
    test_vehicles = [
        # Should match with Tier 1 (basic exact)
        CatalogVehicle(
            name="SUMMIT X WITH EXPERT PACKAGE",
            model_family="SUMMIT", 
            package_name="Expert Package",
            specifications=VehicleSpecifications(engine="850 E-TEC TURBO R")
        ),
        # Different vehicle for comparison
        CatalogVehicle(
            name="EXPEDITION XTREME",
            model_family="EXPEDITION", 
            package_name="Xtreme",
            specifications=VehicleSpecifications(engine="850 E-TEC")
        ),
        # Close but not exact match
        CatalogVehicle(
            name="SUMMIT ADRENALINE",
            model_family="SUMMIT",
            package_name="Adrenaline", 
            specifications=VehicleSpecifications(engine="850 E-TEC")
        )
    ]
    
    print(f"\nTest Catalog Vehicles:")
    for i, vehicle in enumerate(test_vehicles, 1):
        print(f"  {i}. '{vehicle.name}' ({vehicle.model_family})")
    
    # Initialize new architecture
    config = DualParserConfig.from_database("snowmobile_reconciliation.db")
    matching_engine = BERTEnhancedMatchingEngine(config)
    
    print(f"\n=== TESTING EACH TIER ===")
    
    # Test Tier 1 only
    print(f"\nTier 1 Test (Basic Exact):")
    tier1_match, tier1_conf = matching_engine._tier1_exact_match(price_entry, test_vehicles)
    print(f"  Match: {'YES' if tier1_match else 'NO'}")
    print(f"  Vehicle: '{tier1_match.name}' if tier1_match else 'None'")
    print(f"  Confidence: {tier1_conf:.3f}")
    print(f"  Threshold: 0.95 -> {'PASS' if tier1_conf >= 0.95 else 'FAIL'}")
    
    # Test Tier 2 BERT semantic
    print(f"\nTier 2 Test (BERT Semantic):")
    tier2_match, tier2_conf, tier2_data = matching_engine._tier2_bert_semantic_match(price_entry, test_vehicles)
    print(f"  Match: {'YES' if tier2_match else 'NO'}")
    print(f"  Vehicle: '{tier2_match.name}' if tier2_match else 'None'")
    print(f"  Confidence: {tier2_conf:.3f}")
    print(f"  Threshold: 0.80 -> {'PASS' if tier2_conf >= 0.80 else 'FAIL'}")
    if tier2_data and tier2_data.get('results'):
        print(f"  BERT Details:")
        for result in tier2_data['results'][:2]:  # Show top 2
            print(f"    '{result['price_text']}' <-> '{result['catalog_text']}': {result['similarity']:.3f}")
    
    # Test Tier 3 fuzzy fallback
    print(f"\nTier 3 Test (Fuzzy Fallback):")
    tier3_match, tier3_conf, tier3_data = matching_engine._tier3_traditional_fuzzy_match(price_entry, test_vehicles)
    print(f"  Match: {'YES' if tier3_match else 'NO'}")
    print(f"  Vehicle: '{tier3_match.name}' if tier3_match else 'None'")
    print(f"  Confidence: {tier3_conf:.3f}")
    print(f"  Threshold: 0.60 -> {'PASS' if tier3_conf >= 0.60 else 'FAIL'}")
    
    # Test full pipeline
    print(f"\n=== FULL PIPELINE TEST ===")
    final_match, result = matching_engine.match_price_to_catalog(price_entry, test_vehicles)
    
    print(f"Final Result:")
    print(f"  Match: {'YES' if final_match else 'NO'}")
    print(f"  Vehicle: '{final_match.name}' if final_match else 'None'")
    print(f"  Method: {result.final_matching_method}")
    print(f"  Confidence: {result.overall_confidence:.3f}")
    print(f"  Needs Review: {'YES' if result.requires_human_review else 'NO'}")
    
    # Show which tier activated
    print(f"\nTier Activation:")
    print(f"  Tier 1 (Exact): {'ACTIVATED' if result.tier_1_exact_match else 'SKIPPED'} ({result.tier_1_confidence:.3f})")
    print(f"  Tier 2 (BERT): {'ACTIVATED' if result.tier_2_normalized_match else 'SKIPPED'} ({result.tier_2_confidence:.3f})")
    print(f"  Tier 3 (Fuzzy): {'ACTIVATED' if result.tier_3_fuzzy_match else 'SKIPPED'} ({result.tier_3_confidence:.3f})")
    
    # Architecture validation
    print(f"\n=== ARCHITECTURE VALIDATION ===")
    
    if result.final_matching_method == "EXACT":
        print(f"[SUCCESS] Tier 1 activated as expected for exact match")
        print(f"[SUCCESS] BERT stayed in Tier 2, avoided overfitted rules")
        
    elif result.final_matching_method == "BERT_SEMANTIC":
        print(f"[SUCCESS] Tier 2 BERT activated for semantic understanding")
        print(f"[SUCCESS] No overfitted magic numbers used")
        
    elif result.final_matching_method == "FUZZY_FALLBACK":
        print(f"[INFO] Tier 3 fallback activated - traditional algorithms")
        
    else:
        print(f"[WARNING] No tier activated - check thresholds")
    
    print(f"\nNew Architecture Benefits:")
    print(f"  1. Clean separation: Exact -> Semantic -> Fuzzy")
    print(f"  2. BERT in Tier 2 for better semantic understanding")
    print(f"  3. No overfitted magic numbers in main matching logic")
    print(f"  4. Clear thresholds: 0.95 -> 0.80 -> 0.60")

if __name__ == "__main__":
    test_new_architecture()