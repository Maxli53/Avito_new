#!/usr/bin/env python3
"""
Get required fields for snowmobile category from Avito API
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

class AvitoFieldsRetriever:
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
    
    def get_category_tree(self):
        """Get category tree to find snowmobile category"""
        if not self.access_token:
            return None
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        print("\n=== Getting Category Tree ===")
        
        try:
            # Try autoload category tree endpoint
            response = self.session.get(
                f"{self.base_url}/autoload/v1/user-docs/tree",
                headers=headers,
                timeout=30
            )
            
            print(f"Category tree status: {response.status_code}")
            
            if response.status_code == 200:
                tree_data = response.json()
                print("Category tree retrieved successfully")
                
                # Look for snowmobile/motorcycle categories
                self.find_snowmobile_categories(tree_data)
                return tree_data
            else:
                print(f"Category tree request failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Category tree error: {str(e)}")
            return None
    
    def find_snowmobile_categories(self, tree_data, parent_path=""):
        """Recursively find snowmobile-related categories"""
        if isinstance(tree_data, dict):
            # Check if this is a category node
            if 'name' in tree_data and 'slug' in tree_data:
                category_name = tree_data.get('name', '').lower()
                category_slug = tree_data.get('slug', '')
                full_path = f"{parent_path}/{category_name}" if parent_path else category_name
                
                # Look for snowmobile/motorcycle related categories
                snowmobile_terms = ['снегоход', 'snowmobile', 'мотоцикл', 'motorcycle', 'мототехник', 'transport']
                
                if any(term in category_name for term in snowmobile_terms):
                    print(f"FOUND RELEVANT CATEGORY:")
                    print(f"  Name: {tree_data.get('name')}")
                    print(f"  Slug: {category_slug}")
                    print(f"  Path: {full_path}")
                    print(f"  ID: {tree_data.get('id', 'N/A')}")
                    
                    # Try to get fields for this category
                    if category_slug:
                        self.get_category_fields(category_slug)
            
            # Recurse into children
            if 'children' in tree_data:
                for child in tree_data['children']:
                    self.find_snowmobile_categories(child, full_path if 'name' in tree_data else parent_path)
        
        elif isinstance(tree_data, list):
            for item in tree_data:
                self.find_snowmobile_categories(item, parent_path)
    
    def get_category_fields(self, category_slug):
        """Get fields for a specific category"""
        if not self.access_token:
            return None
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        print(f"\n=== Getting Fields for Category: {category_slug} ===")
        
        try:
            # Get fields for this category
            response = self.session.get(
                f"{self.base_url}/autoload/v1/user-docs/node/{category_slug}/fields",
                headers=headers,
                timeout=30
            )
            
            print(f"Fields request status: {response.status_code}")
            
            if response.status_code == 200:
                fields_data = response.json()
                print(f"Fields data retrieved for {category_slug}")
                
                self.analyze_fields(fields_data, category_slug)
                return fields_data
            else:
                print(f"Fields request failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Fields request error: {str(e)}")
            return None
    
    def analyze_fields(self, fields_data, category_slug):
        """Analyze and categorize fields"""
        print(f"\n=== Field Analysis for {category_slug} ===")
        
        required_fields = []
        optional_fields = []
        
        if isinstance(fields_data, dict) and 'fields' in fields_data:
            fields = fields_data['fields']
            
            for field in fields:
                field_name = field.get('name', 'Unknown')
                field_type = field.get('type', 'Unknown')
                is_required = field.get('required', False)
                field_description = field.get('description', '')
                
                field_info = {
                    'name': field_name,
                    'type': field_type,
                    'required': is_required,
                    'description': field_description
                }
                
                if 'values' in field:
                    field_info['values'] = field['values']
                
                if is_required:
                    required_fields.append(field_info)
                else:
                    optional_fields.append(field_info)
        
        # Print results
        print(f"\nREQUIRED FIELDS ({len(required_fields)}):")
        for field in required_fields:
            print(f"  - {field['name']} ({field['type']})")
            if field['description']:
                print(f"    Description: {field['description']}")
            if 'values' in field and field['values']:
                print(f"    Allowed values: {field['values'][:5]}...")  # First 5 values
        
        print(f"\nOPTIONAL FIELDS ({len(optional_fields)}):")
        for field in optional_fields:
            print(f"  - {field['name']} ({field['type']})")
            if field['description']:
                print(f"    Description: {field['description']}")
        
        # Save detailed data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"avito_fields_{category_slug}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'category_slug': category_slug,
                'timestamp': timestamp,
                'required_fields': required_fields,
                'optional_fields': optional_fields,
                'raw_data': fields_data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\nDetailed field data saved to: {filename}")
    
    def get_all_snowmobile_fields(self):
        """Main method to get all snowmobile-related fields"""
        print("Getting Avito Snowmobile Category Fields")
        print("=" * 50)
        
        if not self.authenticate():
            print("Failed to authenticate")
            return False
        
        # Get category tree
        tree_data = self.get_category_tree()
        
        if not tree_data:
            print("Failed to get category tree")
            return False
        
        print(f"\n=== SEARCH COMPLETE ===")
        print("Check the output above for snowmobile-related categories and their fields")
        
        return True

if __name__ == "__main__":
    retriever = AvitoFieldsRetriever()
    success = retriever.get_all_snowmobile_fields()
    
    if success:
        print(f"\nSUCCESS: Snowmobile field requirements retrieved")
    else:
        print(f"\nFAILED: Could not retrieve field requirements")