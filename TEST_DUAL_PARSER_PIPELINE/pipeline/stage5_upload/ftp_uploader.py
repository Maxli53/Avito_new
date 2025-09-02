"""
FTP Uploader Implementation
Handles FTP upload to Avito server with retry logic and connection management
"""

import ftplib
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from io import BytesIO

from .base_uploader import BaseUploader
from ...core import UploadError


class FTPUploader(BaseUploader):
    """
    FTP uploader implementation for Avito marketplace
    
    Handles secure FTP uploads with automatic retry logic,
    connection management, and upload verification.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize FTP uploader
        
        Args:
            config: FTP configuration including host, username, password, remote_path
        """
        super().__init__(config)
        
        # FTP connection settings
        self.host = self.config.get('host', '176.126.165.67')
        self.username = self.config.get('username', 'user133859')
        self.password = self.config.get('password', os.getenv('AVITO_FTP_PASSWORD', ''))
        self.remote_base_path = self.config.get('remote_path', '/test_corrected_profile.xml')
        self.port = self.config.get('port', 21)
        self.timeout = self.config.get('timeout', 30)
        
        # Connection state
        self.ftp_connection: Optional[ftplib.FTP] = None
        self.connected = False
        self.connection_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        
        # Upload settings
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 5)
        
    def connect(self) -> bool:
        """
        Establish FTP connection to Avito server
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            UploadError: If connection fails after retries
        """
        if self.connected and self.ftp_connection:
            return True
        
        if not self.password:
            raise UploadError(
                message="FTP password not configured. Set AVITO_FTP_PASSWORD environment variable.",
                server_host=self.host
            )
        
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Connecting to Avito FTP server: {self.host} (attempt {attempt + 1})")
                
                self.ftp_connection = ftplib.FTP()
                self.ftp_connection.connect(self.host, self.port, self.timeout)
                self.ftp_connection.login(self.username, self.password)
                
                self.connected = True
                self.connection_time = datetime.now()
                self.last_error = None
                
                self.logger.info("FTP connection established successfully")
                return True
                
            except Exception as e:
                self.last_error = str(e)
                self.logger.warning(f"FTP connection attempt {attempt + 1} failed: {e}")
                
                if self.ftp_connection:
                    try:
                        self.ftp_connection.quit()
                    except:
                        pass
                    self.ftp_connection = None
                
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(self.retry_delay)
        
        self.connected = False
        raise UploadError(
            message=f"Failed to connect to FTP server after {self.max_retries} attempts",
            server_host=self.host,
            original_exception=Exception(self.last_error)
        )
    
    def disconnect(self) -> None:
        """Close FTP connection"""
        if self.ftp_connection:
            try:
                self.ftp_connection.quit()
                self.logger.info("FTP connection closed")
            except:
                try:
                    self.ftp_connection.close()
                except:
                    pass
        
        self.ftp_connection = None
        self.connected = False
        self.connection_time = None
    
    def upload_file(self, local_path: Path, remote_path: str) -> bool:
        """
        Upload a single file to FTP server
        
        Args:
            local_path: Path to local file
            remote_path: Destination path on FTP server
            
        Returns:
            True if upload successful, False otherwise
            
        Raises:
            UploadError: If upload fails
        """
        if not self.connected or not self.ftp_connection:
            raise UploadError(
                message="FTP connection not established",
                server_host=self.host,
                upload_path=remote_path
            )
        
        # Validate local file
        if not self.validate_local_file(local_path):
            return False
        
        try:
            file_size = local_path.stat().st_size
            self.logger.info(f"Uploading {local_path} ({file_size} bytes) to {remote_path}")
            
            # Upload file
            with open(local_path, 'rb') as file:
                self.ftp_connection.storbinary(f'STOR {remote_path}', file)
            
            self.logger.info(f"Upload completed: {remote_path}")
            
            # Verify upload
            if self._verify_ftp_upload(remote_path, file_size):
                self.logger.info(f"Upload verified successfully: {remote_path}")
                return True
            else:
                self.logger.error(f"Upload verification failed: {remote_path}")
                return False
            
        except Exception as e:
            raise UploadError(
                message=f"FTP upload failed for {local_path}",
                server_host=self.host,
                upload_path=remote_path,
                file_size=local_path.stat().st_size if local_path.exists() else None,
                original_exception=e
            )
    
    def upload_xml_content(self, xml_content: str, remote_filename: str) -> bool:
        """
        Upload XML content directly as string
        
        Args:
            xml_content: XML content to upload
            remote_filename: Filename on remote server
            
        Returns:
            True if upload successful, False otherwise
        """
        if not self.connected or not self.ftp_connection:
            if not self.connect():
                return False
        
        try:
            self.logger.info(f"Uploading XML content ({len(xml_content)} characters) to {remote_filename}")
            
            # Convert string to bytes and create buffer
            xml_bytes = xml_content.encode('utf-8')
            xml_buffer = BytesIO(xml_bytes)
            
            # Upload XML content
            self.ftp_connection.storbinary(f'STOR {remote_filename}', xml_buffer)
            
            self.logger.info(f"XML upload completed: {remote_filename}")
            
            # Verify upload
            if self._verify_ftp_upload(remote_filename, len(xml_bytes)):
                self.logger.info(f"XML upload verified successfully: {remote_filename}")
                return True
            else:
                self.logger.error(f"XML upload verification failed: {remote_filename}")
                return False
            
        except Exception as e:
            self.logger.error(f"XML upload failed: {e}")
            raise UploadError(
                message=f"FTP XML upload failed",
                server_host=self.host,
                upload_path=remote_filename,
                file_size=len(xml_content.encode('utf-8')),
                original_exception=e
            )
    
    def _verify_ftp_upload(self, remote_path: str, expected_size: int) -> bool:
        """
        Verify FTP upload by checking file exists and size
        
        Args:
            remote_path: Path to remote file
            expected_size: Expected file size in bytes
            
        Returns:
            True if verification successful, False otherwise
        """
        try:
            # List files to check if our file exists
            file_list = self.ftp_connection.nlst()
            remote_filename = remote_path.lstrip('/')
            
            if remote_filename in file_list:
                self.logger.info("Upload verification: File found on server")
                
                # Try to get file size (not all FTP servers support this)
                try:
                    remote_size = self.ftp_connection.size(remote_path)
                    if remote_size == expected_size:
                        self.logger.info(f"Upload verification: Size matches ({remote_size} bytes)")
                        return True
                    else:
                        self.logger.warning(f"Upload verification: Size mismatch - expected {expected_size}, got {remote_size}")
                        return False
                except:
                    # If size check is not supported, just check file existence
                    self.logger.info("Upload verification: Size check not supported, assuming success")
                    return True
            else:
                self.logger.error(f"Upload verification: File not found in directory listing")
                return False
                
        except Exception as e:
            self.logger.warning(f"Upload verification failed: {e}")
            return False
    
    def get_remote_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about remote file
        
        Args:
            remote_path: Path to remote file
            
        Returns:
            Dictionary with file info or None if not available
        """
        if not self.connected or not self.ftp_connection:
            return None
        
        try:
            file_list = self.ftp_connection.nlst()
            remote_filename = remote_path.lstrip('/')
            
            if remote_filename not in file_list:
                return None
            
            info = {'exists': True, 'name': remote_filename}
            
            # Try to get file size
            try:
                info['size'] = self.ftp_connection.size(remote_path)
            except:
                info['size'] = None
            
            # Try to get modification time
            try:
                info['modified'] = self.ftp_connection.sendcmd(f'MDTM {remote_path}')
            except:
                info['modified'] = None
            
            return info
            
        except Exception as e:
            self.logger.warning(f"Failed to get remote file info: {e}")
            return None
    
    def list_remote_files(self, path: str = "/") -> List[str]:
        """
        List files in remote directory
        
        Args:
            path: Remote directory path
            
        Returns:
            List of filenames
        """
        if not self.connected or not self.ftp_connection:
            return []
        
        try:
            return self.ftp_connection.nlst(path)
        except Exception as e:
            self.logger.error(f"Failed to list remote files: {e}")
            return []
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status"""
        return {
            'connected': self.connected,
            'server_host': self.host,
            'username': self.username,
            'port': self.port,
            'connection_time': self.connection_time.isoformat() if self.connection_time else None,
            'last_error': self.last_error,
            'timeout': self.timeout
        }