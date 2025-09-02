"""
Unit tests for FTP upload functionality
Tests FTPUploader class and FTP operations
"""

import pytest
import ftplib
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from io import BytesIO

from pipeline.stage5_upload import FTPUploader
from core import PipelineStats
from core.exceptions import UploadError
from tests.utils import performance_timer, file_helpers
from tests.fixtures.sample_data import SampleDataFactory


class TestFTPUploaderInitialization:
    """Test FTPUploader initialization and configuration"""
    
    def test_ftp_uploader_creation_default_config(self):
        """Test creating FTPUploader with default configuration"""
        uploader = FTPUploader()
        
        assert isinstance(uploader, FTPUploader)
        assert uploader.config is not None
        assert uploader.host == '176.126.165.67'  # Default Avito host
        assert uploader.username == 'user133859'  # Default username
        assert uploader.port == 21
        assert uploader.timeout == 30
        assert uploader.stats.stage == 'upload'
    
    def test_ftp_uploader_custom_config(self):
        """Test FTPUploader with custom configuration"""
        custom_config = {
            'host': 'custom.ftp.server.com',
            'username': 'custom_user',
            'password': 'custom_password',
            'remote_path': '/custom/path/',
            'port': 2121,
            'timeout': 60,
            'max_retries': 5,
            'retry_delay': 10
        }
        
        uploader = FTPUploader(config=custom_config)
        
        assert uploader.host == 'custom.ftp.server.com'
        assert uploader.username == 'custom_user'
        assert uploader.password == 'custom_password'
        assert uploader.remote_base_path == '/custom/path/'
        assert uploader.port == 2121
        assert uploader.timeout == 60
        assert uploader.max_retries == 5
    
    def test_ftp_uploader_environment_password(self):
        """Test FTP uploader reads password from environment"""
        with patch.dict('os.environ', {'AVITO_FTP_PASSWORD': 'env_password'}):
            uploader = FTPUploader()
            assert uploader.password == 'env_password'
    
    def test_ftp_uploader_no_password_error(self):
        """Test error when no password is configured"""
        with patch.dict('os.environ', {}, clear=True):
            uploader = FTPUploader(config={'password': ''})
            
            with pytest.raises(UploadError) as exc_info:
                uploader.connect()
            
            assert "password not configured" in str(exc_info.value).lower()
            assert "AVITO_FTP_PASSWORD" in str(exc_info.value)


