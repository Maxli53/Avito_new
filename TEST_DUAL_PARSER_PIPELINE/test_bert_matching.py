"""
Test BERT-Enhanced Matching Engine with TSTH Example
"""

import sqlite3
from bert_matching_engine import BERTEnhancedMatchingEngine, BERTSemanticMatcher
from data_models import DualParserConfig, PriceListEntry, CatalogVehicle, VehicleSpecifications

def test_bert_semantic_matching():
    print("=== BERT SEMANTIC MATCHING TEST ===\n")
    
    # Test the BERT semantic matcher directly
    bert_matcher = BERTSemanticMatcher()
    
    print("1. DIRECT BERT SIMILARITY TESTS:")
    print("-" * 50)
    
    test_pairs = [
        ("Summit X with Expert Pkg", "SUMMIT X WITH EXPERT PACKAGE"),
        ("Summit X with Expert Pkg", "SUMMIT Expert Package"), 
        ("Expedition Xtreme", "EXPEDITION XTREME"),
        ("Renegade X-RS", "RENEGADE XRS"),
        ("MXZ Neo+", "MXZ NEO PLUS"),
        ("Backcountry Sport", "BACKCOUNTRY SPORT"),
        # Should NOT match well
        ("Summit X", "EXPEDITION XTREME"),
        ("Renegade", "MXZ SPORT")
    ]
    
    for finnish, english in test_pairs:
        similarity = bert_matcher.semantic_similarity(finnish, english)
        match_status = "[MATCH]" if similarity >= 0.7 else "[NO MATCH]"
        print(f"'{finnish}' <-> '{english}'")
        print(f"  Similarity: {similarity:.3f} {match_status}")
        print()

def test_bert_full_pipeline():
    print("2. FULL BERT PIPELINE TEST WITH TSTH:")
    print("-" * 50)
    
    # Load TSTH from database
    conn = sqlite3.connect("snowmobile_reconciliation.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM price_entries WHERE model_code = 'TSTH'")
    
    columns = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("TSTH not found in database!")
        return
    
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
    
    print(f"TSTH Price Entry:")
    print(f"  Model: '{price_entry.malli}' + Package: '{price_entry.paketti}'")
    print(f"  Engine: '{price_entry.moottori}'")
    print(f"  Normalized: '{price_entry.normalized_model_name}' + '{price_entry.normalized_package_name}'")
    
    # Create test catalog vehicles
    test_vehicles = [
        # Perfect match
        CatalogVehicle(
            name="SUMMIT X WITH EXPERT PACKAGE",
            model_family="SUMMIT", 
            package_name="Expert Package",
            specifications=VehicleSpecifications(engine="850 E-TEC TURBO R")
        ),
        # Close match
        CatalogVehicle(
            name="SUMMIT X",
            model_family="SUMMIT",
            specifications=VehicleSpecifications(engine="850 E-TEC")
        ),
        # Different family (should not match well)
        CatalogVehicle(
            name="EXPEDITION XTREME",
            model_family="EXPEDITION", 
            package_name="Xtreme",
            specifications=VehicleSpecifications(engine="850 E-TEC")
        )
    ]
    
    print(f"\nTest Catalog Vehicles:")
    for i, vehicle in enumerate(test_vehicles, 1):
        print(f"  {i}. '{vehicle.name}' ({vehicle.model_family})")
    
    # Initialize BERT matching engine
    config = DualParserConfig.from_database("snowmobile_reconciliation.db")
    matching_engine = BERTEnhancedMatchingEngine(config)
    
    print(f"\nMatching Configuration:")
    print(f"  Exact threshold: {config.exact_match_threshold}")
    print(f"  Normalized threshold: {config.normalized_match_threshold}")
    print(f"  Fuzzy (BERT) threshold: {config.fuzzy_match_threshold}")
    
    print(f"\n3. BERT MATCHING ENGINE RESULTS:")
    print("-" * 50)
    
    # Test against each vehicle individually
    for i, vehicle in enumerate(test_vehicles, 1):
        print(f"\nTesting against Vehicle {i}: '{vehicle.name}'")
        
        match, result = matching_engine.match_price_to_catalog(price_entry, [vehicle])
        
        print(f"  Tier 1 (Exact): {result.tier_1_exact_match} (confidence: {result.tier_1_confidence:.3f})")
        print(f"  Tier 2 (Normalized): {result.tier_2_normalized_match} (confidence: {result.tier_2_confidence:.3f})")
        print(f"  Tier 3 (BERT): {result.tier_3_fuzzy_match} (confidence: {result.tier_3_confidence:.3f})")
        print(f"  Final Method: '{result.final_matching_method}'")
        print(f"  Overall Confidence: {result.overall_confidence:.3f}")
        print(f"  Match Found: {'[YES]' if match else '[NO]'}")
        print(f"  Needs Review: {'[YES]' if result.requires_human_review else '[NO]'}")
        
        # Show BERT algorithm details if available
        if result.tier_3_algorithms and result.tier_3_algorithms.get('results'):
            bert_result = result.tier_3_algorithms['results'][0]
            print(f"  BERT Details:")
            print(f"    Price text: '{bert_result['price_text']}'")
            print(f"    Catalog text: '{bert_result['catalog_text']}'")
            print(f"    Similarity: {bert_result['similarity']:.3f}")
            print(f"    Same family: {bert_result['same_family']}")

