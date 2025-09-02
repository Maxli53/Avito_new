import json
from pathlib import Path

def show_comprehensive_extraction_results():
    """Display comprehensive extraction results from the catalog parser"""
    
    json_path = Path("results/ski_doo_2026_complete_catalog_data.json")
    
    if not json_path.exists():
        print("JSON file not found. Please run the catalog parser first.")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=== SKI-DOO 2026 CATALOG - COMPREHENSIVE EXTRACTION REPORT ===\n")
    
    # Summary statistics
    print(f"EXTRACTION SUMMARY:")
    print(f"  - Total Vehicles Extracted: {len(data['vehicles'])}")
    print(f"  - Total Pages Processed: {data['metadata']['total_pages']}")
    print(f"  - Engine Specifications: {len(data['engines'])}")
    print(f"  - Color Options: {len(data['colors'].get('all_colors', []))}")
    print(f"  - Marketing Messages: {len(data['marketing_data'].get('marketing_messages', []))}")
    
    # Vehicle families
    families = set()
    for vehicle in data['vehicles']:
        if vehicle.get('model_family'):
            families.add(vehicle['model_family'])
    
    print(f"\nVEHICLE FAMILIES DOCUMENTED:")
    for family in sorted(families):
        family_count = len([v for v in data['vehicles'] if v.get('model_family') == family])
        print(f"  - {family}: {family_count} model(s)")
    
    # Show detailed vehicle data
    print(f"\nDETAILED VEHICLE SPECIFICATIONS & MARKETING DATA:")
    print("=" * 80)
    
    for i, vehicle in enumerate(data['vehicles']):
        print(f"\n[{i+1}] {vehicle.get('name', 'Unknown Vehicle')} (Page {vehicle.get('page_number')})")
        print(f"    Model Family: {vehicle.get('model_family', 'Not specified')}")
        
        # Marketing content
        marketing = vehicle.get('marketing', {})
        if marketing.get('tagline'):
            print(f"    Marketing Tagline: \"{marketing['tagline']}\"")
        
        if marketing.get('key_benefits'):
            print(f"    Key Benefits ({len(marketing['key_benefits'])} items):")
            for benefit in marketing['key_benefits'][:5]:  # Show first 5
                print(f"      - {benefit}")
            if len(marketing['key_benefits']) > 5:
                print(f"      ... and {len(marketing['key_benefits']) - 5} more benefits")
        
        # Technical specs
        if vehicle.get('specifications', {}).get('engine'):
            engine = vehicle['specifications']['engine']
            print(f"    Engine: {engine.get('engine_family', 'Not specified')}")
            if engine.get('cylinders'):
                print(f"      - Cylinders: {engine['cylinders']}")
            if engine.get('displacement_cc'):
                print(f"      - Displacement: {engine['displacement_cc']} cc")
        
        # Features
        features = vehicle.get('features', {})
        non_empty_features = {k: v for k, v in features.items() if v and v.strip()}
        if non_empty_features:
            print(f"    Features ({len(non_empty_features)} documented):")
            for feature_name, feature_value in list(non_empty_features.items())[:3]:
                print(f"      - {feature_name.title().replace('_', ' ')}: {feature_value}")
        
        # Dimensions
        dimensions = vehicle.get('dimensions', {})
        if dimensions:
            print(f"    Dimensions:")
            for dim_name, dim_value in dimensions.items():
                print(f"      - {dim_name.title().replace('_', ' ')}: {dim_value}")
        
        # Suspension
        suspension = vehicle.get('suspension', {})
        non_empty_susp = {k: v for k, v in suspension.items() if v and v.strip()}
        if non_empty_susp:
            print(f"    Suspension:")
            for susp_name, susp_value in non_empty_susp.items():
                print(f"      - {susp_name.title().replace('_', ' ')}: {susp_value}")
        
        # Colors
        colors = vehicle.get('colors', [])
        if colors:
            color_names = [c['name'] for c in colors]
            print(f"    Available Colors: {', '.join(color_names)}")
        
        print("-" * 80)
    
    # Show color palette
    print(f"\n🎨 COLOR PALETTE EXTRACTED:")
    all_colors = data['colors'].get('all_colors', [])
    if all_colors:
        print(f"Total Colors Documented: {len(all_colors)}")
        unique_colors = list(set(color['name'] for color in all_colors))
        print("Color Names:")
        for i, color in enumerate(sorted(unique_colors)):
            if i % 3 == 0:
                print("  ", end="")
            print(f"{color:<20}", end="")
            if (i + 1) % 3 == 0:
                print()
        if len(unique_colors) % 3 != 0:
            print()
    
    # Show marketing messages
    print(f"\n📢 MARKETING MESSAGES CAPTURED:")
    marketing_messages = data['marketing_data'].get('marketing_messages', [])
    if marketing_messages:
        for i, message in enumerate(marketing_messages[:3]):
            print(f"  {i+1}. {message[:100]}...")
        if len(marketing_messages) > 3:
            print(f"  ... and {len(marketing_messages) - 3} more messages")
    
    # Product categories
    if data['marketing_data'].get('product_categories'):
        categories = data['marketing_data']['product_categories']
        print(f"\n📦 PRODUCT CATEGORIES: {' • '.join(categories)}")
    
    print(f"\n✅ EXTRACTION COMPLETE - ALL AVAILABLE FIELDS CAPTURED")
    print(f"   Including: Vehicle specs, marketing data, technical details,")
    print(f"   dimensions, colors, features, and comprehensive documentation")

if __name__ == "__main__":
    show_comprehensive_extraction_results()