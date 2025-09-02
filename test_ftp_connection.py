#!/usr/bin/env python3
"""
Test FTP connection to conventum.kg server using credentials from .env
"""

import ftplib
import os
from pathlib import Path
from datetime import datetime

def load_ftp_credentials():
    """Load FTP credentials from integration package"""
    env_path = Path("Avito_I/INTEGRATION_PACKAGE/credentials/.env")
    credentials = {}
    
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    credentials[key] = value
    
    # Note: There are two FTP_PASSWORD entries - use the longer one
    ftp_password = credentials.get('FTP_PASSWORD', '')
    if len(ftp_password) < 20:  # The short one is for ridebase.fi
        # Look for the longer password (for conventum.kg)
        for key, value in credentials.items():
            if 'PASSWORD' in key and len(value) > 20:
                ftp_password = value
                break
    
    return {
        'server': credentials.get('FTP_CLIENT_SERVER', '176.126.165.67'),
        'username': credentials.get('FTP_CLIENT_USERNAME', 'user133859'),
        'password': ftp_password,
        'port': int(credentials.get('FTP_CLIENT_PORT', '21')),
        'path': credentials.get('FTP_FILE_PATH', '/www/conventum.kg/api/avito')
    }

class FTPTester:
    def __init__(self):
        self.credentials = load_ftp_credentials()
        self.ftp = None
        
        print("FTP Connection Test")
        print(f"Server: {self.credentials['server']}")
        print(f"Port: {self.credentials['port']}")
        print(f"Username: {self.credentials['username']}")
        print(f"Password: {'*' * len(self.credentials['password']) if self.credentials['password'] else 'None'}")
        print(f"Target Path: {self.credentials['path']}")
    
    def connect(self):
        """Establish FTP connection"""
        try:
            print(f"\n=== Connecting to FTP Server ===")
            
            # Create FTP connection
            self.ftp = ftplib.FTP()
            
            # Connect to server
            print(f"Connecting to {self.credentials['server']}:{self.credentials['port']}...")
            self.ftp.connect(self.credentials['server'], self.credentials['port'])
            
            # Login
            print(f"Logging in as {self.credentials['username']}...")
            self.ftp.login(self.credentials['username'], self.credentials['password'])
            
            # Get welcome message
            print(f"SUCCESS: Connected to FTP server")
            print(f"Welcome Message: {self.ftp.getwelcome()}")
            
            return True
            
        except ftplib.error_perm as e:
            print(f"PERMISSION ERROR: {str(e)}")
            return False
        except ftplib.error_temp as e:
            print(f"TEMPORARY ERROR: {str(e)}")
            return False
        except Exception as e:
            print(f"CONNECTION ERROR: {str(e)}")
            return False
    
    def test_directory_access(self):
        """Test directory access and permissions"""
        if not self.ftp:
            print("ERROR: No FTP connection")
            return False
        
        try:
            print(f"\n=== Testing Directory Access ===")
            
            # Get current directory
            current_dir = self.ftp.pwd()
            print(f"Current Directory: {current_dir}")
            
            # Try to change to target directory
            target_path = self.credentials['path']
            print(f"Attempting to access: {target_path}")
            
            # Split path and navigate step by step
            path_parts = target_path.strip('/').split('/')
            
            for part in path_parts:
                try:
                    self.ftp.cwd(part)
                    current_dir = self.ftp.pwd()
                    print(f"SUCCESS: Navigated to {current_dir}")
                except ftplib.error_perm as e:
                    print(f"FAILED: Cannot access '{part}' - {str(e)}")
                    return False
            
            print(f"SUCCESS: Full path accessible - {self.ftp.pwd()}")
            return True
            
        except Exception as e:
            print(f"DIRECTORY ACCESS ERROR: {str(e)}")
            return False
    
    def list_directory_contents(self):
        """List contents of current directory"""
        if not self.ftp:
            return False
        
        try:
            print(f"\n=== Directory Contents ===")
            
            # List files and directories
            files = []
            self.ftp.retrlines('LIST', files.append)
            
            if files:
                print(f"Found {len(files)} items:")
                for file_info in files:
                    print(f"  {file_info}")
            else:
                print("Directory is empty")
            
            # Check for existing XML file
            try:
                file_list = self.ftp.nlst()
                xml_files = [f for f in file_list if f.endswith('.xml')]
                if xml_files:
                    print(f"\nXML files found: {xml_files}")
                else:
                    print(f"\nNo XML files found")
            except:
                print("Could not get detailed file list")
            
            return True
            
        except Exception as e:
            print(f"LIST DIRECTORY ERROR: {str(e)}")
            return False
    
    def test_file_operations(self):
        """Test file upload/download capabilities"""
        if not self.ftp:
            return False
        
        try:
            print(f"\n=== Testing File Operations ===")
            
            # Create a test file
            test_filename = f"ftp_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            test_content = f"FTP Test File\nCreated: {datetime.now().isoformat()}\nServer: {self.credentials['server']}"
            
            # Write test file locally
            with open(test_filename, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            # Upload test file
            print(f"Uploading test file: {test_filename}")
            with open(test_filename, 'rb') as f:
                self.ftp.storbinary(f'STOR {test_filename}', f)
            print(f"SUCCESS: File uploaded")
            
            # Verify file exists
            file_list = self.ftp.nlst()
            if test_filename in file_list:
                print(f"SUCCESS: File verified on server")
                
                # Get file size
                file_size = self.ftp.size(test_filename)
                print(f"File size: {file_size} bytes")
            else:
                print(f"WARNING: File not found in directory listing")
            
            # Download test file to verify
            download_filename = f"downloaded_{test_filename}"
            print(f"Downloading file as: {download_filename}")
            with open(download_filename, 'wb') as f:
                self.ftp.retrbinary(f'RETR {test_filename}', f.write)
            print(f"SUCCESS: File downloaded")
            
            # Compare files
            with open(download_filename, 'r', encoding='utf-8') as f:
                downloaded_content = f.read()
            
            if downloaded_content == test_content:
                print(f"SUCCESS: File content matches")
            else:
                print(f"WARNING: File content differs")
            
            # Cleanup test files
            try:
                self.ftp.delete(test_filename)
                print(f"SUCCESS: Test file deleted from server")
            except:
                print(f"WARNING: Could not delete test file from server")
            
            # Cleanup local files
            for filename in [test_filename, download_filename]:
                try:
                    os.remove(filename)
                except:
                    pass
            
            return True
            
        except Exception as e:
            print(f"FILE OPERATIONS ERROR: {str(e)}")
            return False
    
    def check_xml_file_status(self):
        """Check status of the problematic XML file"""
        if not self.ftp:
            return False
        
        try:
            print(f"\n=== Checking XML File Status ===")
            
            xml_filename = "test_corrected_profile.xml"
            
            # Check if file exists
            try:
                file_list = self.ftp.nlst()
                if xml_filename in file_list:
                    print(f"SUCCESS: {xml_filename} exists on server")
                    
                    # Get file info
                    file_size = self.ftp.size(xml_filename)
                    print(f"File size: {file_size} bytes")
                    
                    # Get modification time
                    try:
                        mod_time = self.ftp.voidcmd(f"MDTM {xml_filename}")
                        print(f"Last modified: {mod_time}")
                    except:
                        print("Could not get modification time")
                    
                else:
                    print(f"MISSING: {xml_filename} NOT found on server")
                    print("This explains the 404 errors in Avito reports")
                    
            except Exception as e:
                print(f"XML CHECK ERROR: {str(e)}")
            
            return True
            
        except Exception as e:
            print(f"XML STATUS ERROR: {str(e)}")
            return False
    
    def close(self):
        """Close FTP connection"""
        if self.ftp:
            try:
                self.ftp.quit()
                print(f"\nFTP connection closed")
            except:
                try:
                    self.ftp.close()
                except:
                    pass
    
    def run_full_test(self):
        """Run complete FTP server test"""
        print(f"Starting FTP Server Test")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        results = {
            'connection': False,
            'directory_access': False,
            'file_operations': False,
            'xml_status': False
        }
        
        try:
            # Test 1: Connection
            results['connection'] = self.connect()
            
            if results['connection']:
                # Test 2: Directory Access
                results['directory_access'] = self.test_directory_access()
                
                if results['directory_access']:
                    # List directory contents
                    self.list_directory_contents()
                    
                    # Test 3: File Operations
                    results['file_operations'] = self.test_file_operations()
                    
                    # Test 4: XML File Status
                    results['xml_status'] = self.check_xml_file_status()
            
            # Summary
            print(f"\n=== FTP TEST RESULTS SUMMARY ===")
            for test_name, success in results.items():
                status = "PASSED" if success else "FAILED"
                print(f"{test_name.upper().replace('_', ' ')}: {status}")
            
            passed = sum(results.values())
            total = len(results)
            print(f"\nOverall: {passed}/{total} tests passed")
            
            if passed == total:
                print(f"SUCCESS: FTP server is fully operational")
            elif results['connection']:
                print(f"PARTIAL: Connection works but some features failed")
            else:
                print(f"FAILED: Cannot connect to FTP server")
            
            return results
            
        finally:
            self.close()

if __name__ == "__main__":
    tester = FTPTester()
    results = tester.run_full_test()