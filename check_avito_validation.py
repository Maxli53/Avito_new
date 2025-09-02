#!/usr/bin/env python3
"""
Check Avito validation methods and field content requirements
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

class AvitoValidationChecker:
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
    
    def check_upload_endpoint(self):
        """Check upload endpoint details for validation info"""
        if not self.access_token:
            return False
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        print("\n=== Checking Upload Endpoint ===")
        
        # The upload endpoint expects a URL parameter
        # Let's try with your current (broken) XML URL to see validation response
        
        xml_url = "http://conventum.kg/api/avito/test_corrected_profile.xml"
        
        try:
            # Try to trigger upload validation
            response = self.session.post(
                f"{self.base_url}/autoload/v1/upload",
                headers=headers,
                json={"url": xml_url},
                timeout=30
            )
            
            print(f"Upload validation status: {response.status_code}")
            print(f"Response: {response.text}")
            
            # This should give us validation errors about the missing XML
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        print(f"Validation error details: {error_data['error']}")
                except:
                    pass
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Upload endpoint error: {str(e)}")
            return False
    
    def analyze_error_reports(self):
        """Analyze recent error reports for validation patterns"""
        if not self.access_token:
            return False
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        print("\n=== Analyzing Error Reports for Validation Patterns ===")
        
        try:
            # Get recent reports with errors
            response = self.session.get(
                f"{self.base_url}/autoload/v2/reports",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                reports_data = response.json()
                
                if 'reports' in reports_data:
                    reports = reports_data['reports']
                    error_reports = [r for r in reports if r.get('status') == 'error']
                    
                    print(f"Found {len(error_reports)} error reports to analyze")
                    
                    # Analyze first few error reports for validation issues
                    for i, report in enumerate(error_reports[:3]):
                        print(f"\n--- Error Report #{i+1} ---")
                        print(f"ID: {report.get('id')}")
                        print(f"Date: {report.get('started_at')}")
                        
                        # Get detailed report
                        report_id = report.get('id')
                        if report_id:
                            self.get_detailed_error_report(report_id)
                
                return True
            else:
                print(f"Failed to get reports: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error analyzing reports: {str(e)}")
            return False
    
    def get_detailed_error_report(self, report_id):
        """Get detailed error report for validation analysis"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/autoload/v2/reports/{report_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                report_data = response.json()
                
                # Look for validation-related events
                if 'events' in report_data:
                    events = report_data['events']
                    print(f"  Events found: {len(events)}")
                    
                    for event in events:
                        event_type = event.get('type', 'unknown')
                        event_code = event.get('code', 'unknown')
                        description = event.get('description', '')
                        
                        print(f"    Event: {event_type} (Code: {event_code})")
                        print(f"    Description: {description}")
                        
                        # Look for field validation errors
                        if 'field' in description.lower() or 'validation' in description.lower():
                            print(f"    >>> VALIDATION ERROR DETECTED <<<")
                        
                        print()
                
                # Check section stats for more validation info
                if 'section_stats' in report_data:
                    stats = report_data['section_stats']
                    print(f"  Processing stats: {stats}")
                
            else:
                print(f"  Could not get detailed report: {response.status_code}")
                
        except Exception as e:
            print(f"  Error getting detailed report: {str(e)}")
    
    def check_field_constraints_from_api(self):
        """Check if API provides field constraint information"""
        if not self.access_token:
            return False
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        print("\n=== Checking Field Constraints from API ===")
        
        try:
            # Get the snegohody fields again but focus on validation rules
            response = self.session.get(
                f"{self.base_url}/autoload/v1/user-docs/node/snegohody/fields",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                fields_data = response.json()
                
                if 'fields' in fields_data:
                    fields = fields_data['fields']
                    
                    print(f"Analyzing {len(fields)} fields for validation constraints...")
                    
                    validation_rules = []
                    
                    for field in fields:
                        tag = field.get('tag', 'Unknown')
                        descriptions = field.get('descriptions', '')
                        
                        # Look for validation hints in descriptions
                        validation_keywords = [
                            'обязательн', 'требует', 'должн', 'нельзя', 'запрещен',
                            'формат', 'длина', 'символ', 'число', 'диапазон',
                            'required', 'must', 'format', 'length', 'characters'
                        ]
                        
                        description_lower = descriptions.lower()
                        has_validation = any(keyword in description_lower for keyword in validation_keywords)
                        
                        if has_validation:
                            validation_rules.append({
                                'field': tag,
                                'description': descriptions[:300] + '...' if len(descriptions) > 300 else descriptions
                            })
                    
                    print(f"\nFound {len(validation_rules)} fields with validation hints:")
                    print("-" * 60)
                    
                    for rule in validation_rules:
                        print(f"Field: {rule['field']}")
                        print(f"Validation info: {rule['description']}")
                        print()
                    
                    return len(validation_rules) > 0
                
            else:
                print(f"Failed to get field constraints: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error checking field constraints: {str(e)}")
            return False
    
    def get_validation_from_current_errors(self):
        """Get validation requirements from current error messages"""
        print("\n=== Current Error Analysis ===")
        
        # We know from your profile data that you have recent errors
        # Let's analyze the specific error message
        
        known_error = {
            'code': 108,
            'type': 'error',
            'description': 'Не удалось скачать файл, ошибка: Not Found (404), URL: http://conventum.kg/api/avito/test_corrected_profile.xml'
        }
        
        print("Current Error Analysis:")
        print(f"Error Code: {known_error['code']}")
        print(f"Error Type: {known_error['type']}")
        print(f"Description: {known_error['description']}")
        print()
        
        print("This error indicates:")
        print("1. Avito can reach your server")
        print("2. Avito is looking for the exact filename: test_corrected_profile.xml")
        print("3. Once file exists, Avito will download and validate XML content")
        print("4. Content validation errors will appear in subsequent reports")
        print()
        
        return True
    
    def run_validation_analysis(self):
        """Run complete validation analysis"""
        print("AVITO VALIDATION METHODS ANALYSIS")
        print("=" * 50)
        
        if not self.authenticate():
            return False
        
        # Check various validation methods
        results = {
            'upload_endpoint': self.check_upload_endpoint(),
            'error_reports': self.analyze_error_reports(), 
            'field_constraints': self.check_field_constraints_from_api(),
            'current_errors': self.get_validation_from_current_errors()
        }
        
        print(f"\n=== VALIDATION ANALYSIS SUMMARY ===")
        for method, success in results.items():
            status = "FOUND" if success else "NOT FOUND"
            print(f"{method.replace('_', ' ').title()}: {status}")
        
        print(f"\nRECOMMENDATION:")
        print("1. Upload XML file first to trigger content validation")
        print("2. Check error reports after upload for specific field issues")
        print("3. Use upload endpoint for real-time validation testing")
        print("4. Field constraints are embedded in API descriptions")
        
        return any(results.values())

if __name__ == "__main__":
    checker = AvitoValidationChecker()
    success = checker.run_validation_analysis()