class TestFTPConnection:
    """Test FTP connection management"""
    
    def test_ftp_connection_success(self):
        """Test successful FTP connection"""
        uploader = FTPUploader(config={'password': 'test_password'})
        
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            mock_ftp_class.return_value = mock_ftp
            
            result = uploader.connect()
            
            assert result is True
            assert uploader.connected is True
            assert uploader.connection_time is not None
            
            # Verify FTP connection sequence
            mock_ftp.connect.assert_called_once_with(uploader.host, uploader.port, uploader.timeout)
            mock_ftp.login.assert_called_once_with(uploader.username, uploader.password)
    
    def test_ftp_connection_already_connected(self):
        """Test connection when already connected"""
        uploader = FTPUploader()
        uploader.connected = True
        uploader.ftp_connection = MagicMock()
        
        result = uploader.connect()
        
        assert result is True  # Should return True without reconnecting
    
    def test_ftp_connection_failure_with_retry(self):
        """Test FTP connection failure and retry logic"""
        config = {'password': 'test_password', 'max_retries': 3}
        uploader = FTPUploader(config=config)
        
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            mock_ftp_class.return_value = mock_ftp
            mock_ftp.connect.side_effect = [
                ftplib.error_temp("Temporary failure"),  # First attempt fails
                ftplib.error_temp("Still failing"),      # Second attempt fails  
                None                                      # Third attempt succeeds
            ]
            
            with patch('time.sleep') as mock_sleep:
                result = uploader.connect()
            
            assert result is True
            assert uploader.connected is True
            assert mock_ftp.connect.call_count == 3
            assert mock_sleep.call_count == 2  # Sleep between retries
    
    def test_ftp_connection_permanent_failure(self):
        """Test FTP connection permanent failure after retries"""
        config = {'password': 'test_password', 'max_retries': 2}
        uploader = FTPUploader(config=config)
        
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            mock_ftp_class.return_value = mock_ftp
            mock_ftp.connect.side_effect = ftplib.error_perm("Permanent failure")
            
            with pytest.raises(UploadError) as exc_info:
                uploader.connect()
            
            assert "failed to connect" in str(exc_info.value).lower()
            assert uploader.connected is False
            assert mock_ftp.connect.call_count == 2  # Retried max_retries times
    
    def test_ftp_connection_authentication_failure(self):
        """Test FTP authentication failure"""
        config = {'password': 'wrong_password'}
        uploader = FTPUploader(config=config)
        
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            mock_ftp_class.return_value = mock_ftp
            mock_ftp.login.side_effect = ftplib.error_perm("530 Login incorrect")
            
            with pytest.raises(UploadError) as exc_info:
                uploader.connect()
            
            assert "login" in str(exc_info.value).lower() or "authentication" in str(exc_info.value).lower()
    
    def test_ftp_disconnect(self):
        """Test FTP disconnection"""
        uploader = FTPUploader()
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        uploader.connected = True
        
        uploader.disconnect()
        
        assert uploader.connected is False
        assert uploader.ftp_connection is None
        assert uploader.connection_time is None
        mock_ftp.quit.assert_called_once()
    
    def test_ftp_disconnect_with_error(self):
        """Test FTP disconnection when quit fails"""
        uploader = FTPUploader()
        mock_ftp = MagicMock()
        mock_ftp.quit.side_effect = Exception("Quit failed")
        uploader.ftp_connection = mock_ftp
        uploader.connected = True
        
        # Should not raise exception, should try close as fallback
        uploader.disconnect()
        
        assert uploader.connected is False
        assert uploader.ftp_connection is None
        mock_ftp.quit.assert_called_once()
        mock_ftp.close.assert_called_once()


class TestFileUpload:
    """Test file upload functionality"""
    
    def test_upload_file_success(self, temp_xml_file):
        """Test successful file upload"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Create test file content
        test_content = b"Test XML content for upload"
        temp_xml_file.write_bytes(test_content)
        
        with patch.object(uploader, 'validate_local_file', return_value=True):
            with patch.object(uploader, '_verify_ftp_upload', return_value=True):
                result = uploader.upload_file(temp_xml_file, "remote_test.xml")
        
        assert result is True
        mock_ftp.storbinary.assert_called_once()
        
        # Verify storbinary was called with correct parameters
        call_args = mock_ftp.storbinary.call_args
        assert call_args[0][0] == 'STOR remote_test.xml'
    
    def test_upload_file_not_connected(self, temp_xml_file):
        """Test file upload when not connected"""
        uploader = FTPUploader()
        uploader.connected = False
        
        with pytest.raises(UploadError) as exc_info:
            uploader.upload_file(temp_xml_file, "test.xml")
        
        assert "not established" in str(exc_info.value).lower()
    
    def test_upload_file_validation_failure(self, temp_xml_file):
        """Test file upload with file validation failure"""
        uploader = FTPUploader()
        uploader.connected = True
        uploader.ftp_connection = MagicMock()
        
        with patch.object(uploader, 'validate_local_file', return_value=False):
            result = uploader.upload_file(temp_xml_file, "test.xml")
        
        assert result is False
    
    def test_upload_file_ftp_error(self, temp_xml_file):
        """Test file upload with FTP error"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        mock_ftp.storbinary.side_effect = ftplib.error_perm("Permission denied")
        uploader.ftp_connection = mock_ftp
        
        temp_xml_file.write_text("test content")
        
        with patch.object(uploader, 'validate_local_file', return_value=True):
            with pytest.raises(UploadError) as exc_info:
                uploader.upload_file(temp_xml_file, "test.xml")
        
        assert "ftp upload failed" in str(exc_info.value).lower()
        assert isinstance(exc_info.value.original_exception, ftplib.error_perm)
    
    def test_upload_xml_content_success(self):
        """Test successful XML content upload"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<items>
    <item><title>Test Product</title></item>
</items>"""
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            result = uploader.upload_xml_content(xml_content, "test_upload.xml")
        
        assert result is True
        mock_ftp.storbinary.assert_called_once()
        
        # Verify storbinary was called with BytesIO buffer
        call_args = mock_ftp.storbinary.call_args
        assert call_args[0][0] == 'STOR test_upload.xml'
        assert isinstance(call_args[0][1], BytesIO)
    
    def test_upload_xml_content_not_connected(self):
        """Test XML content upload when not connected (auto-connect)"""
        uploader = FTPUploader()
        uploader.connected = False
        
        with patch.object(uploader, 'connect', return_value=True):
            with patch.object(uploader, '_verify_ftp_upload', return_value=True):
                mock_ftp = MagicMock()
                uploader.ftp_connection = mock_ftp
                uploader.connected = True
                
                result = uploader.upload_xml_content("test", "test.xml")
        
        assert result is True
    
    def test_upload_xml_content_encoding(self):
        """Test XML content upload with proper UTF-8 encoding"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # XML with special characters
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<item><title>Test with special chars: åäö, éè, ñ</title></item>"""
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            result = uploader.upload_xml_content(xml_content, "utf8_test.xml")
        
        assert result is True
        
        # Verify correct encoding was used
        call_args = mock_ftp.storbinary.call_args
        buffer = call_args[0][1]
        buffer.seek(0)
        uploaded_bytes = buffer.read()
        decoded_content = uploaded_bytes.decode('utf-8')
        assert "åäö" in decoded_content
        assert "éè" in decoded_content


