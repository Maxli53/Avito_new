"""
Test utility functions and helpers
Provides common testing functionality across all test modules
"""

import time
import logging
import functools
from pathlib import Path
from typing import Any, Dict, List, Callable, Optional
from contextlib import contextmanager
from unittest.mock import Mock, MagicMock, patch
import pytest

from core import ProductData, PipelineStats, ValidationResult


class TestLogger:
    """Test-specific logging utilities"""
    
    @staticmethod
    def setup_test_logging(level: int = logging.DEBUG):
        """Setup logging for test environment"""
        logging.basicConfig(
            level=level,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('test_pipeline.log')
            ]
        )
    
    @staticmethod
    @contextmanager
    def capture_logs(logger_name: str, level: int = logging.INFO):
        """Capture log messages for testing"""
        import io
        
        logger = logging.getLogger(logger_name)
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(level)
        
        logger.addHandler(handler)
        try:
            yield log_capture
        finally:
            logger.removeHandler(handler)


class PerformanceTimer:
    """Performance measurement utilities for testing"""
    
    def __init__(self):
        self.measurements: Dict[str, List[float]] = {}
    
    @contextmanager
    def time_operation(self, operation_name: str):
        """Time an operation and record the duration"""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            if operation_name not in self.measurements:
                self.measurements[operation_name] = []
            self.measurements[operation_name].append(duration)
    
    def get_average_time(self, operation_name: str) -> Optional[float]:
        """Get average execution time for an operation"""
        if operation_name in self.measurements:
            times = self.measurements[operation_name]
            return sum(times) / len(times)
        return None
    
    def get_stats(self, operation_name: str) -> Dict[str, float]:
        """Get detailed statistics for an operation"""
        if operation_name not in self.measurements:
            return {}
        
        times = self.measurements[operation_name]
        return {
            'count': len(times),
            'total': sum(times),
            'average': sum(times) / len(times),
            'min': min(times),
            'max': max(times)
        }
    
    def assert_performance(self, operation_name: str, max_duration: float):
        """Assert that operation performance meets requirements"""
        avg_time = self.get_average_time(operation_name)
        if avg_time is None:
            pytest.fail(f"No measurements found for operation: {operation_name}")
        
        if avg_time > max_duration:
            pytest.fail(
                f"Performance test failed for {operation_name}: "
                f"average time {avg_time:.3f}s exceeds limit {max_duration:.3f}s"
            )


class DataValidator:
    """Utilities for validating test data and results"""
    
    @staticmethod
    def assert_valid_product_data(product: ProductData):
        """Assert that ProductData instance is valid"""
        assert product.model_code, "Model code is required"
        assert len(product.model_code) == 4, f"Model code must be 4 characters, got {len(product.model_code)}"
        assert product.brand, "Brand is required"
        assert product.year, "Year is required"
        assert 2020 <= product.year <= 2030, f"Year {product.year} is out of valid range"
    
    @staticmethod
    def assert_valid_pipeline_stats(stats: PipelineStats):
        """Assert that PipelineStats are valid and consistent"""
        assert stats.total_processed >= 0, "Total processed must be non-negative"
        assert stats.successful >= 0, "Successful count must be non-negative"
        assert stats.failed >= 0, "Failed count must be non-negative"
        assert stats.successful + stats.failed == stats.total_processed, "Stats counts don't add up"
        assert 0 <= stats.success_rate <= 100, "Success rate must be between 0 and 100"
    
    @staticmethod
    def assert_valid_validation_result(result: ValidationResult):
        """Assert that ValidationResult is properly structured"""
        assert isinstance(result.success, bool), "Success must be boolean"
        assert 0 <= result.confidence_score <= 1, "Confidence score must be between 0 and 1"
        
        if not result.success:
            assert result.errors, "Failed validation must have errors"
        
        if result.errors:
            assert all(isinstance(error, str) for error in result.errors), "All errors must be strings"


