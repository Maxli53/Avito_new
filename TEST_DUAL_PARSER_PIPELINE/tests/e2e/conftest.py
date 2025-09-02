"""
E2E Test Configuration and Fixtures
==================================

Specialized fixtures and configuration for end-to-end testing.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock
from typing import List, Dict, Any

# Import test fixtures
from tests.fixtures.sample_data import SampleDataFactory


@pytest.fixture
def e2e_test_config():
    """Configuration settings for E2E tests"""
    return {
        "max_processing_time": 120,  # 2 minutes max for complete pipeline
        "batch_size_limit": 50,      # Maximum products in single batch
        "performance_sla": {
            "extraction": 15,        # seconds
            "matching": 20,          # seconds  
            "validation": 25,        # seconds
            "generation": 10,        # seconds
            "upload": 30,           # seconds
        },
        "success_rate_threshold": 0.95,  # 95% minimum success rate
    }


@pytest.fixture
def mock_business_environment():
    """Mock business environment for realistic E2E testing"""
    return {
        "dealer_id": "TEST_DEALER_001",
        "season": "2024_SPRING",
        "catalog_type": "FULL_CATALOG",
        "processing_priority": "NORMAL",
        "business_rules": {
            "require_validation": True,
            "min_confidence_score": 0.75,
            "enable_manual_review": True,
        }
    }


@pytest.fixture
def performance_monitor():
    """Performance monitoring fixture for E2E tests"""
    class PerformanceMonitor:
        def __init__(self):
            self.stage_times = {}
            self.total_start_time = None
            
        def start_total_timing(self):
            import time
            self.total_start_time = time.time()
            
        def record_stage_time(self, stage_name: str, duration: float):
            self.stage_times[stage_name] = duration
            
        def get_total_time(self):
            if self.total_start_time:
                import time
                return time.time() - self.total_start_time
            return 0
            
        def get_stage_summary(self):
            return {
                "stages": self.stage_times,
                "total_time": self.get_total_time(),
                "stage_count": len(self.stage_times)
            }
            
        def verify_sla_compliance(self, sla_config: Dict[str, int]):
            violations = []
            for stage, max_time in sla_config.items():
                if stage in self.stage_times:
                    actual_time = self.stage_times[stage]
                    if actual_time > max_time:
                        violations.append(f"{stage}: {actual_time:.2f}s > {max_time}s")
            return violations
    
    return PerformanceMonitor()


@pytest.fixture
def business_outcome_validator():
    """Validator for business outcomes in E2E tests"""
    class BusinessOutcomeValidator:
        def __init__(self):
            self.outcomes = {}
            
        def record_outcome(self, stage: str, success_count: int, total_count: int, details: Dict = None):
            self.outcomes[stage] = {
                "success_count": success_count,
                "total_count": total_count,
                "success_rate": success_count / total_count if total_count > 0 else 0,
                "details": details or {}
            }
            
        def validate_business_requirements(self, min_success_rate: float = 0.90):
            violations = []
            for stage, outcome in self.outcomes.items():
                if outcome["success_rate"] < min_success_rate:
                    violations.append(
                        f"{stage}: {outcome['success_rate']:.2%} < {min_success_rate:.2%}"
                    )
            return violations
            
        def get_overall_success_rate(self):
            if not self.outcomes:
                return 0
            
            total_success = sum(o["success_count"] for o in self.outcomes.values())
            total_attempts = sum(o["total_count"] for o in self.outcomes.values())
            return total_success / total_attempts if total_attempts > 0 else 0
            
        def get_business_summary(self):
            return {
                "overall_success_rate": self.get_overall_success_rate(),
                "stage_outcomes": self.outcomes,
                "total_stages": len(self.outcomes)
            }
    
    return BusinessOutcomeValidator()


@pytest.fixture
def e2e_data_factory():
    """Enhanced data factory for E2E testing scenarios"""
    class E2EDataFactory:
        @staticmethod
        def create_new_model_year_scenario():
            """Create data for new model year testing scenario"""
            return [
                {
                    "model_code": "N2025A", 
                    "brand": "Ski-Doo", 
                    "year": 2025, 
                    "malli": "New Model 2025",
                    "paketti": "Launch Edition", 
                    "moottori": "New Engine Tech",
                    "scenario": "new_model_year"
                },
                {
                    "model_code": "U2025B", 
                    "brand": "Ski-Doo", 
                    "year": 2025, 
                    "malli": "Updated Model",
                    "paketti": "Enhanced Package", 
                    "moottori": "Updated Engine",
                    "scenario": "model_update"
                }
            ]
            
        @staticmethod
        def create_competitive_analysis_scenario():
            """Create multi-brand data for competitive analysis"""
            return [
                {"brand": "Ski-Doo", "model_code": "S1BX", "competitive_strength": "high"},
                {"brand": "Polaris", "model_code": "P850", "competitive_strength": "medium"}, 
                {"brand": "Yamaha", "model_code": "Y998", "competitive_strength": "medium"},
                {"brand": "Arctic Cat", "model_code": "A700", "competitive_strength": "low"}
            ]
            
        @staticmethod
        def create_high_volume_scenario(count: int = 30):
            """Create high volume data for performance testing"""
            base_products = SampleDataFactory.create_valid_products()
            products = []
            
            for i in range(count):
                base_product = base_products[i % len(base_products)]
                products.append({
                    "model_code": f"{base_product.model_code}{i:03d}",
                    "brand": base_product.brand,
                    "year": base_product.year,
                    "malli": f"{base_product.malli} Vol{i}",
                    "paketti": base_product.paketti,
                    "moottori": base_product.moottori,
                    "volume_index": i
                })
                
            return products
            
        @staticmethod
        def create_error_prone_scenario():
            """Create data mix that triggers various error conditions"""
            return [
                {"model_code": "GOOD1", "quality": "high", "expected_outcome": "success"},
                {"model_code": "", "quality": "invalid", "expected_outcome": "failure"},
                {"model_code": "PART1", "quality": "partial", "expected_outcome": "needs_review"},
                {"model_code": "GOOD2", "quality": "high", "expected_outcome": "success"},
                {"model_code": "UNKN1", "quality": "unknown", "expected_outcome": "needs_review"}
            ]
    
    return E2EDataFactory()


@pytest.fixture
def e2e_mock_services():
    """Comprehensive mock services for E2E testing"""
    class E2EMockServices:
        def __init__(self):
            self.llm_call_count = 0
            self.bert_call_count = 0
            self.ftp_call_count = 0
            
        def create_llm_mock(self, response_data: List[Any]):
            """Create LLM service mock with specified responses"""
            def mock_extract(*args, **kwargs):
                self.llm_call_count += 1
                return response_data
            return mock_extract
            
        def create_bert_mock(self, embedding_data: List[List[float]]):
            """Create BERT service mock with specified embeddings"""
            def mock_encode(*args, **kwargs):
                self.bert_call_count += 1  
                return embedding_data
            return mock_encode
            
        def create_ftp_mock(self, success_rate: float = 1.0):
            """Create FTP service mock with specified success rate"""
            def mock_upload(*args, **kwargs):
                self.ftp_call_count += 1
                import random
                if random.random() <= success_rate:
                    return {"status": "success", "file_id": f"upload_{self.ftp_call_count}"}
                else:
                    return {"status": "failed", "error": "Mock failure"}
            return mock_upload
            
        def get_service_stats(self):
            """Get statistics on service calls"""
            return {
                "llm_calls": self.llm_call_count,
                "bert_calls": self.bert_call_count,
                "ftp_calls": self.ftp_call_count,
                "total_calls": self.llm_call_count + self.bert_call_count + self.ftp_call_count
            }
    
    return E2EMockServices()


@pytest.fixture
def e2e_database_validator():
    """Database state validator for E2E tests"""
    class E2EDatabaseValidator:
        def __init__(self, db_manager):
            self.db = db_manager
            
        def validate_pipeline_data_flow(self):
            """Validate data flows correctly through all pipeline stages"""
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            validations = {}
            
            # Check Stage 1: Extraction data
            cursor.execute("SELECT COUNT(*) FROM product_data")
            validations["extraction_count"] = cursor.fetchone()[0]
            
            # Check Stage 2: Matching data
            cursor.execute("SELECT COUNT(*) FROM catalog_data")
            validations["matching_count"] = cursor.fetchone()[0]
            
            # Check Stage 3: Validation data
            cursor.execute("SELECT COUNT(*) FROM validation_results")
            validations["validation_count"] = cursor.fetchone()[0]
            
            # Check data consistency
            cursor.execute("""
                SELECT COUNT(*) FROM product_data pd
                WHERE EXISTS (SELECT 1 FROM validation_results vr WHERE vr.product_id = pd.id)
            """)
            validations["data_consistency_count"] = cursor.fetchone()[0]
            
            conn.close()
            return validations
            
        def validate_business_data_quality(self):
            """Validate business data quality requirements"""
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            quality_checks = {}
            
            # Check for duplicate model codes
            cursor.execute("SELECT model_code, COUNT(*) FROM product_data GROUP BY model_code HAVING COUNT(*) > 1")
            duplicates = cursor.fetchall()
            quality_checks["duplicates"] = len(duplicates)
            
            # Check for invalid years
            cursor.execute("SELECT COUNT(*) FROM product_data WHERE year < 2020 OR year > 2030")
            quality_checks["invalid_years"] = cursor.fetchone()[0]
            
            # Check for empty required fields
            cursor.execute("SELECT COUNT(*) FROM product_data WHERE model_code = '' OR brand = ''")
            quality_checks["empty_required_fields"] = cursor.fetchone()[0]
            
            conn.close()
            return quality_checks
    
    def validator_factory(temp_database):
        return E2EDatabaseValidator(temp_database)
    
    return validator_factory