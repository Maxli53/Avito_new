"""
Integration tests for database operations across pipeline stages
Tests real database operations, transactions, and data persistence
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import sqlite3

from core import DatabaseManager, ProductData, CatalogData, ValidationResult, MatchResult
from core.exceptions import DatabaseError
from tests.fixtures.sample_data import SampleDataFactory
from tests.utils import db_helpers


class TestDatabaseLifecycleIntegration:
    """Test complete database lifecycle across pipeline execution"""
    
    def test_full_product_lifecycle_database_integration(self, temp_database):
        """Test complete product data lifecycle through database"""
        db = temp_database
        
        # Stage 1: Save extracted product data
        extracted_products = SampleDataFactory.create_valid_products()[:3]
        
        save_result = db.save_product_data(extracted_products, clear_existing=True)
        assert save_result is True
        
        # Verify extraction stage data persisted
        loaded_products = db.load_product_data()
        assert len(loaded_products) == 3
        
        # Stage 2: Save matching results for each product
        match_results = []
        for i, product in enumerate(loaded_products):
            match_data = {
                "query_text": f"{product.brand} {product.malli}",
                "matched_model": product.malli,
                "confidence_score": 0.95 - (i * 0.05),  # Varying confidence
                "similarity_score": 0.93 - (i * 0.03),
                "match_method": "bert_semantic",
                "success": True,
                "model_code": product.model_code
            }
            match_results.append(match_data)
            db.save_match_result(match_data)
        
        # Verify matching stage data persisted
        for match_data in match_results:
            loaded_matches = db.load_match_results(query_text=match_data["query_text"])
            assert len(loaded_matches) == 1
            assert loaded_matches[0]["confidence_score"] == match_data["confidence_score"]
        
        # Stage 3: Save validation results
        validation_results = []
        for i, product in enumerate(loaded_products):
            validation_data = {
                "model_code": product.model_code,
                "success": True,
                "confidence_score": 0.92 - (i * 0.02),
                "errors": [],
                "warnings": ["Minor validation note"] if i == 1 else [],
                "field_validations": {
                    "model_code": True,
                    "brand": True, 
                    "year": True,
                    "malli": True
                },
                "validation_layers": [
                    "field_validation",
                    "brp_database", 
                    "specification_validation",
                    "cross_field_validation"
                ]
            }
            validation_results.append(validation_data)
            db.save_validation_result(validation_data)
        
        # Verify validation stage data persisted
        for validation_data in validation_results:
            loaded_validations = db.load_validation_results(model_code=validation_data["model_code"])
            assert len(loaded_validations) == 1
            assert loaded_validations[0]["success"] is True
        
        # Final verification: Query all related data for a product
        test_product = loaded_products[0]
        
        # Product data
        product_matches = db.load_product_data(model_code=test_product.model_code)
        assert len(product_matches) == 1
        assert product_matches[0].brand == test_product.brand
        
        # Match results
        product_match_results = db.load_match_results(query_text=f"{test_product.brand} {test_product.malli}")
        assert len(product_match_results) == 1
        
        # Validation results
        product_validations = db.load_validation_results(model_code=test_product.model_code)
        assert len(product_validations) == 1
        
        # Verify data consistency across stages
        assert product_matches[0].model_code == product_match_results[0]["model_code"]
        assert product_matches[0].model_code == product_validations[0]["model_code"]
    
    def test_database_transaction_integrity_across_stages(self, temp_database):
        """Test database transaction integrity when stages interact"""
        db = temp_database
        
        # Simulate pipeline execution with transaction boundaries
        try:
            with db.get_connection() as conn:
                # Stage 1: Insert products
                products = SampleDataFactory.create_valid_products()[:2]
                
                for product in products:
                    conn.execute("""
                        INSERT INTO product_data 
                        (model_code, brand, year, malli, paketti, moottori, telamatto, kaynnistin, mittaristo, vari, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        product.model_code, product.brand, product.year, product.malli,
                        product.paketti, product.moottori, product.telamatto, 
                        product.kaynnistin, product.mittaristo, product.vari,
                        datetime.now()
                    ))
                
                # Stage 2: Insert match results
                for product in products:
                    conn.execute("""
                        INSERT INTO match_results
                        (query_text, matched_model, confidence_score, success, match_method, model_code, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"{product.brand} {product.malli}",
                        product.malli,
                        0.95,
                        True,
                        "bert_semantic",
                        product.model_code,
                        datetime.now()
                    ))
                
                # Stage 3: Insert validation results
                for product in products:
                    conn.execute("""
                        INSERT INTO validation_results
                        (model_code, success, confidence_score, errors, warnings, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        product.model_code,
                        True,
                        0.90,
                        "[]",  # JSON empty array
                        "[]",  # JSON empty array
                        datetime.now()
                    ))
                
                conn.commit()
        
        except Exception as e:
            pytest.fail(f"Transaction failed: {e}")
        
        # Verify all data was committed together
        products_count = len(db.load_product_data())
        match_count = len(db.load_match_results())
        validation_count = len(db.load_validation_results())
        
        assert products_count == 2
        assert match_count == 2
        assert validation_count == 2
    
    def test_database_rollback_on_stage_failure(self, temp_database):
        """Test database rollback when a pipeline stage fails"""
        db = temp_database
        
        # Start with some existing data
        initial_products = SampleDataFactory.create_valid_products()[:1]
        db.save_product_data(initial_products)
        
        # Simulate partial pipeline failure
        try:
            with db.get_connection() as conn:
                # Add new products
                new_products = SampleDataFactory.create_valid_products()[1:3]
                
                for product in new_products:
                    conn.execute("""
                        INSERT INTO product_data 
                        (model_code, brand, year, malli, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (product.model_code, product.brand, product.year, product.malli, datetime.now()))
                
                # Simulate error in later stage (e.g., duplicate key constraint)
                conn.execute("""
                    INSERT INTO product_data 
                    (model_code, brand, year, malli, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (initial_products[0].model_code, "Duplicate", 2024, "Test", datetime.now()))  # Duplicate model_code
                
                conn.commit()
                
        except sqlite3.IntegrityError:
            # Expected - rollback should occur
            pass
        
        # Verify only original data remains (rollback occurred)
        final_products = db.load_product_data()
        assert len(final_products) == 1  # Only initial product remains
        assert final_products[0].model_code == initial_products[0].model_code


class TestCatalogDataIntegration:
    """Test catalog data integration across pipeline stages"""
    
    def test_catalog_data_cross_stage_usage(self, temp_database):
        """Test catalog data usage across multiple pipeline stages"""
        db = temp_database
        
        # Stage 0: Load catalog data (pre-pipeline)
        catalog_data = SampleDataFactory.create_catalog_data()
        db.save_catalog_data(catalog_data)
        
        # Verify catalog data persisted
        loaded_catalog = db.load_catalog_data()
        assert len(loaded_catalog) == len(catalog_data)
        
        # Stage 1: Extract products that match catalog
        products = []
        for catalog_entry in loaded_catalog:
            product = ProductData(
                model_code=f"{catalog_entry.brand[:2]}{catalog_entry.model_family[:2]}".upper(),
                brand=catalog_entry.brand,
                year=2024,
                malli=catalog_entry.model_family
            )
            products.append(product)
        
        db.save_product_data(products)
        
        # Stage 2: Test matching integration with catalog
        for i, product in enumerate(products):
            # Find matching catalog entry
            matching_catalog = None
            for catalog_entry in loaded_catalog:
                if (catalog_entry.brand == product.brand and 
                    catalog_entry.model_family == product.malli):
                    matching_catalog = catalog_entry
                    break
            
            assert matching_catalog is not None
            
            # Save match result with catalog reference
            match_data = {
                "query_text": f"{product.brand} {product.malli}",
                "matched_model": matching_catalog.model_family,
                "confidence_score": 0.98,
                "success": True,
                "match_method": "catalog_exact_match",
                "model_code": product.model_code,
                "catalog_id": matching_catalog.model_family  # Reference to catalog
            }
            db.save_match_result(match_data)
        
        # Stage 3: Validation with catalog enrichment
        for product in products:
            # Get catalog data for validation enhancement
            product_catalog = db.load_catalog_data(brand=product.brand)
            assert len(product_catalog) >= 1
            
            # Enhanced validation using catalog specifications
            catalog_entry = product_catalog[0]
            validation_enhanced = True if catalog_entry.specifications else False
            
            validation_data = {
                "model_code": product.model_code,
                "success": True,
                "confidence_score": 0.95 if validation_enhanced else 0.85,
                "errors": [],
                "warnings": [],
                "catalog_enhanced": validation_enhanced,
                "catalog_features_count": len(catalog_entry.features) if catalog_entry.features else 0
            }
            db.save_validation_result(validation_data)
        
        # Verify catalog integration worked across all stages
        for product in products:
            # Check match results reference catalog
            matches = db.load_match_results(query_text=f"{product.brand} {product.malli}")
            assert len(matches) == 1
            assert "catalog_id" in matches[0]
            
            # Check validation used catalog data
            validations = db.load_validation_results(model_code=product.model_code)
            assert len(validations) == 1
            assert "catalog_enhanced" in validations[0]
    
    def test_catalog_data_filtering_and_querying(self, temp_database):
        """Test complex catalog data filtering across pipeline stages"""
        db = temp_database
        
        # Setup diverse catalog data
        catalog_entries = [
            CatalogData(
                model_family="Summit X",
                brand="Ski-Doo",
                specifications={"engine": "850 E-TEC", "track_width": "3.0"},
                features=["Mountain Riding", "Electronic Reverse"]
            ),
            CatalogData(
                model_family="Catalyst",
                brand="Arctic Cat", 
                specifications={"engine": "998cc Turbo", "track_width": "3.0"},
                features=["Electronic Power Steering", "7\" Touchscreen"]
            ),
            CatalogData(
                model_family="Ranger",
                brand="Lynx",
                specifications={"engine": "600R E-TEC", "track_width": "2.25"},
                features=["Utility Focused", "Storage Solutions"]
            )
        ]
        
        db.save_catalog_data(catalog_entries)
        
        # Test brand filtering
        skidoo_catalog = db.load_catalog_data(brand="Ski-Doo")
        assert len(skidoo_catalog) == 1
        assert skidoo_catalog[0].model_family == "Summit X"
        
        # Test model family filtering  
        catalyst_catalog = db.load_catalog_data(model_family="Catalyst")
        assert len(catalyst_catalog) == 1
        assert catalyst_catalog[0].brand == "Arctic Cat"
        
        # Test complex filtering (would require custom query methods)
        # Find entries with specific engine types
        turbo_entries = []
        for entry in db.load_catalog_data():
            if entry.specifications and "turbo" in entry.specifications.get("engine", "").lower():
                turbo_entries.append(entry)
        
        assert len(turbo_entries) == 1
        assert turbo_entries[0].model_family == "Catalyst"
        
        # Test feature-based filtering
        touchscreen_entries = []
        for entry in db.load_catalog_data():
            if entry.features and any("touchscreen" in feature.lower() for feature in entry.features):
                touchscreen_entries.append(entry)
        
        assert len(touchscreen_entries) == 1
        assert touchscreen_entries[0].brand == "Arctic Cat"


class TestConcurrentDatabaseAccess:
    """Test concurrent database access patterns"""
    
    def test_concurrent_stage_database_access(self, temp_database):
        """Test database access patterns that might occur with concurrent stages"""
        db = temp_database
        
        # Simulate Stage 1 writing while Stage 2 reads
        products = SampleDataFactory.create_valid_products()[:5]
        
        # Stage 1: Continuous product insertion (simulated)
        for i, product in enumerate(products):
            db.save_product_data([product], clear_existing=False)
            
            # Stage 2: Concurrent reading for matching (simulated)
            current_products = db.load_product_data()
            assert len(current_products) == i + 1
            
            # Stage 2: Save match result for this product
            if current_products:
                latest_product = current_products[-1]  # Just inserted product
                match_data = {
                    "query_text": f"{latest_product.brand} {latest_product.malli}",
                    "matched_model": latest_product.malli,
                    "confidence_score": 0.90,
                    "success": True,
                    "match_method": "concurrent_test",
                    "model_code": latest_product.model_code
                }
                db.save_match_result(match_data)
        
        # Verify final state is consistent
        final_products = db.load_product_data()
        final_matches = db.load_match_results()
        
        assert len(final_products) == 5
        assert len(final_matches) == 5
        
        # Verify each product has corresponding match
        for product in final_products:
            product_matches = db.load_match_results(query_text=f"{product.brand} {product.malli}")
            assert len(product_matches) == 1
    
    def test_database_locking_behavior(self, temp_database):
        """Test database locking and isolation behavior"""
        db = temp_database
        
        # Test read-while-write scenario
        initial_products = SampleDataFactory.create_valid_products()[:2]
        db.save_product_data(initial_products)
        
        # Start a transaction (simulating long-running operation)
        try:
            with db.get_connection() as conn:
                # Read current state
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM product_data")
                initial_count = cursor.fetchone()[0]
                assert initial_count == 2
                
                # Simulate long operation - insert more data in same transaction
                new_product = SampleDataFactory.create_valid_products()[2]
                conn.execute("""
                    INSERT INTO product_data (model_code, brand, year, malli, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (new_product.model_code, new_product.brand, new_product.year, 
                      new_product.malli, datetime.now()))
                
                # Before commit, verify transaction-local view
                cursor.execute("SELECT COUNT(*) FROM product_data")
                transaction_count = cursor.fetchone()[0]
                assert transaction_count == 3
                
                conn.commit()
        
        except Exception as e:
            pytest.fail(f"Transaction locking test failed: {e}")
        
        # Verify final committed state
        final_products = db.load_product_data()
        assert len(final_products) == 3


class TestDatabasePerformanceIntegration:
    """Test database performance under realistic pipeline loads"""
    
    @pytest.mark.performance
    def test_bulk_operations_performance(self, temp_database):
        """Test database performance with realistic pipeline data volumes"""
        from tests.utils import performance_timer
        
        db = temp_database
        
        # Generate realistic data volumes
        large_product_set = []
        for i in range(100):  # 100 products - realistic batch size
            product = ProductData(
                model_code=f"P{i:03d}",
                brand=f"Brand{i % 10}",  # 10 different brands
                year=2020 + (i % 5),     # 5 different years
                malli=f"Model {i // 10}", # 10 different models
                moottori=f"Engine Type {i % 3}",  # 3 engine types
                telamatto=f"{2.0 + (i % 3) * 0.25}"  # 3 track widths
            )
            large_product_set.append(product)
        
        # Test bulk product insertion performance
        with performance_timer.time_operation("bulk_product_insertion"):
            result = db.save_product_data(large_product_set, clear_existing=True)
            assert result is True
        
        # Should handle 100 products quickly
        performance_timer.assert_performance("bulk_product_insertion", 2.0)
        
        # Test bulk querying performance
        with performance_timer.time_operation("bulk_product_querying"):
            all_products = db.load_product_data()
            assert len(all_products) == 100
            
            # Query subsets
            brand_products = db.load_product_data(brand="Brand5")
            year_products = db.load_product_data(year=2022)
            
            assert len(brand_products) == 10  # 10 products per brand
            assert len(year_products) == 20   # 20 products per year
        
        performance_timer.assert_performance("bulk_product_querying", 0.5)
        
        # Test bulk match result insertion
        match_results = []
        for product in large_product_set:
            match_data = {
                "query_text": f"{product.brand} {product.malli}",
                "matched_model": product.malli,
                "confidence_score": 0.85 + (hash(product.model_code) % 100) / 1000,  # Vary confidence
                "success": True,
                "match_method": "performance_test",
                "model_code": product.model_code
            }
            match_results.append(match_data)
        
        with performance_timer.time_operation("bulk_match_insertion"):
            for match_data in match_results:
                db.save_match_result(match_data)
        
        performance_timer.assert_performance("bulk_match_insertion", 3.0)
        
        # Verify all data persisted correctly
        final_matches = db.load_match_results()
        assert len(final_matches) == 100
    
    def test_database_query_optimization(self, temp_database):
        """Test database query performance with indexes"""
        db = temp_database
        
        # Insert test data
        products = []
        for i in range(50):
            product = ProductData(
                model_code=f"IDX{i:02d}",
                brand=f"IndexBrand{i % 5}",
                year=2020 + (i % 4),
                malli=f"IndexModel{i % 10}"
            )
            products.append(product)
        
        db.save_product_data(products)
        
        # Test indexed queries (should be fast)
        with performance_timer.time_operation("indexed_query_model_code"):
            specific_product = db.load_product_data(model_code="IDX25")
            assert len(specific_product) == 1
        
        performance_timer.assert_performance("indexed_query_model_code", 0.1)
        
        with performance_timer.time_operation("indexed_query_brand_year"):
            filtered_products = db.load_product_data(brand="IndexBrand2", year=2022)
            assert len(filtered_products) >= 1
        
        performance_timer.assert_performance("indexed_query_brand_year", 0.1)
    
    def test_database_connection_pooling_simulation(self, temp_database):
        """Test database behavior under multiple connection scenarios"""
        db = temp_database
        
        # Simulate multiple pipeline stages accessing database concurrently
        products = SampleDataFactory.create_valid_products()[:3]
        db.save_product_data(products)
        
        # Test multiple simultaneous queries (connection reuse)
        connection_results = []
        
        for i in range(10):  # Simulate 10 concurrent operations
            with performance_timer.time_operation(f"connection_operation_{i}"):
                # Each operation uses its own connection context
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM product_data WHERE year = ?", (2024,))
                    count = cursor.fetchone()[0]
                    connection_results.append(count)
        
        # All operations should return same consistent result
        assert all(result == connection_results[0] for result in connection_results)
        assert connection_results[0] > 0  # Should find products with year 2024


class TestDatabaseMigrationAndSchema:
    """Test database schema changes and data migration scenarios"""
    
    def test_schema_evolution_compatibility(self, temp_database):
        """Test database schema compatibility across pipeline versions"""
        db = temp_database
        
        # Insert data with current schema
        products = SampleDataFactory.create_valid_products()[:2]
        db.save_product_data(products)
        
        # Verify current schema works
        loaded_products = db.load_product_data()
        assert len(loaded_products) == 2
        
        # Simulate schema evolution (add new column)
        with db.get_connection() as conn:
            try:
                # Add hypothetical new column for pipeline metadata
                conn.execute("ALTER TABLE product_data ADD COLUMN pipeline_version TEXT DEFAULT 'v1.0'")
                conn.execute("ALTER TABLE product_data ADD COLUMN extraction_confidence REAL DEFAULT 0.0")
                conn.commit()
                
                # Verify existing data still accessible
                loaded_products_after = db.load_product_data()
                assert len(loaded_products_after) == 2
                
                # Test inserting with new schema
                new_product = ProductData(
                    model_code="MIGR",
                    brand="Migration",
                    year=2024,
                    malli="Test"
                )
                
                # Insert with additional metadata
                conn.execute("""
                    INSERT INTO product_data 
                    (model_code, brand, year, malli, pipeline_version, extraction_confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_product.model_code, new_product.brand, new_product.year,
                    new_product.malli, "v2.0", 0.95, datetime.now()
                ))
                conn.commit()
                
                # Verify mixed schema data
                all_products = db.load_product_data()
                assert len(all_products) == 3
                
            except Exception as e:
                pytest.fail(f"Schema evolution test failed: {e}")
    
    def test_data_integrity_constraints(self, temp_database):
        """Test database integrity constraints across pipeline stages"""
        db = temp_database
        
        # Test unique constraints
        product1 = ProductData(model_code="UNIQ", brand="Test1", year=2024)
        product2 = ProductData(model_code="UNIQ", brand="Test2", year=2024)  # Same code
        
        db.save_product_data([product1])
        
        # Attempt to insert duplicate should be handled
        try:
            with db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO product_data (model_code, brand, year, created_at)
                    VALUES (?, ?, ?, ?)
                """, (product2.model_code, product2.brand, product2.year, datetime.now()))
                conn.commit()
            pytest.fail("Should have failed due to unique constraint")
        except sqlite3.IntegrityError:
            # Expected - unique constraint violation
            pass
        
        # Verify only first product remains
        products = db.load_product_data()
        assert len([p for p in products if p.model_code == "UNIQ"]) == 1
        
        # Test foreign key constraints (if implemented)
        # This would test that match_results reference valid products
        try:
            match_data = {
                "query_text": "Non-existent product",
                "matched_model": "Test",
                "confidence_score": 0.9,
                "success": True,
                "match_method": "constraint_test",
                "model_code": "NOEXIST"  # Non-existent model_code
            }
            
            # Should succeed (no foreign key constraint currently)
            # But demonstrates where constraints could be added
            result = db.save_match_result(match_data)
            assert result is True
            
        except Exception as e:
            # If foreign key constraints were enabled, this would fail
            print(f"Foreign key constraint test: {e}")
    
    def test_database_backup_and_restore_integration(self, temp_database):
        """Test database backup/restore scenarios for pipeline continuity"""
        db = temp_database
        
        # Create comprehensive test data
        products = SampleDataFactory.create_valid_products()[:3]
        catalog_data = SampleDataFactory.create_catalog_data()[:2]
        
        db.save_product_data(products)
        db.save_catalog_data(catalog_data)
        
        # Add match and validation results
        for product in products:
            match_data = {
                "query_text": f"{product.brand} {product.malli}",
                "matched_model": product.malli,
                "confidence_score": 0.92,
                "success": True,
                "match_method": "backup_test",
                "model_code": product.model_code
            }
            db.save_match_result(match_data)
            
            validation_data = {
                "model_code": product.model_code,
                "success": True,
                "confidence_score": 0.90,
                "errors": [],
                "warnings": []
            }
            db.save_validation_result(validation_data)
        
        # Simulate backup (copy database file)
        backup_path = db.db_path.parent / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        try:
            import shutil
            shutil.copy2(db.db_path, backup_path)
            
            # Verify backup file exists and is valid
            assert backup_path.exists()
            
            # Test restore by creating new database instance from backup
            backup_db = DatabaseManager(backup_path)
            
            # Verify all data restored correctly
            restored_products = backup_db.load_product_data()
            restored_catalog = backup_db.load_catalog_data()
            restored_matches = backup_db.load_match_results()
            restored_validations = backup_db.load_validation_results()
            
            assert len(restored_products) == 3
            assert len(restored_catalog) == 2
            assert len(restored_matches) == 3
            assert len(restored_validations) == 3
            
            # Verify data integrity
            for original, restored in zip(products, restored_products):
                assert original.model_code == restored.model_code
                assert original.brand == restored.brand
                assert original.year == restored.year
            
        finally:
            # Cleanup backup file
            if backup_path.exists():
                backup_path.unlink()