#!/usr/bin/env python3
"""
Extract BRP models from already saved API field data
"""

import json
from pathlib import Path

def extract_models_from_saved_data():
    """Extract BRP models from saved field data"""
    
    # Check the saved field data file
    field_file = Path("avito_snegohody_fields_20250902_124141.json")
    
    if not field_file.exists():
        print("Field data file not found")
        return []
    
    with open(field_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=== EXTRACTING BRP MODELS FROM SAVED API DATA ===")
    
    raw_data = data.get('raw_data', {})
    fields = raw_data.get('fields', [])
    
    # Find the Model field
    model_field = None
    for field in fields:
        if field.get('tag') == 'Model':
            model_field = field
            print(f"Found Model field in saved data")
            break
    
    if not model_field:
        print("Model field not found")
        return []
    
    # Check field structure
    print(f"Model field keys: {list(model_field.keys())}")
    
    # Check content for catalog info
    content = model_field.get('content', [])
    if content:
        content_data = content[0] if isinstance(content, list) else content
        print(f"Content keys: {list(content_data.keys())}")
        
        if 'values_link_xml' in content_data:
            print(f"Values XML Link: {content_data['values_link_xml']}")
        
        if 'is_catalog' in content_data:
            print(f"Is Catalog: {content_data['is_catalog']}")
            
        if 'name_in_catalog' in content_data:
            print(f"Catalog Name: {content_data['name_in_catalog']}")
    
    # Since models are in external catalog, let's check all fields for any that might have model lists
    print("\n=== CHECKING ALL FIELDS FOR MODEL DATA ===")
    
    all_models = []
    brp_models = []
    
    for field in fields:
        tag = field.get('tag', '')
        
        # Check if field has values
        if 'values' in field:
            values = field['values']
            if values and isinstance(values, list):
                print(f"Field '{tag}' has {len(values)} values")
                
                # If it's model-related field, extract values
                if 'model' in tag.lower() or 'марка' in tag.lower():
                    for value in values:
                        if isinstance(value, dict):
                            model_name = value.get('name', value.get('value', str(value)))
                        else:
                            model_name = str(value)
                        
                        all_models.append(model_name)
        
        # Check content for values
        content = field.get('content', [])
        for content_item in (content if isinstance(content, list) else [content]):
            if isinstance(content_item, dict) and 'values' in content_item:
                values = content_item['values']
                if values and isinstance(values, list):
                    print(f"Field '{tag}' content has {len(values)} values")
                    
                    if 'model' in tag.lower():
                        for value in values:
                            if isinstance(value, dict):
                                model_name = value.get('name', value.get('value', str(value)))
                            else:
                                model_name = str(value)
                            
                            all_models.append(model_name)
    
    # Filter for BRP models
    brp_brands = ['ski-doo', 'lynx', 'expedition', 'mxz', 'renegade', 'summit', 'skandic', 'tundra', 'brp']
    
    for model_name in all_models:
        model_lower = model_name.lower()
        is_brp = any(brand in model_lower for brand in brp_brands)
        if is_brp:
            brp_models.append(model_name)
    
    print(f"\nFound {len(all_models)} total models")
    print(f"Found {len(brp_models)} BRP models")
    
    if not brp_models:
        print("\nNo BRP models found in saved data - they must be in external catalog")
        print("The Model field references an external XML catalog that contains the actual model list")
        print("This is normal - Avito stores large model lists externally to keep API responses small")
    
    return brp_models

if __name__ == "__main__":
    models = extract_models_from_saved_data()
    
    if models:
        print("\nBRP MODELS EXTRACTED:")
        for i, model in enumerate(models[:20], 1):
            print(f"  {i:2d}. {model}")
        if len(models) > 20:
            print(f"  ... and {len(models) - 20} more")