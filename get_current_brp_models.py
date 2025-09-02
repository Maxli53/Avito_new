#!/usr/bin/env python3
"""
Get current BRP models list from live Avito API
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

class CurrentBRPModelsRetriever:
    def __init__(self):
        self.credentials = load_credentials()
        self.base_url = "https://api.avito.ru"
        self.access_token = None
        self.session = requests.Session()
        
    def authenticate(self):
        """Get OAuth2 access token"""
        client_id = self.credentials['client_id']
        client_secret = self.credentials['client_secret']
        
        if not client_id or not client_secret:
            print("FAILED: Missing client credentials")
            return False
        
        credentials_encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {credentials_encoded}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {'grant_type': 'client_credentials'}
        
        try:
            response = self.session.post(f"{self.base_url}/token", headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                print("Authentication successful")
                return True
            else:
                print(f"Authentication failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return False
    
    def get_snowmobile_fields(self):
        """Get current snowmobile fields from API"""
        if not self.access_token:
            return None
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        print("\n=== Getting Current Snowmobile Fields ===")
        
        try:
            response = self.session.get(
                f"{self.base_url}/autoload/v1/user-docs/node/snegohody/fields",
                headers=headers,
                timeout=30
            )
            
            print(f"Fields API status: {response.status_code}")
            
            if response.status_code == 200:
                fields_data = response.json()
                print("SUCCESS: Current fields retrieved from live API")
                return fields_data
            else:
                print(f"FAILED: Fields request failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"ERROR: Fields request error: {str(e)}")
            return None
    
    def extract_brp_models(self, fields_data):
        """Extract current BRP models from Model field values"""
        print("\n=== Extracting Current BRP Models ===")
        
        if not fields_data or 'fields' not in fields_data:
            print("No fields data available")
            return []
        
        fields = fields_data['fields']
        model_field = None
        
        # Find the Model field
        for field in fields:
            tag = field.get('tag', '')
            label = field.get('label', '')
            
            if tag.lower() == 'model' or 'модель' in label.lower():
                model_field = field
                print(f"Found Model field: {tag}")
                break
        
        if not model_field:
            print("Model field not found in API response")
            return []
        
        # Debug: print model field structure
        print("DEBUG: Model field structure:")
        print(f"  Keys: {list(model_field.keys())}")
        if 'content' in model_field:
            print(f"  Content entries: {len(model_field['content'])}")
            for i, content in enumerate(model_field['content']):
                print(f"    Content {i} keys: {list(content.keys())}")
                if 'values_link_xml' in content:
                    print(f"    Values XML Link: {content['values_link_xml']}")
                if 'is_catalog' in content:
                    print(f"    Is Catalog: {content['is_catalog']}")
                if 'name_in_catalog' in content:
                    print(f"    Catalog Name: {content['name_in_catalog']}")
        
        # Check for values_link_xml - this might contain the models
        if 'content' in model_field and model_field['content']:
            content = model_field['content'][0]
            if 'values_link_xml' in content:
                xml_link = content['values_link_xml']
                print(f"Found values XML link: {xml_link}")
                # Try to fetch the XML catalog
                return self.get_models_from_xml_catalog(xml_link)
        
        # Extract model values
        brp_models = []
        all_models = []
        
        # Check different possible locations for values
        content_entries = model_field.get('content', [])
        for content in content_entries:
            if 'values' in content:
                values = content['values']
                print(f"Processing {len(values)} model values from content...")
                
                for i, value in enumerate(values):
                    # Handle different value formats
                    if isinstance(value, dict):
                        model_name = value.get('name', value.get('value', value.get('label', str(value))))
                    else:
                        model_name = str(value)
                    
                    all_models.append(model_name)
                    
                    # Show first 5 models for debugging
                    if i < 5:
                        print(f"    Model {i+1}: {model_name}")
                    
                    # Filter for BRP models (containing BRP brands)
                    model_lower = model_name.lower()
                    brp_brands = ['ski-doo', 'lynx', 'expedition', 'mxz', 'renegade', 'summit', 'skandic', 'tundra', 'brp']
                    
                    is_brp = any(brand in model_lower for brand in brp_brands)
                    
                    if is_brp:
                        brp_models.append(model_name)
                
                print(f"Found {len(all_models)} total models, {len(brp_models)} are BRP models")
                break
        
        # Also check direct values array if no content values found
        if not brp_models and 'values' in model_field:
            direct_values = model_field['values']
            print(f"Checking direct values array: {len(direct_values)} items")
            
            for i, value in enumerate(direct_values):
                model_name = str(value)
                all_models.append(model_name)
                
                if i < 5:
                    print(f"    Direct model {i+1}: {model_name}")
                
                model_lower = model_name.lower()
                brp_brands = ['ski-doo', 'lynx', 'expedition', 'mxz', 'renegade', 'summit', 'skandic', 'tundra', 'brp']
                
                is_brp = any(brand in model_lower for brand in brp_brands)
                if is_brp and model_name not in brp_models:
                    brp_models.append(model_name)
        
        print(f"RESULT: {len(all_models)} total models, {len(brp_models)} BRP models extracted")
        return sorted(brp_models)
    
    def get_models_from_xml_catalog(self, xml_url):
        """Fetch BRP models from XML catalog URL"""
        print(f"\n=== Fetching Models from XML Catalog ===")
        
        # Try different approach - get catalog through authenticated API
        if not self.access_token:
            print("No access token available")
            return []
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Try to get the catalog data through API endpoint instead of direct XML
            catalog_endpoint = f"{self.base_url}/autoload/v1/user-docs/node/snegohody/catalog/model"
            print(f"Trying catalog endpoint: {catalog_endpoint}")
            
            response = self.session.get(catalog_endpoint, headers=headers, timeout=30)
            print(f"Catalog API status: {response.status_code}")
            
            if response.status_code == 200:
                # Check if response is JSON or XML
                content_type = response.headers.get('content-type', '')
                
                if 'json' in content_type:
                    # Handle JSON response
                    catalog_data = response.json()
                    print(f"Got JSON catalog data")
                    
                    models = []
                    brp_models = []
                    
                    # Extract models from JSON structure
                    if isinstance(catalog_data, list):
                        for item in catalog_data:
                            if isinstance(item, dict):
                                model_name = item.get('name', item.get('value', str(item)))
                            else:
                                model_name = str(item)
                            models.append(model_name)
                    elif isinstance(catalog_data, dict):
                        if 'models' in catalog_data:
                            for model in catalog_data['models']:
                                model_name = model.get('name', str(model)) if isinstance(model, dict) else str(model)
                                models.append(model_name)
                        elif 'values' in catalog_data:
                            for value in catalog_data['values']:
                                model_name = value.get('name', str(value)) if isinstance(value, dict) else str(value)
                                models.append(model_name)
                    
                    # Filter for BRP models
                    for model_name in models:
                        model_lower = model_name.lower()
                        brp_brands = ['ski-doo', 'lynx', 'expedition', 'mxz', 'renegade', 'summit', 'skandic', 'tundra', 'brp']
                        
                        is_brp = any(brand in model_lower for brand in brp_brands)
                        if is_brp:
                            brp_models.append(model_name)
                    
                    print(f"Found {len(models)} total models in catalog")
                    print(f"Found {len(brp_models)} BRP models")
                    
                    if brp_models:
                        print("First 10 BRP models from catalog:")
                        for i, model in enumerate(brp_models[:10], 1):
                            print(f"  {i:2d}. {model}")
                    
                    return sorted(brp_models)
                    
                else:
                    # Handle XML response
                    xml_content = response.text
                    print(f"Got XML catalog: {len(xml_content)} characters")
                
                # Parse XML to extract model names
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_content)
                
                # Debug: show XML structure
                print(f"XML root tag: {root.tag}")
                print(f"XML root attributes: {root.attrib}")
                print("First few XML elements:")
                count = 0
                for elem in root.iter():
                    print(f"  Tag: {elem.tag}, Text: {elem.text[:50] if elem.text else None}, Attrib: {elem.attrib}")
                    count += 1
                    if count >= 10:
                        break
                
                models = []
                brp_models = []
                
                # Look for different XML patterns that might contain models
                # Pattern 1: Look for 'option' or 'item' elements with model names
                for option in root.iter('option'):
                    if option.text and len(option.text.strip()) > 2:
                        model_name = option.text.strip()
                        models.append(model_name)
                
                # Pattern 2: Look for elements with 'value' attribute
                for elem in root.iter():
                    if 'value' in elem.attrib and elem.attrib['value']:
                        model_name = elem.attrib['value']
                        if len(model_name) > 2:
                            models.append(model_name)
                
                # Pattern 3: Look for text content in leaf elements
                for elem in root.iter():
                    # Only process leaf elements (no children)
                    if len(elem) == 0 and elem.text and len(elem.text.strip()) > 3:
                        model_name = elem.text.strip()
                        # Skip common XML noise
                        if model_name not in ['true', 'false', '1', '0'] and not model_name.isdigit():
                            models.append(model_name)
                
                # Remove duplicates
                models = list(set(models))
                
                # Filter for BRP models
                for model_name in models:
                    model_lower = model_name.lower()
                    brp_brands = ['ski-doo', 'lynx', 'expedition', 'mxz', 'renegade', 'summit', 'skandic', 'tundra', 'brp']
                    
                    is_brp = any(brand in model_lower for brand in brp_brands)
                    if is_brp:
                        brp_models.append(model_name)
                
                print(f"Found {len(models)} total models in XML")
                print(f"Found {len(brp_models)} BRP models in XML")
                
                if brp_models:
                    print("First 10 BRP models from XML:")
                    for i, model in enumerate(brp_models[:10], 1):
                        print(f"  {i:2d}. {model}")
                
                return sorted(brp_models)
            else:
                print(f"Failed to fetch XML: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error fetching XML catalog: {str(e)}")
            return []
    
    def extract_all_field_constraints(self, fields_data):
        """Extract validation constraints for all fields"""
        print("\n=== Extracting Field Validation Constraints ===")
        
        if not fields_data or 'fields' not in fields_data:
            return {}
        
        field_constraints = {}
        fields = fields_data['fields']
        
        for field in fields:
            tag = field.get('tag', 'Unknown')
            label = field.get('label', '')
            descriptions = field.get('descriptions', '')
            
            # Check if required
            is_required = False
            field_type = 'text'
            allowed_values = []
            
            content_entries = field.get('content', [])
            for content in content_entries:
                is_required = content.get('required', False)
                field_type = content.get('field_type', 'text')
                
                if 'values' in content and content['values']:
                    allowed_values = [v.get('name', v.get('value', str(v))) for v in content['values']]
                break
            
            # Also check direct values
            if 'values' in field and field['values']:
                direct_values = [str(v) for v in field['values']]
                if not allowed_values:
                    allowed_values = direct_values
            
            # Extract validation hints from descriptions
            validation_hints = []
            if descriptions:
                desc_lower = descriptions.lower()
                
                # Look for common validation patterns
                if 'обязательн' in desc_lower or 'required' in desc_lower:
                    validation_hints.append('required')
                if 'число' in desc_lower or 'number' in desc_lower:
                    validation_hints.append('numeric')
                if 'длина' in desc_lower or 'length' in desc_lower:
                    validation_hints.append('length_limited')
                if 'формат' in desc_lower or 'format' in desc_lower:
                    validation_hints.append('format_specific')
            
            field_constraints[tag] = {
                'label': label,
                'required': is_required,
                'type': field_type,
                'allowed_values': allowed_values[:10] if len(allowed_values) > 10 else allowed_values,  # First 10 for display
                'total_values': len(allowed_values),
                'validation_hints': validation_hints,
                'description': descriptions[:200] + '...' if len(descriptions) > 200 else descriptions
            }
        
        return field_constraints
    
    def save_current_data(self, brp_models, field_constraints, raw_fields_data):
        """Save current API data with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save BRP models
        models_data = {
            'source': 'Live Avito API',
            'endpoint': '/autoload/v1/user-docs/node/snegohody/fields',
            'extracted_date': datetime.now().isoformat(),
            'total_brp_models': len(brp_models),
            'brp_models': brp_models
        }
        
        models_filename = f"current_brp_models_{timestamp}.json"
        with open(models_filename, 'w', encoding='utf-8') as f:
            json.dump(models_data, f, indent=2, ensure_ascii=False)
        
        # Save field constraints
        constraints_data = {
            'source': 'Live Avito API',
            'endpoint': '/autoload/v1/user-docs/node/snegohody/fields',
            'extracted_date': datetime.now().isoformat(),
            'total_fields': len(field_constraints),
            'field_constraints': field_constraints,
            'raw_api_response': raw_fields_data
        }
        
        constraints_filename = f"current_field_constraints_{timestamp}.json"
        with open(constraints_filename, 'w', encoding='utf-8') as f:
            json.dump(constraints_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved current data:")
        print(f"  BRP Models: {models_filename}")
        print(f"  Field Constraints: {constraints_filename}")
        
        return models_filename, constraints_filename
    
    def run_current_extraction(self):
        """Main method to get current BRP models and constraints"""
        print("GETTING CURRENT BRP MODELS FROM LIVE AVITO API")
        print("=" * 60)
        
        if not self.authenticate():
            return False
        
        # Get current fields data
        fields_data = self.get_snowmobile_fields()
        if not fields_data:
            print("Failed to retrieve fields data")
            return False
        
        # Extract BRP models
        brp_models = self.extract_brp_models(fields_data)
        if not brp_models:
            print("No BRP models found in API response")
            return False
        
        # Extract field constraints
        field_constraints = self.extract_all_field_constraints(fields_data)
        
        # Save current data
        models_file, constraints_file = self.save_current_data(brp_models, field_constraints, fields_data)
        
        # Print summary
        print(f"\n=== EXTRACTION COMPLETE ===")
        print(f"Current BRP Models: {len(brp_models)}")
        print(f"Field Constraints: {len(field_constraints)}")
        print(f"Required Fields: {sum(1 for f in field_constraints.values() if f['required'])}")
        print(f"Optional Fields: {sum(1 for f in field_constraints.values() if not f['required'])}")
        
        print(f"\nFirst 10 BRP Models:")
        for i, model in enumerate(brp_models[:10], 1):
            print(f"  {i:2d}. {model}")
        
        if len(brp_models) > 10:
            print(f"  ... and {len(brp_models) - 10} more models")
        
        print(f"\nKey Field Constraints:")
        important_fields = ['Id', 'Title', 'Model', 'Price', 'Year', 'Power', 'EngineCapacity']
        for field in important_fields:
            if field in field_constraints:
                constraint = field_constraints[field]
                status = "REQUIRED" if constraint['required'] else "OPTIONAL"
                print(f"  {field}: {status} ({constraint['type']})")
                if constraint['total_values'] > 0:
                    print(f"    {constraint['total_values']} allowed values")
        
        return True

if __name__ == "__main__":
    retriever = CurrentBRPModelsRetriever()
    success = retriever.run_current_extraction()
    
    if success:
        print(f"\nSUCCESS: Current BRP models and validation constraints retrieved from live API")
    else:
        print(f"\nFAILED: Could not retrieve current data from API")