class MockFactory:
    """Factory for creating consistent mock objects"""
    
    @staticmethod
    def create_mock_database(products: List[ProductData] = None):
        """Create a mock database with optional test data"""
        mock_db = MagicMock()
        
        if products:
            mock_db.load_product_data.return_value = products
            mock_db.save_product_data.return_value = True
        else:
            mock_db.load_product_data.return_value = []
            mock_db.save_product_data.return_value = True
        
        mock_db.initialize_database.return_value = True
        return mock_db
    
    @staticmethod
    def create_mock_extractor(products: List[ProductData] = None, success_rate: float = 1.0):
        """Create a mock PDF extractor"""
        mock_extractor = MagicMock()
        
        if products:
            # Simulate some failures based on success rate
            successful_count = int(len(products) * success_rate)
            mock_extractor.extract_with_hooks.return_value = products[:successful_count]
        else:
            mock_extractor.extract_with_hooks.return_value = []
        
        mock_extractor.get_stats.return_value = PipelineStats(
            stage="extraction",
            successful=len(products) if products else 0,
            total_processed=len(products) if products else 0
        )
        
        return mock_extractor
    
    @staticmethod
    def create_mock_config(overrides: Dict[str, Any] = None):
        """Create a mock configuration object"""
        base_config = {
            'database_path': 'test.db',
            'extraction': {'llm_provider': 'mock'},
            'matching': {'use_bert': False},
            'validation': {'strict_mode': False},
            'generation': {'template_path': 'test'},
            'upload': {'host': 'test.example.com', 'dry_run': True}
        }
        
        if overrides:
            base_config.update(overrides)
        
        mock_config = MagicMock()
        for key, value in base_config.items():
            setattr(mock_config, key, value)
        
        return mock_config


class FileTestHelpers:
    """Utilities for file-based testing"""
    
    @staticmethod
    def create_temp_pdf(content: bytes = None) -> Path:
        """Create a temporary PDF file for testing"""
        import tempfile
        
        if not content:
            # Minimal valid PDF content
            content = b'%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n>>\nstartxref\n9\n%%EOF'
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(content)
            return Path(temp_file.name)
    
    @staticmethod  
    def create_temp_xml(content: str = None) -> Path:
        """Create a temporary XML file for testing"""
        import tempfile
        
        if not content:
            content = '<?xml version="1.0" encoding="UTF-8"?>\n<items>\n<item><title>Test</title></item>\n</items>'
        
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(content)
            return Path(temp_file.name)
    
    @staticmethod
    def cleanup_temp_files(files: List[Path]):
        """Clean up temporary files after testing"""
        for file_path in files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logging.warning(f"Failed to cleanup temp file {file_path}: {e}")


class TestDecorators:
    """Custom test decorators for common scenarios"""
    
    @staticmethod
    def requires_external_service(service_name: str):
        """Skip test if external service is not available"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # This could check if service is available
                # For now, just mark as external
                pytest.mark.external(func)(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def performance_test(max_duration: float):
        """Decorator to mark and validate performance tests"""
        def decorator(func):
            @functools.wraps(func)
            @pytest.mark.performance
            def wrapper(*args, **kwargs):
                timer = PerformanceTimer()
                with timer.time_operation(func.__name__):
                    result = func(*args, **kwargs)
                
                timer.assert_performance(func.__name__, max_duration)
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def retry_on_failure(max_retries: int = 3):
        """Retry test on failure (useful for flaky external services)"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries - 1:
                            time.sleep(1)  # Brief delay between retries
                
                raise last_exception
            return wrapper
        return decorator


class DatabaseTestHelpers:
    """Database-specific test utilities"""
    
    @staticmethod
    def assert_database_state(db_manager, expected_product_count: int = None, 
                            expected_catalog_count: int = None):
        """Assert database is in expected state"""
        if expected_product_count is not None:
            products = db_manager.load_product_data()
            assert len(products) == expected_product_count, \
                f"Expected {expected_product_count} products, got {len(products)}"
        
        if expected_catalog_count is not None:
            catalog = db_manager.load_catalog_data()
            assert len(catalog) == expected_catalog_count, \
                f"Expected {expected_catalog_count} catalog entries, got {len(catalog)}"
    
    @staticmethod
    def clear_database(db_manager):
        """Clear all data from test database"""
        with db_manager.get_connection() as conn:
            conn.execute("DELETE FROM product_data")
            conn.execute("DELETE FROM catalog_data") 
            conn.execute("DELETE FROM validation_results")
            conn.execute("DELETE FROM match_results")
            conn.commit()


# Global instances for easy access
performance_timer = PerformanceTimer()
data_validator = DataValidator()
mock_factory = MockFactory()
file_helpers = FileTestHelpers()
db_helpers = DatabaseTestHelpers()
test_logger = TestLogger()