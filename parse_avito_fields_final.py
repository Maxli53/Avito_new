#!/usr/bin/env python3
"""
Parse Avito snowmobile fields properly from API response
"""

import json

def parse_avito_fields():
    """Parse the Avito fields from saved JSON"""
    # Read the saved JSON file
    with open('avito_snegohody_fields_20250902_124141.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    raw_data = data['raw_data']
    
    if 'fields' not in raw_data:
        print("No fields found in raw data")
        return
    
    fields = raw_data['fields']
    
    print("AVITO SNOWMOBILE FIELDS - COMPLETE ANALYSIS")
    print("=" * 60)
    print(f"Total fields: {len(fields)}")
    print()
    
    required_fields = []
    optional_fields = []
    snowmobile_specific = []
    
    for field in fields:
        tag = field.get('tag', 'Unknown')
        label = field.get('label', 'No label')
        descriptions = field.get('descriptions', '')
        
        # Check if field is required
        is_required = False
        if 'content' in field and field['content']:
            content = field['content'][0]  # Take first content entry
            is_required = content.get('required', False)
        
        field_info = {
            'tag': tag,
            'label': label,
            'required': is_required,
            'description': descriptions[:200] + '...' if len(descriptions) > 200 else descriptions
        }
        
        if is_required:
            required_fields.append(field_info)
        else:
            optional_fields.append(field_info)
        
        # Check if snowmobile-specific
        snowmobile_terms = [
            'мощность', 'двигател', 'объем', 'модель', 'марка', 'год', 'цена',
            'power', 'engine', 'model', 'make', 'year', 'price', 'снегоход'
        ]
        
        field_text = f"{tag} {label} {descriptions}".lower()
        if any(term in field_text for term in snowmobile_terms):
            snowmobile_specific.append(field_info)
    
    # Display results
    print(f"REQUIRED FIELDS ({len(required_fields)}):")
    print("-" * 50)
    for field in required_fields:
        print(f"* {field['tag']} - {field['label']}")
        if field['description']:
            print(f"  Description: {field['description']}")
        print()
    
    if not required_fields:
        print("  No strictly required fields found")
        print()
    
    print(f"IMPORTANT/SNOWMOBILE-SPECIFIC FIELDS ({len(snowmobile_specific)}):")
    print("-" * 50)
    for field in snowmobile_specific:
        status = "REQUIRED" if field['required'] else "OPTIONAL"
        print(f"{'*' if field['required'] else '+'} {field['tag']} - {field['label']} ({status})")
        if field['description']:
            print(f"  {field['description']}")
        print()
    
    print("ALL FIELDS SUMMARY:")
    print("-" * 50)
    field_mapping = {}
    
    for field in fields:
        tag = field.get('tag', 'Unknown')
        label = field.get('label', 'No label')
        
        is_required = False
        field_type = 'Unknown'
        
        if 'content' in field and field['content']:
            content = field['content'][0]
            is_required = content.get('required', False)
            field_type = content.get('field_type', 'Unknown')
        
        field_mapping[tag] = {
            'label': label,
            'required': is_required,
            'type': field_type
        }
    
    # Show key fields for XML
    xml_important_fields = [
        'Id', 'Title', 'Category', 'GoodsType', 'AdType', 'Description',
        'Price', 'Images', 'ContactPhone', 'Model', 'Make', 'Year',
        'Power', 'EngineCapacity', 'PersonCapacity', 'TrackWidth',
        'EngineType', 'Condition', 'Address'
    ]
    
    print("KEY FIELDS FOR XML GENERATION:")
    print("-" * 50)
    
    found_important = 0
    for xml_field in xml_important_fields:
        if xml_field in field_mapping:
            field_info = field_mapping[xml_field]
            status = "REQUIRED" if field_info['required'] else "OPTIONAL"
            print(f"  {xml_field}: {field_info['label']} ({status})")
            found_important += 1
        else:
            print(f"  {xml_field}: NOT FOUND in API")
    
    print(f"\nFound {found_important}/{len(xml_important_fields)} important XML fields")
    
    # Final mapping for XML
    print(f"\nRECOMMENDED XML FIELD MAPPING:")
    print("=" * 50)
    
    xml_mapping = {
        'Id': 'Unique identifier (usually article code)',
        'Title': 'Ad title/name',
        'Model': 'Snowmobile model',
        'Make': 'Brand/manufacturer (BRP)',  
        'Year': 'Model year',
        'Price': 'Price in rubles',
        'Power': 'Engine power in HP',
        'EngineCapacity': 'Engine displacement in CC',
        'PersonCapacity': 'Number of passengers',
        'TrackWidth': 'Track width in mm',
        'Description': 'Full product description',
        'Images': 'Product images',
        'Address': 'Location (Санкт-Петербург)',
        'Category': 'Мотоциклы и мототехника',
        'VehicleType': 'Снегоходы',
        'EngineType': 'Бензин',
        'Condition': 'Новое',
        'Kilometrage': '0'
    }
    
    for xml_field, description in xml_mapping.items():
        found_in_api = "YES" if xml_field in field_mapping else "NO"
        print(f"  {xml_field:<15}: {description} (In API: {found_in_api})")

if __name__ == "__main__":
    parse_avito_fields()