class TestUploadVerification:
    """Test upload verification functionality"""
    
    def test_verify_ftp_upload_success(self):
        """Test successful upload verification"""
        uploader = FTPUploader()
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Mock file listing and size check
        mock_ftp.nlst.return_value = ['test_file.xml', 'other_file.xml']
        mock_ftp.size.return_value = 1024  # Expected size
        
        result = uploader._verify_ftp_upload('test_file.xml', 1024)
        
        assert result is True
        mock_ftp.nlst.assert_called_once()
        mock_ftp.size.assert_called_once_with('test_file.xml')
    
    def test_verify_ftp_upload_file_not_found(self):
        """Test upload verification when file not found"""
        uploader = FTPUploader()
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        mock_ftp.nlst.return_value = ['other_file.xml']  # Missing our file
        
        result = uploader._verify_ftp_upload('missing_file.xml', 1024)
        
        assert result is False
    
    def test_verify_ftp_upload_size_mismatch(self):
        """Test upload verification with size mismatch"""
        uploader = FTPUploader()
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        mock_ftp.nlst.return_value = ['test_file.xml']
        mock_ftp.size.return_value = 512  # Wrong size
        
        result = uploader._verify_ftp_upload('test_file.xml', 1024)  # Expected 1024
        
        assert result is False
    
    def test_verify_ftp_upload_size_not_supported(self):
        """Test upload verification when size command not supported"""
        uploader = FTPUploader()
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        mock_ftp.nlst.return_value = ['test_file.xml']
        mock_ftp.size.side_effect = ftplib.error_perm("SIZE not supported")
        
        result = uploader._verify_ftp_upload('test_file.xml', 1024)
        
        # Should still return True if file exists but size check fails
        assert result is True
    
    def test_verify_ftp_upload_listing_error(self):
        """Test upload verification with listing error"""
        uploader = FTPUploader()
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        mock_ftp.nlst.side_effect = ftplib.error_perm("Listing failed")
        
        result = uploader._verify_ftp_upload('test_file.xml', 1024)
        
        assert result is False


