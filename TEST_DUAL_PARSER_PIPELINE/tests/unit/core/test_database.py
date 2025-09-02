"""
Unit tests for DatabaseManager class
Tests database operations, connection management, and data persistence
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from core import DatabaseManager, ProductData, CatalogData
from core.exceptions import DatabaseError
from tests.utils import db_helpers, DatabaseTestHelpers
from tests.fixtures.sample_data import SampleDataFactory


class TestDatabaseManagerInitialization:
    """Test DatabaseManager initialization and setup"""
    
    def test_database_manager_creation(self, temp_database):
        """Test creating DatabaseManager instance"""
        db = temp_database
        
        assert isinstance(db, DatabaseManager)
        assert db.db_path.exists()
        assert str(db.db_path).endswith('.db')
    
    def test_database_initialization_creates_tables(self, temp_database):
        """Test that database initialization creates required tables"""
        db = temp_database
        
        # Check that tables exist
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'product_data', 'catalog_data', 'validation_results', 
            'match_results', 'pipeline_runs', 'upload_history'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not created"
    
    def test_database_initialization_creates_indexes(self, temp_database):
        """Test that database initialization creates proper indexes"""
        db = temp_database
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
        
        # Should have indexes on frequently queried columns
        expected_indexes = [
            'idx_product_model_code', 'idx_product_brand_year',
            'idx_catalog_model_family', 'idx_validation_model_code'
        ]
        
        for index in expected_indexes:
            assert index in indexes, f"Index {index} not created"
    
    def test_database_connection_context_manager(self, temp_database):
        """Test database connection context manager"""
        db = temp_database
        
        # Test successful connection
        with db.get_connection() as conn:
            assert conn is not None
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_database_connection_error_handling(self):
        """Test database connection error handling"""
        # Try to connect to non-existent directory
        invalid_path = Path("/invalid/directory/database.db")
        
        with pytest.raises(DatabaseError) as exc_info:
            db = DatabaseManager(invalid_path)
            db.initialize_database()
        
        assert "Database connection error" in str(exc_info.value)


class TestProductDataOperations:
    """Test product data CRUD operations"""
    
    def test_save_single_product(self, temp_database):
        """Test saving a single product to database"""
        db = temp_database
        product = ProductData(
            model_code="SAVE",
            brand="SaveTest",
            year=2024,
            malli="Test Model"
        )
        
        result = db.save_product_data([product])
        
        assert result is True
        
        # Verify product was saved
        saved_products = db.load_product_data()
        assert len(saved_products) == 1
        assert saved_products[0].model_code == "SAVE"
        assert saved_products[0].brand == "SaveTest"
    
    def test_save_multiple_products(self, temp_database):
        """Test saving multiple products to database"""
        db = temp_database
        products = SampleDataFactory.create_valid_products()[:3]  # Take first 3
        
        result = db.save_product_data(products)
        
        assert result is True
        
        # Verify all products were saved
        saved_products = db.load_product_data()
        assert len(saved_products) == 3
        
        # Verify data integrity
        saved_codes = [p.model_code for p in saved_products]
        original_codes = [p.model_code for p in products]
        assert set(saved_codes) == set(original_codes)
    
    def test_save_products_with_clear_existing(self, temp_database):
        """Test saving products with clear_existing=True"""
        db = temp_database
        
        # Save initial products
        initial_products = SampleDataFactory.create_valid_products()[:2]
        db.save_product_data(initial_products)
        
        # Verify initial save
        assert len(db.load_product_data()) == 2
        
        # Save new products with clear_existing=True
        new_products = SampleDataFactory.create_valid_products()[2:4]
        db.save_product_data(new_products, clear_existing=True)
        
        # Should only have new products
        saved_products = db.load_product_data()
        assert len(saved_products) == 2
        
        new_codes = [p.model_code for p in new_products]
        saved_codes = [p.model_code for p in saved_products]
        assert set(saved_codes) == set(new_codes)
    
    def test_load_products_empty_database(self, temp_database):
        """Test loading products from empty database"""
        db = temp_database
        
        products = db.load_product_data()
        
        assert isinstance(products, list)
        assert len(products) == 0
    
    def test_load_products_with_filters(self, temp_database):
        """Test loading products with brand filter"""
        db = temp_database
        products = SampleDataFactory.create_valid_products()
        db.save_product_data(products)
        
        # Filter by brand
        ski_doo_products = db.load_product_data(brand="Ski-Doo")
        
        assert all(p.brand == "Ski-Doo" for p in ski_doo_products)
        assert len(ski_doo_products) > 0
    
    def test_load_products_with_year_range(self, temp_database):
        """Test loading products with year filter"""
        db = temp_database
        products = SampleDataFactory.create_valid_products()
        db.save_product_data(products)
        
        # Filter by year
        products_2024 = db.load_product_data(year=2024)
        
        assert all(p.year == 2024 for p in products_2024)
        assert len(products_2024) > 0
    
    def test_save_invalid_product_data(self, temp_database):
        """Test error handling for invalid product data"""
        db = temp_database
        
        # Missing required fields - this should be caught by ProductData validation
        with pytest.raises(ValueError):
            invalid_product = ProductData(
                model_code="",  # Empty model code
                brand="Test",
                year=2024
            )
    
    def test_database_constraint_violations(self, temp_database):
        """Test database constraint handling"""
        db = temp_database
        
        product1 = ProductData(model_code="DUPL", brand="Test1", year=2024)
        product2 = ProductData(model_code="DUPL", brand="Test2", year=2024)  # Duplicate
        
        # Save first product
        db.save_product_data([product1])
        
        # Attempt to save duplicate - should handle gracefully
        with pytest.raises(DatabaseError):
            db.save_product_data([product2])


class TestCatalogDataOperations:
    """Test catalog data CRUD operations"""
    
    def test_save_catalog_data(self, temp_database):
        """Test saving catalog data to database"""
        db = temp_database
        catalog_data = SampleDataFactory.create_catalog_data()[:2]
        
        result = db.save_catalog_data(catalog_data)
        
        assert result is True
        
        # Verify catalog data was saved
        saved_catalog = db.load_catalog_data()
        assert len(saved_catalog) == 2
        
        # Verify data integrity
        saved_families = [c.model_family for c in saved_catalog]
        original_families = [c.model_family for c in catalog_data]
        assert set(saved_families) == set(original_families)
    
    def test_load_catalog_data_empty(self, temp_database):
        """Test loading catalog data from empty database"""
        db = temp_database
        
        catalog_data = db.load_catalog_data()
        
        assert isinstance(catalog_data, list)
        assert len(catalog_data) == 0
    
    def test_load_catalog_data_by_brand(self, temp_database):
        """Test loading catalog data filtered by brand"""
        db = temp_database
        catalog_data = SampleDataFactory.create_catalog_data()
        db.save_catalog_data(catalog_data)
        
        # Filter by brand
        ski_doo_catalog = db.load_catalog_data(brand="Ski-Doo")
        
        assert all(c.brand == "Ski-Doo" for c in ski_doo_catalog)
        assert len(ski_doo_catalog) > 0
    
    def test_catalog_data_specifications_json(self, temp_database):
        """Test that specifications are properly stored as JSON"""
        db = temp_database
        
        catalog = CatalogData(
            model_family="TestFamily",
            brand="TestBrand",
            specifications={
                "engine_type": "2-stroke",
                "displacement": "850cc",
                "features": ["feature1", "feature2"]
            }
        )
        
        db.save_catalog_data([catalog])
        saved_catalog = db.load_catalog_data()
        
        assert len(saved_catalog) == 1
        saved_specs = saved_catalog[0].specifications
        
        assert saved_specs["engine_type"] == "2-stroke"
        assert saved_specs["displacement"] == "850cc"
        assert "feature1" in saved_specs["features"]


class TestValidationResultOperations:
    """Test validation result storage and retrieval"""
    
    def test_save_validation_results(self, temp_database):
        """Test saving validation results"""
        db = temp_database
        
        # First save a product
        product = ProductData(model_code="VAL1", brand="Valid", year=2024)
        db.save_product_data([product])
        
        # Save validation result
        validation_data = {
            "model_code": "VAL1",
            "success": True,
            "confidence_score": 0.95,
            "errors": [],
            "warnings": ["Minor warning"],
            "field_validations": {"model_code": True, "brand": True, "year": True}
        }
        
        result = db.save_validation_result(validation_data)
        assert result is True
        
        # Load and verify
        validation_results = db.load_validation_results(model_code="VAL1")
        assert len(validation_results) == 1
        assert validation_results[0]["success"] is True
        assert validation_results[0]["confidence_score"] == 0.95
    
    def test_load_validation_results_empty(self, temp_database):
        """Test loading validation results when none exist"""
        db = temp_database
        
        results = db.load_validation_results()
        assert isinstance(results, list)
        assert len(results) == 0


class TestMatchResultOperations:
    """Test match result storage and retrieval"""
    
    def test_save_match_results(self, temp_database):
        """Test saving match results"""
        db = temp_database
        
        # Save match result
        match_data = {
            "query_text": "Summit X Expert 165",
            "matched_model": "Summit X",
            "confidence_score": 0.94,
            "similarity_score": 0.96,
            "match_method": "bert_semantic",
            "success": True
        }
        
        result = db.save_match_result(match_data)
        assert result is True
        
        # Load and verify
        match_results = db.load_match_results(query_text="Summit X Expert 165")
        assert len(match_results) == 1
        assert match_results[0]["matched_model"] == "Summit X"
        assert match_results[0]["confidence_score"] == 0.94


class TestDatabaseTransactions:
    """Test database transaction handling"""
    
    def test_transaction_rollback_on_error(self, temp_database):
        """Test that transactions rollback properly on error"""
        db = temp_database
        
        # Save some initial data
        product1 = ProductData(model_code="TXN1", brand="Transaction", year=2024)
        db.save_product_data([product1])
        
        # Verify initial state
        assert len(db.load_product_data()) == 1
        
        # Attempt operation that will fail (simulate constraint violation)
        with pytest.raises(DatabaseError):
            with db.get_connection() as conn:
                # This should fail and rollback
                conn.execute("INSERT INTO product_data (model_code, brand, year) VALUES (?, ?, ?)",
                           ("TXN1", "Duplicate", 2024))  # Duplicate model_code
                conn.commit()
        
        # Data should remain unchanged after rollback
        products = db.load_product_data()
        assert len(products) == 1
        assert products[0].brand == "Transaction"  # Original data
    
    def test_concurrent_access_handling(self, temp_database):
        """Test handling of concurrent database access"""
        db = temp_database
        
        # Simulate concurrent writes
        product1 = ProductData(model_code="CON1", brand="Concurrent1", year=2024)
        product2 = ProductData(model_code="CON2", brand="Concurrent2", year=2024)
        
        # Both operations should succeed
        result1 = db.save_product_data([product1])
        result2 = db.save_product_data([product2])
        
        assert result1 is True
        assert result2 is True
        
        # Both products should be saved
        products = db.load_product_data()
        assert len(products) == 2


class TestDatabasePerformance:
    """Test database performance and optimization"""
    
    @pytest.mark.performance
    def test_bulk_insert_performance(self, temp_database):
        """Test performance of bulk product insertion"""
        from tests.utils import performance_timer
        
        db = temp_database
        
        # Generate large dataset
        products = []
        for i in range(100):  # Reasonable size for testing
            products.append(ProductData(
                model_code=f"P{i:03d}",
                brand=f"Brand{i % 10}",
                year=2024,
                malli=f"Model {i}"
            ))
        
        # Time the bulk insert
        with performance_timer.time_operation("bulk_insert"):
            result = db.save_product_data(products)
        
        assert result is True
        
        # Verify all products were inserted
        saved_products = db.load_product_data()
        assert len(saved_products) == 100
        
        # Assert reasonable performance (less than 1 second for 100 products)
        performance_timer.assert_performance("bulk_insert", 1.0)
    
    @pytest.mark.performance  
    def test_query_performance_with_indexes(self, temp_database):
        """Test that database queries perform well with indexes"""
        from tests.utils import performance_timer
        
        db = temp_database
        
        # Insert test data
        products = []
        for i in range(50):
            products.append(ProductData(
                model_code=f"Q{i:03d}",
                brand=f"Brand{i % 5}",  # 5 different brands
                year=2020 + (i % 5),  # 5 different years
                malli=f"Model {i}"
            ))
        
        db.save_product_data(products)
        
        # Test query performance
        with performance_timer.time_operation("filtered_query"):
            brand_products = db.load_product_data(brand="Brand1")
        
        assert len(brand_products) == 10  # Should be 10 products with Brand1
        
        # Query should be fast (less than 0.1 seconds)
        performance_timer.assert_performance("filtered_query", 0.1)


class TestDatabaseMaintenance:
    """Test database maintenance operations"""
    
    def test_database_vacuum_operation(self, temp_database):
        """Test database VACUUM operation"""
        db = temp_database
        
        # Add and remove data to create fragmentation
        products = SampleDataFactory.create_valid_products()
        db.save_product_data(products)
        
        # Clear data to create empty space
        db.save_product_data([], clear_existing=True)
        
        # Perform VACUUM (this would be a method on DatabaseManager)
        with db.get_connection() as conn:
            conn.execute("VACUUM")
        
        # Database should still be functional
        test_product = ProductData(model_code="VACM", brand="Vacuum", year=2024)
        result = db.save_product_data([test_product])
        assert result is True
    
    def test_database_integrity_check(self, temp_database):
        """Test database integrity checking"""
        db = temp_database
        
        # Perform integrity check
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
        
        assert result == "ok"


class TestDatabaseErrorHandling:
    """Test database error handling and recovery"""
    
    def test_connection_timeout_handling(self):
        """Test handling of database connection timeouts"""
        # Create database with short timeout
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = Path(temp_db.name)
        
        try:
            db = DatabaseManager(db_path, connection_timeout=0.001)  # Very short timeout
            
            # This might raise a timeout error depending on system load
            # The test verifies that timeouts are handled gracefully
            try:
                db.initialize_database()
                products = db.load_product_data()
                assert isinstance(products, list)
            except DatabaseError as e:
                assert "timeout" in str(e).lower() or "connection" in str(e).lower()
                
        finally:
            if db_path.exists():
                db_path.unlink()
    
    def test_corrupted_database_handling(self):
        """Test handling of corrupted database files"""
        # Create corrupted database file
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db.write(b"This is not a valid SQLite database")
            db_path = Path(temp_db.name)
        
        try:
            with pytest.raises(DatabaseError):
                db = DatabaseManager(db_path)
                db.initialize_database()
        finally:
            if db_path.exists():
                db_path.unlink()
    
    def test_disk_full_simulation(self, temp_database):
        """Test handling of disk full conditions"""
        db = temp_database
        
        # Mock disk full condition by patching sqlite3
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            
            # Simulate disk full error
            mock_conn.execute.side_effect = sqlite3.OperationalError("database or disk is full")
            
            with pytest.raises(DatabaseError) as exc_info:
                product = ProductData(model_code="FULL", brand="DiskFull", year=2024)
                db.save_product_data([product])
            
            assert "disk is full" in str(exc_info.value).lower()


class TestDatabaseIntegration:
    """Integration tests for database operations with other components"""
    
    def test_end_to_end_product_lifecycle(self, temp_database):
        """Test complete product data lifecycle in database"""
        db = temp_database
        
        # 1. Save product data
        product = ProductData(
            model_code="LIFE",
            brand="Lifecycle",
            year=2024,
            malli="Test Model",
            paketti="Test Package"
        )
        
        save_result = db.save_product_data([product])
        assert save_result is True
        
        # 2. Load and verify product
        loaded_products = db.load_product_data(model_code="LIFE")
        assert len(loaded_products) == 1
        assert loaded_products[0].model_code == "LIFE"
        
        # 3. Save validation result for product
        validation_data = {
            "model_code": "LIFE",
            "success": True,
            "confidence_score": 0.92,
            "errors": [],
            "warnings": []
        }
        
        val_result = db.save_validation_result(validation_data)
        assert val_result is True
        
        # 4. Save match result for product
        match_data = {
            "query_text": "Test Model Test Package",
            "matched_model": "Test Model",
            "confidence_score": 0.88,
            "success": True,
            "match_method": "exact"
        }
        
        match_result = db.save_match_result(match_data)
        assert match_result is True
        
        # 5. Verify all related data exists
        validation_results = db.load_validation_results(model_code="LIFE")
        assert len(validation_results) == 1
        
        match_results = db.load_match_results(query_text="Test Model Test Package")
        assert len(match_results) == 1
        
        # 6. Clean up (delete product and related data)
        db.save_product_data([], clear_existing=True)
        
        # Verify cleanup
        final_products = db.load_product_data()
        assert len(final_products) == 0