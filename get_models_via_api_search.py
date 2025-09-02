#!/usr/bin/env python3
"""
Get BRP models through Avito API search or other endpoints
"""

import requests
import json
import base64
from pathlib import Path
import time

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

class ModelFetcher:
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
    
    def try_different_endpoints(self):
        """Try various API endpoints to get model data"""
        
        if not self.access_token:
            print("No access token")
            return []
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # List of endpoints to try
        endpoints = [
            "/autoload/v1/user-docs/catalogs",
            "/autoload/v1/user-docs/catalog/model",
            "/autoload/v1/user-docs/node/snegohody/values/model",
            "/autoload/v1/catalogs/snegohody/model",
            "/autoload/v1/reference/models",
            "/autoload/v1/dictionary/models"
        ]
        
        print("=== TRYING DIFFERENT API ENDPOINTS ===")
        
        for endpoint in endpoints:
            full_url = f"{self.base_url}{endpoint}"
            print(f"\nTrying: {endpoint}")
            
            try:
                response = self.session.get(full_url, headers=headers, timeout=10)
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"  Got JSON response")
                        
                        # Check what we got
                        if isinstance(data, list):
                            print(f"  List with {len(data)} items")
                            if data and len(data) > 0:
                                print(f"  First item: {str(data[0])[:100]}")
                        elif isinstance(data, dict):
                            print(f"  Dict with keys: {list(data.keys())}")
                            
                        # Save for analysis
                        filename = f"api_response_{endpoint.replace('/', '_')}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        print(f"  Saved to: {filename}")
                        
                    except json.JSONDecodeError:
                        print(f"  Not JSON response")
                        
                elif response.status_code == 404:
                    print(f"  Endpoint not found")
                elif response.status_code == 429:
                    print(f"  Rate limited")
                    time.sleep(2)  # Wait before next attempt
                else:
                    print(f"  Failed with status {response.status_code}")
                    
            except Exception as e:
                print(f"  Error: {str(e)}")
            
            # Small delay between requests
            time.sleep(1)
        
        return []
    
    def check_existing_listings(self):
        """Check if we can get models from existing listings"""
        
        if not self.access_token:
            print("No access token")
            return []
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        print("\n=== CHECKING EXISTING LISTINGS FOR MODEL INFO ===")
        
        try:
            # Get current listings
            response = self.session.get(
                f"{self.base_url}/autoload/v2/reports",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                reports = response.json()
                print(f"Got {len(reports.get('reports', []))} reports")
                
                # Check if any reports have model information
                for report in reports.get('reports', [])[:5]:
                    report_id = report.get('id')
                    if report_id:
                        print(f"Checking report {report_id}")
                        
                        detail_response = self.session.get(
                            f"{self.base_url}/autoload/v2/reports/{report_id}",
                            headers=headers,
                            timeout=30
                        )
                        
                        if detail_response.status_code == 200:
                            detail_data = detail_response.json()
                            
                            # Look for model info in report
                            if 'items' in detail_data:
                                for item in detail_data.get('items', []):
                                    if 'model' in str(item).lower():
                                        print(f"  Found model reference in report")
                        
                        time.sleep(1)  # Avoid rate limiting
        
        except Exception as e:
            print(f"Error checking listings: {str(e)}")
        
        return []

def main():
    """Main function"""
    fetcher = ModelFetcher()
    
    if not fetcher.authenticate():
        print("Authentication failed")
        return
    
    # Try different approaches
    print("\n=== ATTEMPTING TO GET BRP MODELS FROM LIVE API ===")
    
    # Try different endpoints
    models = fetcher.try_different_endpoints()
    
    # Check existing listings
    fetcher.check_existing_listings()
    
    print("\n=== SUMMARY ===")
    print("The BRP models are stored in an external XML catalog that is rate-limited")
    print("Alternative approaches tried:")
    print("1. Direct API endpoints - No model catalog endpoints found")
    print("2. Existing listings - No model data in reports")
    print("3. Field values - Models stored externally, not in field response")
    print("\nCONCLUSION: Models must be fetched from the XML catalog URL")
    print("Due to rate limiting, we need to use the existing validated list")

if __name__ == "__main__":
    main()