class TestRemoteFileInfo:
    """Test remote file information retrieval"""
    
    def test_get_remote_file_info_success(self):
        """Test successful remote file info retrieval"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        mock_ftp.nlst.return_value = ['test_file.xml', 'other_file.xml']
        mock_ftp.size.return_value = 2048
        mock_ftp.sendcmd.return_value = "213 20241201120000"  # MDTM response
        
        info = uploader.get_remote_file_info('test_file.xml')
        
        assert info is not None
        assert info['exists'] is True
        assert info['name'] == 'test_file.xml'
        assert info['size'] == 2048
        assert info['modified'] == "213 20241201120000"
    
    def test_get_remote_file_info_not_found(self):
        """Test remote file info when file not found"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        mock_ftp.nlst.return_value = ['other_file.xml']  # File not in listing
        
        info = uploader.get_remote_file_info('missing_file.xml')
        
        assert info is None
    
    def test_get_remote_file_info_not_connected(self):
        """Test remote file info when not connected"""
        uploader = FTPUploader()
        uploader.connected = False
        
        info = uploader.get_remote_file_info('test_file.xml')
        
        assert info is None
    
    def test_list_remote_files_success(self):
        """Test listing remote files"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        mock_ftp.nlst.return_value = ['file1.xml', 'file2.xml', 'file3.xml']
        
        files = uploader.list_remote_files()
        
        assert files == ['file1.xml', 'file2.xml', 'file3.xml']
        mock_ftp.nlst.assert_called_once_with("/")
    
    def test_list_remote_files_specific_path(self):
        """Test listing files in specific remote directory"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        mock_ftp.nlst.return_value = ['subdir_file1.xml']
        
        files = uploader.list_remote_files("/subdir")
        
        assert files == ['subdir_file1.xml']
        mock_ftp.nlst.assert_called_once_with("/subdir")


class TestMultipleFileUpload:
    """Test multiple file upload functionality"""
    
    def test_upload_multiple_files_success(self, temp_xml_file):
        """Test successful upload of multiple files"""
        uploader = FTPUploader()
        
        # Create additional temp files
        temp_file2 = temp_xml_file.parent / "test2.xml"
        temp_file3 = temp_xml_file.parent / "test3.xml"
        
        temp_xml_file.write_text("Content 1")
        temp_file2.write_text("Content 2")
        temp_file3.write_text("Content 3")
        
        file_mappings = [
            (temp_xml_file, "remote1.xml"),
            (temp_file2, "remote2.xml"),
            (temp_file3, "remote3.xml")
        ]
        
        with patch.object(uploader, 'connect', return_value=True):
            with patch.object(uploader, 'upload_file', return_value=True) as mock_upload:
                with patch.object(uploader, 'disconnect'):
                    results = uploader.upload_files(file_mappings)
        
        assert len(results) == 3
        assert all(results.values())  # All uploads successful
        assert mock_upload.call_count == 3
        
        # Verify statistics
        stats = uploader.get_stats()
        assert stats.successful == 3
        assert stats.total_processed == 3
    
    def test_upload_multiple_files_partial_failure(self, temp_xml_file):
        """Test multiple file upload with some failures"""
        uploader = FTPUploader()
        
        temp_file2 = temp_xml_file.parent / "test2.xml"
        nonexistent_file = temp_xml_file.parent / "nonexistent.xml"
        
        temp_xml_file.write_text("Content 1")
        temp_file2.write_text("Content 2")
        # nonexistent_file is not created
        
        file_mappings = [
            (temp_xml_file, "remote1.xml"),
            (temp_file2, "remote2.xml"), 
            (nonexistent_file, "remote3.xml")  # This will fail
        ]
        
        with patch.object(uploader, 'connect', return_value=True):
            with patch.object(uploader, 'upload_file') as mock_upload:
                # First two succeed, third fails due to missing file
                mock_upload.side_effect = [True, True, False]
                
                with patch.object(uploader, 'disconnect'):
                    results = uploader.upload_files(file_mappings)
        
        assert len(results) == 3
        assert results[str(temp_xml_file)] is True
        assert results[str(temp_file2)] is True
        assert results[str(nonexistent_file)] is False
        
        # Verify statistics
        stats = uploader.get_stats()
        assert stats.successful == 2
        assert stats.failed == 1
        assert stats.total_processed == 3