def test_bert_best_match():
    print(f"\n4. BEST MATCH TEST (All vehicles together):")
    print("-" * 50)
    
    # Load TSTH
    conn = sqlite3.connect("snowmobile_reconciliation.db")
    cursor = conn.cursor()
    cursor.execute("SELECT model_code, malli, paketti, moottori, normalized_model_name, normalized_package_name FROM price_entries WHERE model_code = 'TSTH'")
    row = cursor.fetchone()
    conn.close()
    
    price_entry = PriceListEntry(
        model_code=row[0], malli=row[1], paketti=row[2], moottori=row[3],
        normalized_model_name=row[4], normalized_package_name=row[5]
    )
    
    # Multiple catalog options
    catalog_vehicles = [
        CatalogVehicle(name="SUMMIT X WITH EXPERT PACKAGE", model_family="SUMMIT", package_name="Expert Package"),
        CatalogVehicle(name="SUMMIT X", model_family="SUMMIT", package_name="X"),
        CatalogVehicle(name="SUMMIT ADRENALINE", model_family="SUMMIT", package_name="Adrenaline"),
        CatalogVehicle(name="EXPEDITION XTREME", model_family="EXPEDITION", package_name="Xtreme"),
        CatalogVehicle(name="RENEGADE X-RS", model_family="RENEGADE", package_name="X-RS")
    ]
    
    config = DualParserConfig.from_database("snowmobile_reconciliation.db")
    matching_engine = BERTEnhancedMatchingEngine(config)
    
    print(f"Testing TSTH against {len(catalog_vehicles)} catalog vehicles:")
    
    best_match, result = matching_engine.match_price_to_catalog(price_entry, catalog_vehicles)
    
    print(f"\nBEST MATCH RESULT:")
    if best_match:
        print(f"  [MATCHED] to: '{best_match.name}'")
        print(f"  Method: {result.final_matching_method}")
        print(f"  Confidence: {result.overall_confidence:.3f}")
        print(f"  Quality: {'AUTO-ACCEPT' if not result.requires_human_review else 'NEEDS REVIEW'}")
        
        print(f"\n  Match Summary:")
        print(f"    TSTH: '{price_entry.malli} {price_entry.paketti}' ({price_entry.moottori})")
        print(f"    |")
        print(f"    Catalog: '{best_match.name}' ({best_match.model_family})")
        print(f"    Method: {result.final_matching_method}")
    else:
        print(f"  [NO MATCH FOUND]")
        print(f"  Best confidence: {result.overall_confidence:.3f}")

if __name__ == "__main__":
    print("Starting BERT matching tests...\n")
    test_bert_semantic_matching()
    test_bert_full_pipeline()
    test_bert_best_match()
    print(f"\n=== BERT MATCHING TESTS COMPLETE ===")