#!/usr/bin/env python3
"""
Test Avito API endpoints with real credentials
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
            print(f"Response Headers: {dict(response.headers)}")
            
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
    
    def test_account_info(self):
        """Test account information endpoint"""
        if not self.access_token:
            print("FAILED: No access token available")
            return False
        
        print("\n=== Testing Account Information ===")
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/core/v1/accounts/self",
                headers=headers,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                account_data = response.json()
                print("SUCCESS: Account information retrieved:")
                print(json.dumps(account_data, indent=2, ensure_ascii=False))
                return True
            else:
                print(f"FAILED: Account info request failed")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: Account info error: {str(e)}")
            return False
    
    def test_autoload_operations(self):
        """Test autoload operations endpoint"""
        if not self.access_token:
            print("FAILED: No access token available")
            return False
        
        print("\n=== Testing Autoload Operations ===")
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Get recent autoload operations
            response = self.session.get(
                f"{self.base_url}/autoload/v1/operations",
                headers=headers,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                operations_data = response.json()
                print("SUCCESS: Autoload operations retrieved:")
                print(json.dumps(operations_data, indent=2, ensure_ascii=False))
                return True
            else:
                print(f"FAILED: Autoload operations request failed")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: Autoload operations error: {str(e)}")
            return False
    
    def test_items_stats(self):
        """Test items statistics endpoint"""
        if not self.access_token:
            print("FAILED: No access token available")
            return False
        
        print("\n=== Testing Items Statistics ===")
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/core/v1/items/stats",
                headers=headers,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                stats_data = response.json()
                print("SUCCESS: Items statistics retrieved:")
                print(json.dumps(stats_data, indent=2, ensure_ascii=False))
                return True
            else:
                print(f"FAILED: Items statistics request failed")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: Items statistics error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all API tests"""
        print("Starting Avito API Tests")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        results = {}
        
        # Test 1: Authentication
        results['auth'] = self.get_access_token()
        
        if results['auth']:
            # Test 2: Account Info
            results['account'] = self.test_account_info()
            
            # Test 3: Autoload Operations
            results['autoload'] = self.test_autoload_operations()
            
            # Test 4: Items Statistics
            results['items_stats'] = self.test_items_stats()
        else:
            print("FAILED: Skipping other tests due to authentication failure")
            results['account'] = False
            results['autoload'] = False
            results['items_stats'] = False
        
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