#!/usr/bin/env python3
"""
Extract snowmobile fields data without emoji encoding issues
"""

import requests
import json
import base64
from pathlib import Path
from datetime import datetime

def load_credentials():
    """Load Avito API credentials"""
    env_path = Path("Avito_I/INTEGRATION_PACKAGE/credentials/.env")
    credentials = {}
    
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    credentials[key] = value
    
    return {
        'client_id': credentials.get('AVITO_CLIENT_ID'),
        'client_secret': credentials.get('AVITO_CLIENT_SECRET')
    }

def authenticate():
    """Get OAuth2 access token"""
    credentials = load_credentials()
    client_id = credentials['client_id']
    client_secret = credentials['client_secret']
    
    credentials_encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        'Authorization': f'Basic {credentials_encoded}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {'grant_type': 'client_credentials'}
    
    response = requests.post("https://api.avito.ru/token", headers=headers, data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        return token_data.get('access_token')
    return None

def get_snegohody_fields():
    """Get fields for snegohody category"""
    access_token = authenticate()
    if not access_token:
        print("Authentication failed")
        return None
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(
        "https://api.avito.ru/autoload/v1/user-docs/node/snegohody/fields",
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get fields: {response.status_code} - {response.text}")
        return None

def analyze_fields_simple(fields_data):
    """Analyze fields without emoji characters"""
    if not fields_data or 'fields' not in fields_data:
        print("No fields data found")
        return
    
    fields = fields_data['fields']
    required_fields = []
    optional_fields = []
    
    print(f"AVITO SNOWMOBILE FIELDS ANALYSIS")
    print(f"================================")
    print(f"Total fields found: {len(fields)}")
    print("")
    
    for field in fields:
        field_name = field.get('name', 'Unknown')
        field_type = field.get('type', 'Unknown')
        is_required = field.get('required', False)
        description = field.get('description', '')
        
        field_info = {
            'name': field_name,
            'type': field_type,
            'required': is_required,
            'description': description
        }
        
        if 'values' in field and field['values']:
            field_info['values'] = field['values']
        
        if is_required:
            required_fields.append(field_info)
        else:
            optional_fields.append(field_info)
    
    print(f"REQUIRED FIELDS ({len(required_fields)}):")
    print("-" * 40)
    for field in required_fields:
        print(f"* {field['name']} ({field['type']})")
        if field['description']:
            print(f"  Description: {field['description']}")
        if 'values' in field:
            values_preview = field['values'][:5] if len(field['values']) > 5 else field['values']
            print(f"  Allowed values: {values_preview}")
            if len(field['values']) > 5:
                print(f"  ... and {len(field['values']) - 5} more")
        print("")
    
    print(f"OPTIONAL FIELDS ({len(optional_fields)}):")
    print("-" * 40)
    for field in optional_fields:
        print(f"+ {field['name']} ({field['type']})")
        if field['description']:
            print(f"  Description: {field['description']}")
        if 'values' in field:
            values_preview = field['values'][:3] if len(field['values']) > 3 else field['values']
            print(f"  Values: {values_preview}")
            if len(field['values']) > 3:
                print(f"  ... and {len(field['values']) - 3} more")
        print("")
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"avito_snegohody_fields_{timestamp}.json"
    
    output_data = {
        'category': 'snegohody',
        'timestamp': timestamp,
        'summary': {
            'total_fields': len(fields),
            'required_fields': len(required_fields),
            'optional_fields': len(optional_fields)
        },
        'required_fields': required_fields,
        'optional_fields': optional_fields,
        'raw_data': fields_data
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Field data saved to: {filename}")
    
    # Show key insights
    print(f"\nKEY INSIGHTS FOR XML GENERATION:")
    print("=" * 50)
    
    # Find important fields for snowmobiles
    important_terms = ['power', 'engine', 'year', 'model', 'make', 'price', 'title']
    important_fields = []
    
    for field in required_fields + optional_fields:
        field_name_lower = field['name'].lower()
        if any(term in field_name_lower for term in important_terms):
            important_fields.append(field)
    
    print("Important fields for snowmobile listings:")
    for field in important_fields:
        status = "REQUIRED" if field['required'] else "OPTIONAL"
        print(f"  {field['name']} - {status}")
    
    return output_data

if __name__ == "__main__":
    print("Getting Avito snowmobile fields...")
    fields_data = get_snegohody_fields()
    
    if fields_data:
        analyze_fields_simple(fields_data)
        print("\nSUCCESS: Snowmobile field requirements retrieved!")
    else:
        print("FAILED: Could not retrieve field requirements")