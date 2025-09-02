"""
Phase 3 Debug: Transparent Matching Algorithm Analysis
Shows why 0% match success rate with step-by-step matching logic
"""

from modular_parser import ModularDualParser, CatalogExtractor
from matching_engine import MatchingEngine, TextNormalizer
from data_models import DualParserConfig, PriceListEntry, CatalogVehicle, VehicleSpecifications
import sqlite3

def debug_matching_algorithm():
    print("=== PHASE 3: MATCHING ALGORITHM DEBUG ===\n")
    
    # Load some real price entries
    print("1. LOADING PRICE ENTRIES FROM DATABASE:")
    conn = sqlite3.connect("snowmobile_reconciliation.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT model_code, malli, paketti, moottori, normalized_model_name, normalized_package_name 
        FROM price_entries 
        WHERE malli IN ('Summit', 'Expedition', 'Renegade', 'MXZ', 'Backcountry')
        ORDER BY malli 
        LIMIT 5
    """)
    
    price_data = cursor.fetchall()
    conn.close()
    
    price_entries = []
    for row in price_data:
        entry = PriceListEntry(
            model_code=row[0],
            malli=row[1], 
            paketti=row[2],
            moottori=row[3],
            normalized_model_name=row[4],
            normalized_package_name=row[5]
        )
        price_entries.append(entry)
        print(f"   {entry.model_code}: {entry.malli} {entry.paketti or ''} ({entry.moottori})")
    
    print(f"\nLoaded {len(price_entries)} price entries")
    
    print("\n2. CREATING TEST CATALOG VEHICLES:")
    # Create some test catalog vehicles that SHOULD match
    test_vehicles = [
        CatalogVehicle(
            name="SUMMIT X WITH EXPERT PACKAGE",
            model_family="SUMMIT", 
            package_name="Expert Package",
            specifications=VehicleSpecifications(engine="850 E-TEC TURBO R")
        ),
        CatalogVehicle(
            name="SUMMIT X",
            model_family="SUMMIT",
            specifications=VehicleSpecifications(engine="850 E-TEC")
        ),
        CatalogVehicle(
            name="EXPEDITION XTREME", 
            model_family="EXPEDITION",
            package_name="Xtreme",
            specifications=VehicleSpecifications(engine="850 E-TEC")
        ),
        CatalogVehicle(
            name="RENEGADE X-RS",
            model_family="RENEGADE", 
            package_name="X-RS",
            specifications=VehicleSpecifications(engine="850 E-TEC")
        ),
        CatalogVehicle(
            name="MXZ X-RS",
            model_family="MXZ",
            package_name="X-RS", 
            specifications=VehicleSpecifications(engine="600R E-TEC")
        )
    ]
    
    for vehicle in test_vehicles:
        print(f"   {vehicle.name} ({vehicle.model_family}) - {vehicle.specifications.engine}")
    
    print(f"\nCreated {len(test_vehicles)} test catalog vehicles")
    
    print("\n" + "="*80)
    
    # Initialize matching engine
    config = DualParserConfig.from_database("snowmobile_reconciliation.db") 
    matching_engine = MatchingEngine(config)
    
    print(f"\n3. MATCHING ENGINE CONFIGURATION:")
    print(f"   Exact match threshold: {config.exact_match_threshold}")
    print(f"   Normalized match threshold: {config.normalized_match_threshold}")
    print(f"   Fuzzy match threshold: {config.fuzzy_match_threshold}")
    
    print(f"\n4. STEP-BY-STEP MATCHING ANALYSIS:")
    
    # Test each price entry against catalog vehicles
    for i, price_entry in enumerate(price_entries, 1):
        print(f"\n--- MATCH ATTEMPT {i} ---")
        print(f"Price Entry: {price_entry.model_code} - '{price_entry.malli}' + '{price_entry.paketti or 'None'}'")
        print(f"Normalized: '{price_entry.normalized_model_name}' + '{price_entry.normalized_package_name or 'None'}'")
        
        # Try matching against each catalog vehicle
        best_match = None
        best_result = None
        best_confidence = 0.0
        
        for j, catalog_vehicle in enumerate(test_vehicles, 1):
            print(f"\n  Testing against catalog vehicle {j}: '{catalog_vehicle.name}'")
            
            # Use matching engine
            match, result = matching_engine.match_price_to_catalog(price_entry, [catalog_vehicle])
            
            print(f"    Tier 1 (Exact): {result.tier_1_exact_match} (confidence: {result.tier_1_confidence:.3f})")
            print(f"    Tier 2 (Normalized): {result.tier_2_normalized_match} (confidence: {result.tier_2_confidence:.3f})")
            print(f"    Tier 3 (Fuzzy): {result.tier_3_fuzzy_match} (confidence: {result.tier_3_confidence:.3f})")
            print(f"    Overall: {result.final_matching_method} (confidence: {result.overall_confidence:.3f})")
            print(f"    Match found: {match is not None}")
            
            if result.overall_confidence > best_confidence:
                best_confidence = result.overall_confidence  
                best_match = match
                best_result = result
            
            # Debug tier 1 exact matching
            if not result.tier_1_exact_match:
                print(f"    Tier 1 Debug:")
                print(f"      Price model '{price_entry.malli}' in catalog family '{catalog_vehicle.model_family}': {price_entry.malli.upper() in catalog_vehicle.model_family.upper()}")
                print(f"      Price model '{price_entry.malli}' in catalog name '{catalog_vehicle.name}': {price_entry.malli.upper() in catalog_vehicle.name.upper()}")
        
        print(f"\n  BEST MATCH FOR {price_entry.model_code}:")
        if best_match:
            print(f"    Matched to: {best_match.name}")
            print(f"    Method: {best_result.final_matching_method}")
            print(f"    Confidence: {best_result.overall_confidence:.3f}")
            print(f"    Needs review: {best_result.requires_human_review}")
        else:
            print(f"    NO MATCH FOUND (best confidence: {best_confidence:.3f})")
        
        print("-" * 60)

def debug_normalization_differences():
    print(f"\n=== NORMALIZATION COMPARISON ===")
    
    normalizer = TextNormalizer()
    
    test_pairs = [
        ("Finnish: Summit", "English: SUMMIT"),
        ("Finnish: Summit X with Expert Pkg", "English: SUMMIT X WITH EXPERT PACKAGE"),
        ("Finnish: Expedition Xtreme", "English: EXPEDITION XTREME"), 
        ("Finnish: MXZ X-RS", "English: MXZ X-RS"),
        ("Finnish: Renegade X-RS", "English: RENEGADE X-RS")
    ]
    
    for finnish_desc, english_desc in test_pairs:
        finnish = finnish_desc.split(": ")[1]
        english = english_desc.split(": ")[1]
        
        norm_finnish = normalizer.normalize_model_name(finnish)
        norm_english = normalizer.normalize_model_name(english)
        
        print(f"{finnish_desc:<35} -> '{norm_finnish}'")
        print(f"{english_desc:<35} -> '{norm_english}'")
        print(f"Match: {norm_finnish == norm_english}")
        print()

if __name__ == "__main__":
    debug_matching_algorithm()
    debug_normalization_differences()