"""
Global pytest configuration and fixtures for Avito Pipeline Testing
Provides shared test fixtures, utilities, and configuration for all test modules
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock
from datetime import datetime
import json

# Import core classes
from core.models import ProductData, CatalogData, ValidationResult
from core.database import DatabaseManager
from core.exceptions import PipelineError


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def temp_database():
    """Create a temporary SQLite database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        db_path = Path(temp_db.name)
    
    db_manager = DatabaseManager(str(db_path))
    
    yield db_manager
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def populated_database(temp_database):
    """Database with sample test data"""
    db = temp_database
    
    # Add sample product data
    sample_products = [
        ProductData(
            model_code="S1MX",
            brand="Lynx",
            year=2024,
            malli="BoonDocker",
            paketti="DS",
            moottori="850 E-TEC",
            telamatto="3.0",
            kaynnistin="Electric",
            mittaristo="Digital",
            vari="White/Black"
        ),
        ProductData(
            model_code="S2RX", 
            brand="Ski-Doo",
            year=2023,
            malli="Summit",
            paketti="X",
            moottori="600R E-TEC",
            telamatto="2.6", 
            kaynnistin="Pull",
            mittaristo="Analog",
            vari="Red"
        )
    ]
    
    db.save_product_data(sample_products)
    
    # Add sample catalog data
    sample_catalog = [
        CatalogData(
            model_family="BoonDocker",
            brand="Lynx",
            specifications={"engine": "850 E-TEC", "track_width": "3.0"},
            features=["Electronic Reverse", "Digital Display", "Heated Grips"]
        ),
        CatalogData(
            model_family="Summit", 
            brand="Ski-Doo",
            specifications={"engine": "600R E-TEC", "track_width": "2.6"},
            features=["Mountain Riding", "T-Motion Suspension"]
        )
    ]
    
    db.save_catalog_data(sample_catalog)
    
    return db


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_product_data():
    """Sample ProductData instances for testing"""
    return [
        ProductData(
            model_code="T1ST",
            brand="Arctic Cat",
            year=2024,
            malli="Catalyst",
            paketti="9000",
            moottori="858cc 2-stroke",
            telamatto="3.0",
            kaynnistin="Electric",
            mittaristo="7\" Touchscreen",
            vari="Team Arctic Green"
        ),
        ProductData(
            model_code="T2MT",
            brand="Polaris",
            year=2023,
            malli="RMK",
            paketti="850",
            moottori="850 Patriot",
            telamatto="2.75",
            kaynnistin="Electric",
            mittaristo="Digital",
            vari="Lime Squeeze"
        )
    ]


@pytest.fixture
def sample_catalog_data():
    """Sample CatalogData instances for testing"""
    return [
        CatalogData(
            model_family="Catalyst",
            brand="Arctic Cat", 
            specifications={
                "engine_type": "2-stroke",
                "displacement": "858cc",
                "track_width": "3.0",
                "suspension": "QS3"
            },
            features=[
                "Lightweight Chassis",
                "7-inch Touchscreen Display", 
                "Electronic Power Steering",
                "Heated Seat"
            ]
        ),
        CatalogData(
            model_family="RMK",
            brand="Polaris",
            specifications={
                "engine_type": "4-stroke", 
                "displacement": "850cc",
                "track_width": "2.75",
                "suspension": "Walker Evans"
            },
            features=[
                "Patriot Engine",
                "Mountain Performance",
                "AXYS Chassis"
            ]
        )
    ]


@pytest.fixture
def sample_validation_results():
    """Sample ValidationResult instances"""
    return [
        ValidationResult(is_valid=True, confidence_score=0.95, validation_notes=["Test validation"]),
        ValidationResult(is_valid=False, confidence_score=0.65, validation_notes=["Failed validation"])
    ]


@pytest.fixture 
def sample_match_results():
    """Sample MatchResult instances"""
    return [
        {"success": True, "confidence_score": 0.98, "matched_model": "Catalyst 9000"},
        {"success": True, "confidence_score": 0.87, "matched_model": "RMK 850"}
    ]


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_pdf_extractor():
    """Mock PDF extraction functionality"""
    mock_extractor = MagicMock()
    mock_extractor.extract_with_hooks.return_value = [
        ProductData(
            model_code="M1CK",
            brand="Yamaha", 
            year=2024,
            malli="Sidewinder",
            paketti="L-TX GT"
        )
    ]
    mock_extractor.get_stats.return_value = {"successful": 1, "total_processed": 1}
    return mock_extractor


