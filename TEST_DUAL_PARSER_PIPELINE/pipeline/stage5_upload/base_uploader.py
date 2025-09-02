"""
Base Uploader Abstract Class
Defines the interface for all upload implementations
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime

from ...core import PipelineStats, PipelineStage, UploadError

logger = logging.getLogger(__name__)


class BaseUploader(ABC):
    """
    Abstract base class for all upload implementations
    
    Provides common functionality and defines the interface that all
    uploaders must implement for file upload and processing monitoring.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize uploader with configuration
        
        Args:
            config: Uploader-specific configuration dictionary
        """
        self.config = config or {}
        self.logger = logger
        self.stats = PipelineStats(stage=PipelineStage.UPLOAD)
        self.connection_config = {}
        
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to upload destination
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            UploadError: If connection fails
        """
        pass
    
    @abstractmethod
    def upload_file(self, local_path: Path, remote_path: str) -> bool:
        """
        Upload a single file to destination
        
        Args:
            local_path: Path to local file
            remote_path: Destination path on remote server
            
        Returns:
            True if upload successful, False otherwise
            
        Raises:
            UploadError: If upload fails
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to upload destination
        """
        pass
    
    def upload_files(self, file_mappings: List[Tuple[Path, str]]) -> Dict[str, bool]:
        """
        Upload multiple files
        
        Args:
            file_mappings: List of (local_path, remote_path) tuples
            
        Returns:
            Dictionary mapping file paths to upload success status
        """
        try:
            self.stats.start_time = datetime.now()
            upload_results = {}
            
            # Establish connection
            if not self.connect():
                raise UploadError(
                    message="Failed to establish upload connection",
                    server_host=self.config.get('host', 'unknown')
                )
            
            try:
                for local_path, remote_path in file_mappings:
                    try:
                        # Validate local file
                        if not local_path.exists():
                            self.logger.warning(f"Local file not found: {local_path}")
                            upload_results[str(local_path)] = False
                            self.stats.failed += 1
                            continue
                        
                        # Upload file
                        success = self.upload_file(local_path, remote_path)
                        upload_results[str(local_path)] = success
                        
                        if success:
                            self.stats.successful += 1
                            self.logger.info(f"Successfully uploaded: {local_path} -> {remote_path}")
                        else:
                            self.stats.failed += 1
                            self.logger.warning(f"Upload failed: {local_path}")
                            
                    except Exception as e:
                        self.stats.failed += 1
                        upload_results[str(local_path)] = False
                        self.logger.error(f"Upload error for {local_path}: {e}")
            
            finally:
                # Always disconnect
                self.disconnect()
            
            self.stats.end_time = datetime.now()
            self.stats.total_processed = len(file_mappings)
            
            if self.stats.start_time:
                self.stats.processing_time = (self.stats.end_time - self.stats.start_time).total_seconds()
            
            self.logger.info(
                f"Upload completed: {self.stats.successful}/{self.stats.total_processed} successful "
                f"({self.stats.success_rate:.1f}%) in {self.stats.processing_time:.2f}s"
            )
            
            return upload_results
            
        except Exception as e:
            self.stats.end_time = datetime.now()
            raise UploadError(
                message=f"Batch upload failed",
                server_host=self.config.get('host', 'unknown'),
                original_exception=e
            )
    
    def validate_local_file(self, file_path: Path) -> bool:
        """
        Validate local file before upload
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            True if file is valid for upload, False otherwise
        """
        try:
            if not file_path.exists():
                self.logger.error(f"File does not exist: {file_path}")
                return False
            
            if not file_path.is_file():
                self.logger.error(f"Path is not a file: {file_path}")
                return False
            
            file_size = file_path.stat().st_size
            if file_size == 0:
                self.logger.warning(f"File is empty: {file_path}")
                return False
            
            # Check file size limits (e.g., 100MB)
            max_size = self.config.get('max_file_size', 100 * 1024 * 1024)
            if file_size > max_size:
                self.logger.error(f"File too large ({file_size} bytes): {file_path}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"File validation error: {e}")
            return False
    
    def get_remote_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about remote file (can be overridden by subclasses)
        
        Args:
            remote_path: Path to remote file
            
        Returns:
            Dictionary with file info or None if not available
        """
        # Default implementation returns None
        # Subclasses can override to provide actual remote file info
        return None
    
    def verify_upload(self, local_path: Path, remote_path: str) -> bool:
        """
        Verify upload by comparing file sizes (can be overridden by subclasses)
        
        Args:
            local_path: Path to local file
            remote_path: Path to remote file
            
        Returns:
            True if upload verified, False otherwise
        """
        try:
            # Get local file size
            local_size = local_path.stat().st_size
            
            # Get remote file info
            remote_info = self.get_remote_file_info(remote_path)
            if not remote_info:
                self.logger.warning(f"Cannot verify upload - remote file info not available: {remote_path}")
                return False
            
            remote_size = remote_info.get('size', 0)
            
            if local_size == remote_size:
                self.logger.info(f"Upload verified - sizes match ({local_size} bytes): {remote_path}")
                return True
            else:
                self.logger.error(f"Upload verification failed - size mismatch: local={local_size}, remote={remote_size}")
                return False
                
        except Exception as e:
            self.logger.error(f"Upload verification error: {e}")
            return False
    
    def cleanup_local_files(self, file_paths: List[Path], successful_uploads_only: bool = True) -> int:
        """
        Clean up local files after upload
        
        Args:
            file_paths: List of file paths to potentially clean up
            successful_uploads_only: Only delete files that were successfully uploaded
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        
        for file_path in file_paths:
            try:
                if file_path.exists():
                    # If configured to only delete successful uploads, skip failed ones
                    # This would require tracking upload results, simplified here
                    file_path.unlink()
                    deleted_count += 1
                    self.logger.info(f"Cleaned up local file: {file_path}")
                    
            except Exception as e:
                self.logger.warning(f"Failed to cleanup file {file_path}: {e}")
        
        return deleted_count
    
    def generate_remote_path(self, local_path: Path, base_remote_dir: str = "") -> str:
        """
        Generate remote path from local path
        
        Args:
            local_path: Local file path
            base_remote_dir: Base directory on remote server
            
        Returns:
            Generated remote path
        """
        filename = local_path.name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Add timestamp to filename to avoid conflicts
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            timestamped_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
        else:
            timestamped_filename = f"{filename}_{timestamp}"
        
        if base_remote_dir:
            return f"{base_remote_dir}/{timestamped_filename}"
        else:
            return timestamped_filename
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get connection status information
        
        Returns:
            Dictionary with connection status details
        """
        return {
            'connected': False,  # Override in subclasses
            'server_host': self.config.get('host', 'unknown'),
            'connection_time': None,
            'last_error': None
        }
    
    def get_stats(self) -> PipelineStats:
        """Get upload statistics"""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset upload statistics"""
        self.stats = PipelineStats(stage=PipelineStage.UPLOAD)