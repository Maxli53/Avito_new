#!/usr/bin/env python3
"""
Get Avito profile data and current listings from live API
"""

import requests
import json
import base64
from datetime import datetime
from pathlib import Path

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

class AvitoDataRetriever:
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
    
    def get_profile_data(self):
        """Get detailed autoload profile data"""
        if not self.access_token:
            return None
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        print("\n=== Getting Autoload Profile Data ===")
        
        try:
            # Try both v1 and v2 profile endpoints
            endpoints = [
                ("/autoload/v1/profile", "V1 Profile"),
                ("/autoload/v2/profile", "V2 Profile")
            ]
            
            profile_data = {}
            
            for endpoint, name in endpoints:
                response = self.session.get(f"{self.base_url}{endpoint}", headers=headers)
                print(f"{name} Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    profile_data[name] = data
                    print(f"{name} data retrieved successfully")
                else:
                    print(f"{name} failed: {response.text}")
                    profile_data[name] = None
            
            return profile_data
            
        except Exception as e:
            print(f"Profile data error: {str(e)}")
            return None
    
    def get_reports_data(self):
        """Get autoload reports data"""
        if not self.access_token:
            return None
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        print("\n=== Getting Autoload Reports ===")
        
        try:
            reports_data = {}
            
            # Get reports list
            response = self.session.get(f"{self.base_url}/autoload/v2/reports", headers=headers)
            print(f"Reports List Status: {response.status_code}")
            
            if response.status_code == 200:
                reports_list = response.json()
                reports_data['reports_list'] = reports_list
                print(f"Reports list retrieved: {len(reports_list) if isinstance(reports_list, list) else 'Not a list'}")
                
                # Get each report details if we have reports
                if isinstance(reports_list, list) and len(reports_list) > 0:
                    reports_data['detailed_reports'] = []
                    for i, report in enumerate(reports_list[:3]):  # Get first 3 reports
                        if isinstance(report, dict) and 'report_id' in report:
                            report_id = report['report_id']
                            detail_response = self.session.get(
                                f"{self.base_url}/autoload/v2/reports/{report_id}",
                                headers=headers
                            )
                            if detail_response.status_code == 200:
                                reports_data['detailed_reports'].append(detail_response.json())
                                print(f"Report {report_id} details retrieved")
            else:
                print(f"Reports list failed: {response.text}")
                reports_data['reports_list'] = None
            
            # Get last completed report
            response = self.session.get(f"{self.base_url}/autoload/v2/reports/last_completed_report", headers=headers)
            print(f"Last Report Status: {response.status_code}")
            
            if response.status_code == 200:
                last_report = response.json()
                reports_data['last_completed_report'] = last_report
                print("Last completed report retrieved")
            else:
                print(f"Last report failed: {response.text}")
                reports_data['last_completed_report'] = None
                
            return reports_data
            
        except Exception as e:
            print(f"Reports data error: {str(e)}")
            return None
    
    def get_items_data(self):
        """Get items/listings data"""
        if not self.access_token:
            return None
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        print("\n=== Getting Items Data ===")
        
        try:
            items_data = {}
            
            # Try to get items through various endpoints
            endpoints_to_try = [
                ("/autoload/v2/items/avito_ids", "Avito IDs"),
                ("/autoload/v2/items/ad_ids", "Ad IDs")
            ]
            
            for endpoint, name in endpoints_to_try:
                response = self.session.get(f"{self.base_url}{endpoint}", headers=headers)
                print(f"{name} Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    items_data[name] = data
                    print(f"{name} retrieved successfully")
                else:
                    print(f"{name} failed: {response.text}")
                    items_data[name] = None
            
            return items_data
            
        except Exception as e:
            print(f"Items data error: {str(e)}")
            return None
    
    def save_data_to_files(self, profile_data, reports_data, items_data):
        """Save retrieved data to JSON files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save profile data
        if profile_data:
            with open(f"avito_profile_data_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            print(f"Profile data saved to avito_profile_data_{timestamp}.json")
        
        # Save reports data
        if reports_data:
            with open(f"avito_reports_data_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump(reports_data, f, indent=2, ensure_ascii=False)
            print(f"Reports data saved to avito_reports_data_{timestamp}.json")
        
        # Save items data
        if items_data:
            with open(f"avito_items_data_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump(items_data, f, indent=2, ensure_ascii=False)
            print(f"Items data saved to avito_items_data_{timestamp}.json")
    
    def run_data_collection(self):
        """Run complete data collection"""
        print("Starting Avito Data Collection")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        if not self.authenticate():
            print("Failed to authenticate - aborting data collection")
            return
        
        # Collect all data
        profile_data = self.get_profile_data()
        reports_data = self.get_reports_data()
        items_data = self.get_items_data()
        
        # Save to files
        self.save_data_to_files(profile_data, reports_data, items_data)
        
        print("\n=== DATA COLLECTION SUMMARY ===")
        print(f"Profile Data: {'Retrieved' if profile_data else 'Failed'}")
        print(f"Reports Data: {'Retrieved' if reports_data else 'Failed'}")
        print(f"Items Data: {'Retrieved' if items_data else 'Failed'}")
        
        return {
            'profile': profile_data,
            'reports': reports_data,
            'items': items_data
        }

if __name__ == "__main__":
    retriever = AvitoDataRetriever()
    data = retriever.run_data_collection()