@pytest.fixture
def mock_bert_matcher():
    """Mock BERT semantic matching"""
    mock_matcher = MagicMock()
    mock_matcher.match_products.return_value = [
        {"success": True, "confidence_score": 0.95, "matched_model": "Sidewinder L-TX GT"}
    ]
    mock_matcher.get_stats.return_value = {"successful": 1, "total_processed": 1}
    return mock_matcher


@pytest.fixture
def mock_validator():
    """Mock validation functionality"""
    mock_validator = MagicMock()
    mock_validator.validate_products.return_value = [
        ValidationResult(is_valid=True, confidence_score=0.92, validation_notes=["Mock validation"])
    ]
    mock_validator.get_stats.return_value = {"successful": 1, "total_processed": 1}
    return mock_validator


@pytest.fixture
def mock_xml_generator():
    """Mock XML generation"""
    mock_generator = MagicMock()
    mock_generator.generate_xml_for_products.return_value = [
        '<?xml version="1.0" encoding="UTF-8"?><item><title>Test Snowmobile</title></item>'
    ]
    mock_generator.get_stats.return_value = {"successful": 1, "total_processed": 1}
    return mock_generator


@pytest.fixture  
def mock_ftp_uploader():
    """Mock FTP upload functionality"""
    mock_uploader = MagicMock()
    mock_uploader.connect.return_value = True
    mock_uploader.upload_xml_content.return_value = True
    mock_uploader.get_stats.return_value = {"successful": 1, "total_processed": 1}
    return mock_uploader


# ============================================================================
# FILE FIXTURES
# ============================================================================

@pytest.fixture
def temp_pdf_file():
    """Create a temporary PDF file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
        temp_path = Path(temp_pdf.name)
        # Write some dummy PDF content
        temp_pdf.write(b'%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n>>\nstartxref\n9\n%%EOF')
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_xml_file():
    """Create a temporary XML file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as temp_xml:
        temp_path = Path(temp_xml.name)
        temp_xml.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<items>\n<item><title>Test</title></item>\n</items>')
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing"""
    return {
        "products": [
            {
                "model_code": "J1SON",
                "brand": "Test Brand",
                "year": 2024,
                "specifications": {
                    "engine": "Test Engine",
                    "track": "Test Track"
                }
            }
        ]
    }


# ============================================================================
# CONFIGURATION FIXTURES  
# ============================================================================

@pytest.fixture
def test_config():
    """Test configuration with safe defaults"""
    return {
        "database_path": "test_memory.db",
        "extraction": {
            "llm_provider": "mock",
            "use_fallback": True
        },
        "matching": {
            "use_bert": False,
            "similarity_threshold": 0.8
        },
        "validation": {
            "strict_mode": False,
            "confidence_threshold": 0.7
        },
        "upload": {
            "host": "test.example.com",
            "username": "test_user",
            "dry_run": True
        }
    }


# ============================================================================
# PERFORMANCE FIXTURES
# ============================================================================

@pytest.fixture
def performance_timer():
    """Timer for performance testing"""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = datetime.now()
        
        def stop(self):
            self.end_time = datetime.now()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds()
            return None
    
    return Timer()


# ============================================================================
# CLEANUP AND SETUP HOOKS
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_logs():
    """Automatically cleanup log files after each test"""
    yield
    
    # Clean up any log files created during testing
    log_files = Path(".").glob("*.log")
    for log_file in log_files:
        if "test" in log_file.name.lower():
            try:
                log_file.unlink()
            except:
                pass


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "external: marks tests requiring external services"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location"""
    for item in items:
        # Mark tests in performance directory as slow
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.performance)
        
        # Mark tests requiring external services
        if any(keyword in str(item.fspath) for keyword in ["ftp", "claude", "external"]):
            item.add_marker(pytest.mark.external)
        
        # Mark tests by pipeline stage
        for stage in ["extraction", "matching", "validation", "generation", "upload"]:
            if stage in str(item.fspath):
                item.add_marker(getattr(pytest.mark, stage))


# ============================================================================
# TEST UTILITIES
# ============================================================================

class TestUtils:
    """Utility functions for testing"""
    
    @staticmethod
    def assert_product_data_equal(product1: ProductData, product2: ProductData):
        """Assert two ProductData instances are equal"""
        assert product1.model_code == product2.model_code
        assert product1.brand == product2.brand
        assert product1.year == product2.year
        assert product1.malli == product2.malli
    
    @staticmethod
    def create_mock_pipeline_result(success: bool = True, products_count: int = 1):
        """Create a mock pipeline result for testing"""
        return {
            "success": success,
            "products_processed": products_count,
            "products_validated": products_count if success else 0,
            "xml_generated": success
        }


@pytest.fixture
def test_utils():
    """Test utility functions"""
    return TestUtils