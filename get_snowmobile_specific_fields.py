#!/usr/bin/env python3
"""
Get specific snowmobile category fields from Avito API
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

class AvitoSnowmobileFields:
    def __init__(self):
        self.credentials = load_credentials()
        self.base_url = "https://api.avito.ru"
        self.access_token = None
        self.session = requests.Session()
        
    def authenticate(self):
        """Get OAuth2 access token"""
        client_id = self.credentials['client_id']
        client_secret = self.credentials['client_secret']
        
        credentials_encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {credentials_encoded}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {'grant_type': 'client_credentials'}
        
        response = self.session.post(f"{self.base_url}/token", headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            print("Authentication successful")
            return True
        else:
            print(f"Authentication failed: {response.text}")
            return False
    
    def try_category_slugs(self):
        """Try different category slugs for snowmobiles"""
        # Common Russian slugs for snowmobiles
        potential_slugs = [
            'snegohody',
            'snegokhody', 
            'motocikly_i_mototehnika',
            'mototehnika',
            'transport',
            'motorcycles',
            'snowmobiles'
        ]
        
        successful_fields = {}
        
        for slug in potential_slugs:
            print(f"\n=== Trying category slug: {slug} ===")
            fields = self.get_category_fields(slug)
            if fields:
                successful_fields[slug] = fields
        
        return successful_fields
    
    def get_category_fields(self, category_slug):
        """Get fields for a specific category slug"""
        if not self.access_token:
            return None
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/autoload/v1/user-docs/node/{category_slug}/fields",
                headers=headers,
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                fields_data = response.json()
                print(f"SUCCESS: Fields retrieved for {category_slug}")
                
                # Analyze the fields
                self.analyze_and_display_fields(fields_data, category_slug)
                return fields_data
                
            elif response.status_code == 404:
                print(f"Category '{category_slug}' not found")
                return None
            else:
                print(f"Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting fields for {category_slug}: {str(e)}")
            return None
    
    def analyze_and_display_fields(self, fields_data, category_slug):
        """Analyze and display fields in a readable format"""
        print(f"\n=== FIELD ANALYSIS FOR {category_slug.upper()} ===")
        
        if not isinstance(fields_data, dict):
            print("Invalid fields data format")
            return
        
        # Look for fields in different possible structures
        fields = None
        if 'fields' in fields_data:
            fields = fields_data['fields']
        elif isinstance(fields_data, list):
            fields = fields_data
        
        if not fields:
            print("No fields found in response")
            return
        
        required_fields = []
        optional_fields = []
        snowmobile_fields = []
        
        print(f"\nProcessing {len(fields)} fields...")
        
        for field in fields:
            if not isinstance(field, dict):
                continue
                
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
            
            # Add allowed values if present
            if 'values' in field and field['values']:
                field_info['values'] = field['values']
            
            # Categorize fields
            if is_required:
                required_fields.append(field_info)
            else:
                optional_fields.append(field_info)
            
            # Check if field is snowmobile-specific
            snowmobile_terms = ['мощность', 'объем', 'двигател', 'мотор', 'лошад', 'power', 'engine', 'track', 'snow']
            if any(term in field_name.lower() or term in description.lower() for term in snowmobile_terms):
                snowmobile_fields.append(field_info)
        
        # Display results
        self.display_field_categories(required_fields, optional_fields, snowmobile_fields, category_slug)
        
        # Save detailed data
        self.save_fields_data(fields_data, category_slug, required_fields, optional_fields)
    
    def display_field_categories(self, required_fields, optional_fields, snowmobile_fields, category_slug):
        """Display categorized fields"""
        
        print(f"\n🔴 REQUIRED FIELDS ({len(required_fields)}):")
        print("=" * 40)
        for field in required_fields:
            print(f"✓ {field['name']} ({field['type']})")
            if field['description']:
                print(f"  Description: {field['description']}")
            if 'values' in field:
                values_preview = field['values'][:3] if len(field['values']) > 3 else field['values']
                print(f"  Values: {values_preview}{'...' if len(field['values']) > 3 else ''}")
            print()
        
        print(f"\n🟡 OPTIONAL FIELDS ({len(optional_fields)}):")
        print("=" * 40)
        for field in optional_fields:
            print(f"• {field['name']} ({field['type']})")
            if field['description']:
                print(f"  Description: {field['description']}")
            if 'values' in field:
                values_preview = field['values'][:3] if len(field['values']) > 3 else field['values']
                print(f"  Values: {values_preview}{'...' if len(field['values']) > 3 else ''}")
            print()
        
        print(f"\n🏍️ SNOWMOBILE-SPECIFIC FIELDS ({len(snowmobile_fields)}):")
        print("=" * 50)
        for field in snowmobile_fields:
            req_status = "REQUIRED" if field['required'] else "OPTIONAL"
            print(f"⚡ {field['name']} ({field['type']}) - {req_status}")
            if field['description']:
                print(f"  Description: {field['description']}")
            if 'values' in field:
                print(f"  Allowed values: {field['values']}")
            print()
    
    def save_fields_data(self, raw_data, category_slug, required_fields, optional_fields):
        """Save detailed field data to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"avito_snowmobile_fields_{category_slug}_{timestamp}.json"
        
        output_data = {
            'category_slug': category_slug,
            'timestamp': timestamp,
            'summary': {
                'required_count': len(required_fields),
                'optional_count': len(optional_fields),
                'total_count': len(required_fields) + len(optional_fields)
            },
            'required_fields': required_fields,
            'optional_fields': optional_fields,
            'raw_api_response': raw_data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed field data saved to: {filename}")
    
    def get_xml_template_fields(self):
        """Extract fields from existing XML template"""
        print(f"\n=== XML TEMPLATE ANALYSIS ===")
        print("Fields found in main_template.xml:")
        
        xml_fields = [
            'Id', 'Title', 'Model', 'Availability', 'Price', 'Type', 
            'Year', 'Power', 'EngineCapacity', 'PersonCapacity', 
            'TrackWidth', 'Description', 'Images', 'Address', 
            'Category', 'VehicleType', 'Make', 'EngineType', 
            'Condition', 'Kilometrage', 'AvitoDateBegin', 'AvitoDateEnd'
        ]
        
        # Fixed values from template
        fixed_values = {
            'Address': 'Санкт-Петербург',
            'Category': 'Мотоциклы и мототехника',
            'VehicleType': 'Снегоходы', 
            'Make': 'BRP',
            'EngineType': 'Бензин',
            'Condition': 'Новое',
            'Kilometrage': '0'
        }
        
        print(f"\nTemplate Fields ({len(xml_fields)}):")
        for field in xml_fields:
            if field in fixed_values:
                print(f"  ✓ {field}: {fixed_values[field]} (FIXED)")
            else:
                print(f"  ○ {field}: (DYNAMIC)")
        
        # Type values from reference file
        print(f"\nSnowmobile Type Values (from Авито reference):")
        type_values = [
            'Утилитарный',
            'Спортивный или горный', 
            'Туристический',
            'Детский',
            'Мотобуксировщик'
        ]
        
        for type_val in type_values:
            print(f"  - {type_val}")
    
    def run_complete_analysis(self):
        """Run complete snowmobile fields analysis"""
        print("AVITO SNOWMOBILE FIELDS ANALYSIS")
        print("=" * 60)
        
        if not self.authenticate():
            return False
        
        # Try different category slugs
        successful_fields = self.try_category_slugs()
        
        # Show XML template analysis
        self.get_xml_template_fields()
        
        # Summary
        print(f"\n=== ANALYSIS SUMMARY ===")
        print(f"Categories found: {len(successful_fields)}")
        
        if successful_fields:
            print("Successfully retrieved fields for:")
            for slug in successful_fields.keys():
                print(f"  ✓ {slug}")
        else:
            print("No category fields retrieved from API")
            print("Using XML template structure as reference")
        
        return len(successful_fields) > 0

if __name__ == "__main__":
    analyzer = AvitoSnowmobileFields()
    success = analyzer.run_complete_analysis()