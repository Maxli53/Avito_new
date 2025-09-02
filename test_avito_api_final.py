#!/usr/bin/env python3
"""
Test Avito API endpoints with real credentials using correct endpoints
"""

import requests
import json
import base64
import time
from datetime import datetime
import os
from pathlib import Path

# Load credentials from integration package
def load_credentials():
    """Load Avito API credentials"""
    # Read from integration package .env file
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

class AvitoAPITester:
    def __init__(self):
        self.credentials = load_credentials()
        self.base_url = "https://api.avito.ru"
        self.access_token = None
        self.session = requests.Session()
        
        print(f"Loaded credentials:")
        print(f"Client ID: {self.credentials['client_id']}")
        print(f"Client Secret: {'*' * len(self.credentials['client_secret']) if self.credentials['client_secret'] else 'None'}")
    
    def get_access_token(self):
        """Get OAuth2 access token using client credentials"""
        print("\n=== Testing Authentication ===")
        
        # Prepare client credentials for Basic Auth
        client_id = self.credentials['client_id']
        client_secret = self.credentials['client_secret']
        
        if not client_id or not client_secret:
            print("FAILED: Missing client credentials")
            return False
        
        # Basic Auth header
        credentials_encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {credentials_encoded}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/token",
                headers=headers,
                data=data,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                print(f"SUCCESS: Authentication successful")
                print(f"Token Type: {token_data.get('token_type')}")
                print(f"Expires In: {token_data.get('expires_in')} seconds")
                return True
            else:
                print(f"FAILED: Authentication failed")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: Authentication error: {str(e)}")
            return False
    
    def test_autoload_profile(self):
        """Test autoload profile endpoint"""
        if not self.access_token:
            print("FAILED: No access token available")
            return False
        
        print("\n=== Testing Autoload Profile ===")
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/autoload/v1/profile",
                headers=headers,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                profile_data = response.json()
                print("SUCCESS: Autoload profile retrieved")
                # Print safely without encoding issues
                print("Profile data structure:")
                for key in profile_data.keys():
                    print(f"  - {key}: {type(profile_data[key])}")
                return True
            else:
                print(f"FAILED: Autoload profile request failed")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: Autoload profile error: {str(e)}")
            return False
    
    def test_autoload_reports(self):
        """Test autoload reports endpoint"""
        if not self.access_token:
            print("FAILED: No access token available")
            return False
        
        print("\n=== Testing Autoload Reports ===")
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/autoload/v2/reports",
                headers=headers,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                reports_data = response.json()
                print("SUCCESS: Autoload reports retrieved")
                print(f"Number of reports: {len(reports_data) if isinstance(reports_data, list) else 'N/A'}")
                return True
            else:
                print(f"FAILED: Autoload reports request failed")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: Autoload reports error: {str(e)}")
            return False
    
    def test_autoload_last_report(self):
        """Test autoload last completed report endpoint"""
        if not self.access_token:
            print("FAILED: No access token available")
            return False
        
        print("\n=== Testing Last Completed Report ===")
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/autoload/v2/reports/last_completed_report",
                headers=headers,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                report_data = response.json()
                print("SUCCESS: Last completed report retrieved")
                # Print structure without encoding issues
                print("Report data structure:")
                if isinstance(report_data, dict):
                    for key in report_data.keys():
                        print(f"  - {key}: {type(report_data[key])}")
                return True
            else:
                print(f"FAILED: Last report request failed")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: Last report error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all API tests"""
        print("Starting Avito API Tests with Correct Endpoints")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        results = {}
        
        # Test 1: Authentication
        results['auth'] = self.get_access_token()
        
        if results['auth']:
            # Test 2: Autoload Profile
            results['autoload_profile'] = self.test_autoload_profile()
            
            # Test 3: Autoload Reports
            results['autoload_reports'] = self.test_autoload_reports()
            
            # Test 4: Last Completed Report
            results['last_report'] = self.test_autoload_last_report()
        else:
            print("FAILED: Skipping other tests due to authentication failure")
            results['autoload_profile'] = False
            results['autoload_reports'] = False
            results['last_report'] = False
        
        # Summary
        print("\n=== TEST RESULTS SUMMARY ===")
        for test_name, success in results.items():
            status = "PASSED" if success else "FAILED"
            print(f"{test_name.upper()}: {status}")
        
        passed = sum(results.values())
        total = len(results)
        print(f"\nOverall: {passed}/{total} tests passed")
        
        return results

if __name__ == "__main__":
    tester = AvitoAPITester()
    results = tester.run_all_tests()