class TestFTPUploaderPerformance:
    """Test FTP uploader performance characteristics"""
    
    @pytest.mark.performance
    def test_single_file_upload_speed(self, temp_xml_file):
        """Test speed of single file upload"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Create reasonably sized test file
        test_content = "XML content line\n" * 100  # ~1.6KB
        temp_xml_file.write_text(test_content)
        
        with patch.object(uploader, 'validate_local_file', return_value=True):
            with patch.object(uploader, '_verify_ftp_upload', return_value=True):
                with performance_timer.time_operation("single_file_upload"):
                    result = uploader.upload_file(temp_xml_file, "performance_test.xml")
        
        assert result is True
        
        # Should complete quickly (less than 0.5 seconds for mocked upload)
        performance_timer.assert_performance("single_file_upload", 0.5)
    
    @pytest.mark.performance
    def test_xml_content_upload_speed(self):
        """Test speed of XML content upload"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Create reasonably sized XML content
        xml_items = []
        for i in range(50):
            xml_items.append(f"<item><title>Product {i}</title><description>Description for product {i}</description></item>")
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<items>
{''.join(xml_items)}
</items>"""
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            with performance_timer.time_operation("xml_content_upload"):
                result = uploader.upload_xml_content(xml_content, "batch_products.xml")
        
        assert result is True
        
        # Should complete quickly (less than 0.3 seconds for mocked upload)
        performance_timer.assert_performance("xml_content_upload", 0.3)
    
    def test_connection_pooling_simulation(self):
        """Test behavior with multiple uploads using same connection"""
        uploader = FTPUploader()
        
        with patch.object(uploader, 'connect') as mock_connect:
            with patch.object(uploader, '_verify_ftp_upload', return_value=True):
                mock_ftp = MagicMock()
                uploader.ftp_connection = mock_ftp
                uploader.connected = True
                mock_connect.return_value = True
                
                # Multiple XML uploads
                for i in range(5):
                    result = uploader.upload_xml_content(f"<item>Content {i}</item>", f"file_{i}.xml")
                    assert result is True
                
                # Should only connect once
                assert mock_connect.call_count <= 1


class TestFTPUploaderErrorHandling:
    """Test comprehensive error handling"""
    
    def test_connection_timeout_handling(self):
        """Test handling of connection timeouts"""
        config = {'password': 'test_pass', 'timeout': 1}  # Very short timeout
        uploader = FTPUploader(config=config)
        
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = MagicMock()
            mock_ftp_class.return_value = mock_ftp
            mock_ftp.connect.side_effect = OSError("Connection timeout")
            
            with pytest.raises(UploadError) as exc_info:
                uploader.connect()
            
            assert "connect" in str(exc_info.value).lower()
    
    def test_network_error_during_upload(self, temp_xml_file):
        """Test handling of network errors during upload"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        temp_xml_file.write_text("test content")
        
        # Simulate network error during upload
        mock_ftp.storbinary.side_effect = OSError("Network unreachable")
        
        with patch.object(uploader, 'validate_local_file', return_value=True):
            with pytest.raises(UploadError) as exc_info:
                uploader.upload_file(temp_xml_file, "network_test.xml")
        
        assert "network" in str(exc_info.value).lower() or "unreachable" in str(exc_info.value).lower()
    
    def test_disk_full_error_handling(self):
        """Test handling of remote disk full errors"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Simulate disk full error
        mock_ftp.storbinary.side_effect = ftplib.error_temp("552 Disk full")
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            with pytest.raises(UploadError) as exc_info:
                uploader.upload_xml_content("test content", "disk_full_test.xml")
        
        assert "disk" in str(exc_info.value).lower() or "552" in str(exc_info.value)
    
    def test_permission_error_handling(self, temp_xml_file):
        """Test handling of file permission errors"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Simulate permission error
        mock_ftp.storbinary.side_effect = ftplib.error_perm("550 Permission denied")
        
        temp_xml_file.write_text("test content")
        
        with patch.object(uploader, 'validate_local_file', return_value=True):
            with pytest.raises(UploadError) as exc_info:
                uploader.upload_file(temp_xml_file, "permission_test.xml")
        
        assert "permission" in str(exc_info.value).lower()
    
    def test_invalid_remote_path_handling(self):
        """Test handling of invalid remote paths"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Simulate invalid path error
        mock_ftp.storbinary.side_effect = ftplib.error_perm("550 No such file or directory")
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            with pytest.raises(UploadError) as exc_info:
                uploader.upload_xml_content("test", "/invalid/path/file.xml")
        
        assert "550" in str(exc_info.value) or "directory" in str(exc_info.value).lower()


class TestFTPUploaderIntegration:
    """Integration tests for FTP uploader with other components"""
    
    def test_integration_with_generated_xml(self):
        """Test FTP uploader with XML from generation stage"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # XML as it would come from generation stage
        generated_xml = """<?xml version="1.0" encoding="UTF-8"?>
<items>
    <item>
        <title>Ski-Doo Summit X Expert 165 2024</title>
        <model_code>SKDO</model_code>
        <brand>Ski-Doo</brand>
        <year>2024</year>
        <price>45000</price>
        <description>Model: Summit X Expert 165
Engine: 850 E-TEC Turbo R
Track: 3.0
Starter: Electric</description>
    </item>
</items>"""
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            result = uploader.upload_xml_content(generated_xml, "avito_snowmobiles_20241201.xml")
        
        assert result is True
        mock_ftp.storbinary.assert_called_once()
    
    def test_integration_with_pipeline_statistics(self):
        """Test FTP uploader statistics integration"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Simulate multiple uploads for statistics
        uploads = [
            ("content1", "file1.xml"),
            ("content2", "file2.xml"),
            ("content3", "file3.xml")
        ]
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            for content, filename in uploads:
                result = uploader.upload_xml_content(content, filename)
                assert result is True
        
        # Verify statistics tracking
        stats = uploader.get_stats()
        assert stats.successful == 3
        assert stats.total_processed == 3
        assert stats.success_rate == 100.0
        assert stats.processing_time is not None
    
    def test_integration_with_monitoring_system(self):
        """Test integration with upload monitoring"""
        uploader = FTPUploader()
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Mock monitoring system
        with patch('pipeline.stage5_upload.ProcessingMonitor') as mock_monitor_class:
            mock_monitor = MagicMock()
            mock_monitor_class.return_value = mock_monitor
            
            with patch.object(uploader, '_verify_ftp_upload', return_value=True):
                result = uploader.upload_xml_content("test content", "monitored_upload.xml")
            
            assert result is True
            
            # Could verify monitoring calls if implemented
            # mock_monitor.record_upload.assert_called_once()
    
    def test_integration_with_retry_logic(self):
        """Test integration with comprehensive retry logic"""
        config = {
            'password': 'test_pass',
            'max_retries': 3,
            'retry_delay': 0.1  # Short delay for testing
        }
        uploader = FTPUploader(config=config)
        uploader.connected = True
        mock_ftp = MagicMock()
        uploader.ftp_connection = mock_ftp
        
        # Simulate transient failures followed by success
        mock_ftp.storbinary.side_effect = [
            ftplib.error_temp("Temporary failure"),  # First attempt
            ftplib.error_temp("Still failing"),     # Second attempt
            None                                     # Third attempt succeeds
        ]
        
        with patch.object(uploader, '_verify_ftp_upload', return_value=True):
            with patch('time.sleep') as mock_sleep:
                result = uploader.upload_xml_content("retry test", "retry_test.xml")
        
        assert result is True
        assert mock_ftp.storbinary.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries


class TestConnectionStatusAndInfo:
    """Test connection status and information methods"""
    
    def test_get_connection_status_connected(self):
        """Test connection status when connected"""
        uploader = FTPUploader()
        uploader.connected = True
        uploader.connection_time = datetime.now()
        
        status = uploader.get_connection_status()
        
        assert status['connected'] is True
        assert status['server_host'] == uploader.host
        assert status['username'] == uploader.username
        assert status['port'] == uploader.port
        assert status['connection_time'] is not None
        assert status['last_error'] is None
    
    def test_get_connection_status_disconnected_with_error(self):
        """Test connection status when disconnected with error"""
        uploader = FTPUploader()
        uploader.connected = False
        uploader.last_error = "Connection failed"
        
        status = uploader.get_connection_status()
        
        assert status['connected'] is False
        assert status['last_error'] == "Connection failed"
        assert status['connection_time'] is None
    
    def test_connection_status_serialization(self):
        """Test that connection status can be serialized"""
        uploader = FTPUploader()
        uploader.connected = True
        uploader.connection_time = datetime.now()
        
        status = uploader.get_connection_status()
        
        # Should be JSON serializable
        import json
        try:
            json.dumps(status, default=str)  # Use default=str for datetime
        except (TypeError, ValueError):
            pytest.fail("Connection status is not JSON serializable")