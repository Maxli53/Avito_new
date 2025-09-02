import asyncio
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from catalog_spec_parser import SkiDooCatalogParser

async def main():
    print("=== ENHANCED SKI-DOO 2026 CATALOG EXTRACTION TEST ===\n")
    
    # Initialize enhanced parser with database connection
    parser = SkiDooCatalogParser(db_path="snowmobile_reconciliation.db")
    
    # Show available PDFs
    parser.list_available_pdfs()
    
    # Use dynamic PDF discovery - no hardcoded paths needed
    print("Starting enhanced catalog extraction with intelligent matching...\n")
    start_time = datetime.now()
    
    try:
        # Extract all catalog data using enhanced parser - no PDF path needed
        catalog_data = parser.extract_all_catalog_data(brand="SKI-DOO", year=2026)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        print(f"\n=== EXTRACTION RESULTS ===")
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Total vehicles extracted: {len(catalog_data['vehicles'])}")
        print(f"Total engines documented: {len(catalog_data['engines'])}")
        print(f"Total colors documented: {len(catalog_data['colors'].get('all_colors', []))}")
        
        # Display enhanced matching results
        display_enhanced_results(catalog_data)
        
        # Save to JSON for detailed analysis
        save_path = Path("results/ski_doo_2026_enhanced_catalog_data.json")
        save_path.parent.mkdir(exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(catalog_data, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\nEnhanced catalog data saved to: {save_path}")
        
        # Store in enhanced database schema
        await store_enhanced_catalog_data(catalog_data, parser.db_path)
        
        # Generate matching report
        generate_matching_report(catalog_data)
        
    except Exception as e:
        print(f"Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return

def display_enhanced_results(catalog_data: dict):
    """Display enhanced extraction results with matching information"""
    
    print(f"\n=== ENHANCED MATCHING RESULTS ===")
    
    # Analyze matching methods used
    matching_stats = {}
    image_stats = {}
    total_images = 0
    
    for vehicle in catalog_data['vehicles']:
        method = vehicle.get('matching_method', 'UNKNOWN')
        matching_stats[method] = matching_stats.get(method, 0) + 1
        
        # Image statistics
        images = vehicle.get('product_images', [])
        total_images += len(images)
        for img in images:
            img_type = img.get('image_type', 'UNKNOWN')
            image_stats[img_type] = image_stats.get(img_type, 0) + 1
    
    print("Matching Methods Used:")
    for method, count in matching_stats.items():
        print(f"  {method}: {count} vehicles")
    
    if total_images > 0:
        print(f"\nProduct Images Extracted: {total_images} total")
        for img_type, count in image_stats.items():
            print(f"  {img_type}: {count} images")
    
    print(f"\n=== DETAILED VEHICLE INFORMATION ===")
    
    for i, vehicle in enumerate(catalog_data['vehicles']):
        print(f"\n--- Vehicle {i+1}: {vehicle.get('name', 'Unknown')} ---")
        print(f"Page: {vehicle.get('page_number', 'N/A')}")
        print(f"Model Family: {vehicle.get('model_family', 'N/A')}")
        
        # Matching information
        method = vehicle.get('matching_method', 'N/A')
        confidence = vehicle.get('matching_confidence', 'N/A')
        print(f"Matching Method: {method}")
        if confidence != 'N/A':
            print(f"Matching Confidence: {confidence:.3f}")
        
        confidence_desc = vehicle.get('confidence_description')
        if confidence_desc:
            print(f"Confidence Description: {confidence_desc}")
        
        model_code = vehicle.get('price_list_model_code')
        if model_code:
            print(f"Price List Model Code: {model_code}")
        
        # Product images
        images = vehicle.get('product_images', [])
        if images:
            print(f"Product Images: {len(images)} extracted")
            for img in images[:2]:  # Show first 2
                print(f"  - {img['image_type']}: {img['image_filename']} ({img['width']}x{img['height']})")
                if img.get('dominant_colors'):
                    colors = [c['name'] for c in img['dominant_colors'][:2]]
                    print(f"    Colors: {', '.join(colors)}")
        
        # Marketing data
        marketing = vehicle.get('marketing', {})
        if marketing.get('tagline'):
            print(f"Marketing Tagline: \"{marketing['tagline'][:80]}...\"")
        
        key_benefits = marketing.get('key_benefits', [])
        if key_benefits:
            print(f"Key Benefits: {len(key_benefits)} items")
            for benefit in key_benefits[:3]:  # Show first 3
                print(f"  - {benefit[:60]}...")
        
        # Technical specifications
        specs = vehicle.get('specifications', {})
        if specs.get('engine'):
            engine = specs['engine']
            if engine.get('engine_family'):
                print(f"Engine: {engine['engine_family']}")

async def store_enhanced_catalog_data(catalog_data: dict, db_path: str):
    """Store enhanced catalog data in the new database schema"""
    
    print(f"\n=== STORING ENHANCED CATALOG DATA ===")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        stored_vehicles = 0
        stored_images = 0
        
        for vehicle_data in catalog_data['vehicles']:
            vehicle_id = vehicle_data['id']
            
            # Store in catalog_entries table
            cursor.execute("""
                INSERT OR REPLACE INTO catalog_entries (
                    id, vehicle_name, model_family, page_number,
                    specifications, features, marketing, dimensions,
                    performance, options, powertrain, suspension,
                    tracks, colors, matching_method, matching_confidence,
                    confidence_description, matching_notes, extraction_timestamp,
                    source_catalog_name, source_catalog_page, price_list_model_code,
                    extraction_method, parser_version, has_image_data,
                    images_processed, main_product_image
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vehicle_id,
                vehicle_data.get('name'),
                vehicle_data.get('model_family'),
                vehicle_data.get('page_number'),
                json.dumps(vehicle_data.get('specifications', {})),
                json.dumps(vehicle_data.get('features', {})),
                json.dumps(vehicle_data.get('marketing', {})),
                json.dumps(vehicle_data.get('dimensions', {})),
                json.dumps(vehicle_data.get('performance', {})),
                json.dumps(vehicle_data.get('options', {})),
                json.dumps(vehicle_data.get('powertrain', {})),
                json.dumps(vehicle_data.get('suspension', {})),
                json.dumps(vehicle_data.get('tracks', {})),
                json.dumps(vehicle_data.get('colors', [])),
                vehicle_data.get('matching_method'),
                vehicle_data.get('matching_confidence'),
                vehicle_data.get('confidence_description'),
                vehicle_data.get('matching_notes'),
                vehicle_data.get('extraction_timestamp'),
                vehicle_data.get('source_catalog_name'),
                vehicle_data.get('source_catalog_page'),
                vehicle_data.get('price_list_model_code'),
                vehicle_data.get('extraction_method'),
                vehicle_data.get('parser_version'),
                len(vehicle_data.get('product_images', [])) > 0,
                len(vehicle_data.get('product_images', [])),
                vehicle_data.get('product_images', [{}])[0].get('image_path') if vehicle_data.get('product_images') else None
            ))
            
            stored_vehicles += 1
            
            # Store product images
            for image_data in vehicle_data.get('product_images', []):
                cursor.execute("""
                    INSERT OR REPLACE INTO product_images (
                        id, vehicle_id, vehicle_name, image_filename, image_path,
                        page_number, image_index, width, height, image_type,
                        dominant_colors, features_visible, quality_score,
                        extraction_timestamp, source_catalog, extraction_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"{vehicle_id}_{image_data.get('image_index', 0)}",
                    vehicle_id,
                    image_data.get('vehicle_name'),
                    image_data.get('image_filename'),
                    image_data.get('image_path'),
                    image_data.get('page_number'),
                    image_data.get('image_index'),
                    image_data.get('width'),
                    image_data.get('height'),
                    image_data.get('image_type'),
                    json.dumps(image_data.get('dominant_colors', [])),
                    json.dumps(image_data.get('features_visible', [])),
                    image_data.get('quality_score'),
                    image_data.get('extraction_timestamp'),
                    image_data.get('source_catalog'),
                    image_data.get('extraction_method')
                ))
                
                stored_images += 1
        
        conn.commit()
        print(f"Successfully stored: {stored_vehicles} vehicles")
        print(f"Successfully stored: {stored_images} product images")
        
    except Exception as e:
        print(f"Error storing catalog data: {e}")
        conn.rollback()
    finally:
        conn.close()

def generate_matching_report(catalog_data: dict):
    """Generate detailed matching report"""
    
    print(f"\n=== MATCHING QUALITY REPORT ===")
    
    vehicles = catalog_data.get('vehicles', [])
    if not vehicles:
        print("No vehicles to analyze")
        return
    
    # Analyze matching quality
    exact_matches = [v for v in vehicles if v.get('matching_method') == 'EXACT']
    normalized_matches = [v for v in vehicles if v.get('matching_method') == 'NORMALIZED']  
    fuzzy_matches = [v for v in vehicles if v.get('matching_method') == 'FUZZY']
    
    print(f"Total vehicles extracted: {len(vehicles)}")
    print(f"Exact matches: {len(exact_matches)} ({len(exact_matches)/len(vehicles)*100:.1f}%)")
    print(f"Normalized matches: {len(normalized_matches)} ({len(normalized_matches)/len(vehicles)*100:.1f}%)")
    print(f"Fuzzy matches: {len(fuzzy_matches)} ({len(fuzzy_matches)/len(vehicles)*100:.1f}%)")
    
    if fuzzy_matches:
        print("\nFuzzy match details:")
        for vehicle in fuzzy_matches:
            name = vehicle.get('name', 'Unknown')
            confidence = vehicle.get('matching_confidence', 0)
            desc = vehicle.get('confidence_description', 'N/A')
            print(f"  - {name}: {desc}")
    
    # Image extraction statistics
    total_images = sum(len(v.get('product_images', [])) for v in vehicles)
    vehicles_with_images = len([v for v in vehicles if v.get('product_images')])
    
    print(f"\nImage extraction statistics:")
    print(f"Vehicles with images: {vehicles_with_images}/{len(vehicles)} ({vehicles_with_images/len(vehicles)*100:.1f}%)")
    print(f"Total images extracted: {total_images}")
    if vehicles_with_images > 0:
        print(f"Average images per vehicle: {total_images/vehicles_with_images:.1f}")

if __name__ == "__main__":
    asyncio.run(main())