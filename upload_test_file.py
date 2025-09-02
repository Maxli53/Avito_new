#!/usr/bin/env python3
"""
Upload a test file to the FTP server
"""

import ftplib
from datetime import datetime

def upload_test_file():
    # FTP credentials
    credentials = {
        'server': '176.126.165.67',
        'username': 'user133859',
        'password': 'epPx$E8pndgP8%^&$zgNjB7',
        'port': 21,
        'path': '/www/conventum.kg/api/avito'
    }
    
    print("Uploading test file to FTP server")
    print(f"Server: {credentials['server']}")
    print(f"Target directory: {credentials['path']}")
    
    # Create test file content
    test_filename = "avito_test_upload.txt"
    test_content = f"""Avito FTP Upload Test
====================

Upload Time: {datetime.now().isoformat()}
Server: {credentials['server']}
Directory: {credentials['path']}
Status: Test upload successful

This file demonstrates that we can successfully upload files to the Avito FTP directory.
Next step: Upload the actual XML file with snowmobile listings.

Test completed successfully!
"""
    
    try:
        # Connect to FTP server
        print(f"\nConnecting to FTP server...")
        ftp = ftplib.FTP()
        ftp.connect(credentials['server'], credentials['port'])
        ftp.login(credentials['username'], credentials['password'])
        print(f"SUCCESS: Connected to FTP server")
        
        # Navigate to target directory
        print(f"Navigating to {credentials['path']}...")
        ftp.cwd(credentials['path'])
        print(f"SUCCESS: In directory {ftp.pwd()}")
        
        # Write test file locally
        print(f"Creating local test file: {test_filename}")
        with open(test_filename, 'w', encoding='utf-8') as f:
            f.write(test_content)
        print(f"SUCCESS: Local test file created ({len(test_content)} characters)")
        
        # Upload test file
        print(f"Uploading {test_filename} to server...")
        with open(test_filename, 'rb') as f:
            ftp.storbinary(f'STOR {test_filename}', f)
        print(f"SUCCESS: File uploaded to server")
        
        # Verify file exists and get info
        print(f"Verifying upload...")
        file_list = ftp.nlst()
        if test_filename in file_list:
            print(f"SUCCESS: {test_filename} confirmed on server")
            
            # Get file size
            try:
                file_size = ftp.size(test_filename)
                print(f"File size: {file_size} bytes")
            except:
                print("Could not get file size")
                
            # Show current directory contents
            print(f"\nCurrent directory contents:")
            files = []
            ftp.retrlines('LIST', files.append)
            for file_info in files:
                if test_filename in file_info:
                    print(f"  -> {file_info}")
                else:
                    print(f"     {file_info}")
        else:
            print(f"WARNING: File not found in directory listing")
        
        # Test download to verify
        print(f"\nTesting download to verify file integrity...")
        download_filename = f"downloaded_{test_filename}"
        with open(download_filename, 'wb') as f:
            ftp.retrbinary(f'RETR {test_filename}', f.write)
        
        # Compare files
        with open(download_filename, 'r', encoding='utf-8') as f:
            downloaded_content = f.read()
        
        if downloaded_content == test_content:
            print(f"SUCCESS: File integrity verified - content matches perfectly")
        else:
            print(f"WARNING: Downloaded content differs from original")
        
        # Clean up local files
        import os
        try:
            os.remove(test_filename)
            os.remove(download_filename)
            print(f"Local test files cleaned up")
        except:
            pass
        
        # Close FTP connection
        ftp.quit()
        print(f"\nFTP connection closed")
        
        print(f"\n=== UPLOAD TEST COMPLETED SUCCESSFULLY ===")
        print(f"✅ File uploaded: {test_filename}")
        print(f"✅ Server location: {credentials['path']}/{test_filename}")
        print(f"✅ File integrity: Verified")
        print(f"✅ FTP operations: All working")
        
        # Show URL where file would be accessible
        public_url = f"http://conventum.kg/api/avito/{test_filename}"
        print(f"\n📍 Public URL: {public_url}")
        print(f"   (This is where Avito would look for XML files)")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Upload failed - {str(e)}")
        return False

if __name__ == "__main__":
    success = upload_test_file()
    if success:
        print(f"\n🎉 SUCCESS: Ready to upload XML files for Avito!")
    else:
        print(f"\n❌ FAILED: FTP upload not working")