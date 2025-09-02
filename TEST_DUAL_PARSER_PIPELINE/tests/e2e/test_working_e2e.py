"""
Working End-to-End Tests
========================

Simplified E2E tests that work with the actual codebase structure and available methods.
These tests validate complete workflows using the DatabaseManager and core models.
"""

import pytest
import tempfile
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any
import time

# Import core components that actually exist
from core.models import ProductData, ValidationResult, MatchResult
from core.database import DatabaseManager
from core.exceptions import PipelineError

# Import fixtures
from tests.fixtures.sample_data import SampleDataFactory


class TestWorkingE2EWorkflows:
    """Working end-to-end tests using available functionality"""

    @pytest.mark.e2e
    def test_basic_pipeline_flow_e2e(self, temp_database):
        """
        Test basic pipeline flow using available database methods
        """
        # Stage 1: Create and save product data (simulating extraction)
        test_products = [
            ProductData(
                model_code="E2E1",
                brand="Ski-Doo",
                year=2024,
                malli="Summit X",
                paketti="Expert 165",
                moottori="850 E-TEC Turbo"
            ),
            ProductData(
                model_code="E2E2",
                brand="Polaris", 
                year=2024,
                malli="Pro-RMK 850",
                paketti="Assault 155",
                moottori="850 Patriot"
            )
        ]
        
        # Save products to database
        saved_count = temp_database.save_product_data(test_products, clear_existing=True)
        assert saved_count == 2
        
        # Load products back to verify data persistence
        loaded_products = temp_database.load_product_data()
        assert len(loaded_products) == 2
        
        # Verify data integrity
        loaded_codes = {p.model_code for p in loaded_products}
        assert "E2E1" in loaded_codes
        assert "E2E2" in loaded_codes
        
        # Stage 2: Create match results (simulating matching stage)  
        match_results = []
        for product in loaded_products:
            # Create dummy catalog data for successful match
            from core.models import CatalogData
            dummy_catalog = CatalogData(
                model_family=product.malli or "Test Family",
                specifications={"engine": product.moottori or "Test Engine"}
            )
            
            match_result = MatchResult(
                product_data=product,
                catalog_data=dummy_catalog,  # This will set matched=True
                confidence_score=0.92,
                match_details={"match_method": "e2e_test", "stage": "matching"}
            )
            match_results.append(match_result)
            
            # Save match result to database
            temp_database.save_match_result(match_result)
        
        # Stage 3: Create validation results (simulating validation stage)  
        validation_results = []
        for match_result in match_results:
            validation_result = ValidationResult(
                success=True,
                confidence=0.89,
                metadata={
                    "product_code": match_result.product_data.model_code,
                    "validation_stage": "e2e_test"
                }
            )
            validation_results.append(validation_result)
            
            # Save validation result to database
            product_id = f"{match_result.product_data.brand}_{match_result.product_data.model_code}_{match_result.product_data.year}"
            temp_database.save_validation_result(product_id, validation_result)
        
        # Verify complete pipeline execution
        assert len(match_results) == 2
        assert len(validation_results) == 2
        assert all(v.success for v in validation_results)
        assert all(m.matched for m in match_results)
        
        # Verify database state after complete pipeline
        stats = temp_database.get_statistics()
        assert stats["total_products"] >= 2
        
        # Final integration test - load data with filters
        ski_doo_products = temp_database.load_product_data(brand="Ski-Doo")
        polaris_products = temp_database.load_product_data(brand="Polaris")
        
        assert len(ski_doo_products) == 1
        assert len(polaris_products) == 1
        assert ski_doo_products[0].model_code == "E2E1"
        assert polaris_products[0].model_code == "E2E2"

    @pytest.mark.e2e 
    def test_error_handling_e2e(self, temp_database):
        """
        Test pipeline error handling and recovery
        """
        # Create products with potential issues
        problematic_products = [
            ProductData(
                model_code="GOOD",
                brand="TestBrand",
                year=2024,
                malli="Good Model",
                paketti="Standard",
                moottori="Standard Engine"
            ),
            # This product will be used to simulate processing issues
            ProductData(
                model_code="PROB",
                brand="TestBrand", 
                year=2024,
                malli="Problem Model",
                paketti="Issue Package",
                moottori="Problem Engine"
            )
        ]
        
        # Save products successfully
        saved_count = temp_database.save_product_data(problematic_products, clear_existing=True)
        assert saved_count == 2
        
        # Load products for processing
        loaded_products = temp_database.load_product_data()
        assert len(loaded_products) == 2
        
        # Simulate mixed matching results
        match_results = []
        for product in loaded_products:
            if product.model_code == "GOOD":
                # Good product matches successfully
                match_result = MatchResult(
                    product_data=product,
                    confidence_score=0.95,
                    matched=True,
                    match_details={"status": "success"}
                )
            else:
                # Problematic product has low confidence
                match_result = MatchResult(
                    product_data=product,
                    confidence_score=0.35,
                    matched=False,
                    match_details={"status": "low_confidence", "issues": ["unclear_model"]}
                )
            
            match_results.append(match_result)
            temp_database.save_match_result(match_result)
        
        # Simulate mixed validation results
        validation_results = []
        for match_result in match_results:
            if match_result.matched:
                # Successful match gets successful validation
                validation_result = ValidationResult(
                    success=True,
                    confidence=0.93,
                    metadata={"product_code": match_result.product_data.model_code}
                )
            else:
                # Failed match gets failed validation
                validation_result = ValidationResult(
                    success=False,
                    confidence=0.40,
                    errors=["Low matching confidence", "Model unclear"],
                    metadata={"product_code": match_result.product_data.model_code}
                )
            
            validation_results.append(validation_result)
            product_id = f"{match_result.product_data.brand}_{match_result.product_data.model_code}_{match_result.product_data.year}"
            temp_database.save_validation_result(product_id, validation_result)
        
        # Verify error handling - mixed results
        successful_matches = [m for m in match_results if m.matched]
        failed_matches = [m for m in match_results if not m.matched]
        successful_validations = [v for v in validation_results if v.success]
        failed_validations = [v for v in validation_results if not v.success]
        
        assert len(successful_matches) == 1
        assert len(failed_matches) == 1  
        assert len(successful_validations) == 1
        assert len(failed_validations) == 1
        
        # Verify that processing continues despite failures
        assert successful_matches[0].product_data.model_code == "GOOD"
        assert failed_matches[0].product_data.model_code == "PROB"
        
        # Verify database integrity after mixed results
        stats = temp_database.get_statistics()
        assert stats["total_products"] == 2

    @pytest.mark.e2e
    def test_batch_processing_e2e(self, temp_database):
        """
        Test batch processing capabilities
        """
        # Create a batch of products
        batch_size = 10
        batch_products = []
        
        for i in range(batch_size):
            product = ProductData(
                model_code=f"B{i:03d}",
                brand="BatchBrand" if i % 2 == 0 else "AltBrand",
                year=2024,
                malli=f"Batch Model {i}",
                paketti=f"Package {i % 3}",
                moottori=f"Engine Type {i % 4}"
            )
            batch_products.append(product)
        
        # Measure batch processing performance
        start_time = time.time()
        
        # Stage 1: Batch save
        saved_count = temp_database.save_product_data(batch_products, clear_existing=True)
        stage1_time = time.time() - start_time
        
        assert saved_count == batch_size
        assert stage1_time < 5.0  # Should complete quickly
        
        # Stage 2: Batch load and verify
        loaded_products = temp_database.load_product_data()
        assert len(loaded_products) == batch_size
        
        # Stage 3: Batch processing simulation
        batch_matches = []
        for product in loaded_products:
            # Simulate varying match quality
            confidence = 0.8 + (hash(product.model_code) % 20) / 100  # 0.8 to 0.99
            match_result = MatchResult(
                product_data=product,
                confidence_score=confidence,
                matched=confidence > 0.85,
                match_details={"batch_processing": True}
            )
            batch_matches.append(match_result)
            temp_database.save_match_result(match_result)
        
        # Stage 4: Batch validation simulation
        batch_validations = []
        for match in batch_matches:
            validation = ValidationResult(
                success=match.matched,
                confidence=match.confidence_score,
                metadata={"batch_id": "E2E_BATCH_TEST"}
            )
            batch_validations.append(validation)
            product_id = f"{match.product_data.brand}_{match.product_data.model_code}_{match.product_data.year}"
            temp_database.save_validation_result(product_id, validation)
        
        total_time = time.time() - start_time
        
        # Verify batch processing results
        successful_matches = [m for m in batch_matches if m.matched]
        successful_validations = [v for v in batch_validations if v.success]
        
        assert len(batch_matches) == batch_size
        assert len(batch_validations) == batch_size
        assert len(successful_matches) >= batch_size * 0.7  # At least 70% should succeed
        assert len(successful_validations) == len(successful_matches)
        
        # Performance verification
        assert total_time < 10.0  # Batch processing should be efficient
        products_per_second = batch_size / total_time
        assert products_per_second > 1.0  # Should process at least 1 product per second
        
        # Brand-based filtering test
        batch_brand_products = temp_database.load_product_data(brand="BatchBrand")
        alt_brand_products = temp_database.load_product_data(brand="AltBrand")
        
        assert len(batch_brand_products) == batch_size // 2  # Half should be BatchBrand
        assert len(alt_brand_products) == batch_size // 2   # Half should be AltBrand
        
        # Year-based filtering test
        year_2024_products = temp_database.load_product_data(year=2024)
        assert len(year_2024_products) == batch_size  # All should be 2024

    @pytest.mark.e2e
    def test_data_persistence_e2e(self, temp_database):
        """
        Test data persistence and database integrity across operations
        """
        # Phase 1: Initial data creation
        initial_products = [
            ProductData(
                model_code="PERS",
                brand="PersistBrand",
                year=2024,
                malli="Persist Model",
                paketti="Persist Package",
                moottori="Persist Engine",
                price=15000.00,
                currency="EUR"
            )
        ]
        
        temp_database.save_product_data(initial_products, clear_existing=True)
        
        # Phase 2: Add more data without clearing
        additional_products = [
            ProductData(
                model_code="ADD1",
                brand="PersistBrand",
                year=2024,
                malli="Additional Model 1",
                paketti="Add Package",
                moottori="Add Engine"
            ),
            ProductData(
                model_code="ADD2", 
                brand="DifferentBrand",
                year=2025,
                malli="Additional Model 2", 
                paketti="Different Package",
                moottori="Different Engine"
            )
        ]
        
        temp_database.save_product_data(additional_products, clear_existing=False)
        
        # Verify all data persisted
        all_products = temp_database.load_product_data()
        assert len(all_products) == 3
        
        # Verify specific data persistence
        codes = {p.model_code for p in all_products}
        assert "PERS" in codes
        assert "ADD1" in codes
        assert "ADD2" in codes
        
        # Phase 3: Add processing results
        for product in all_products:
            # Add match results
            match_result = MatchResult(
                product_data=product,
                confidence_score=0.88,
                matched=True,
                match_details={"persistence_test": True}
            )
            temp_database.save_match_result(match_result)
            
            # Add validation results
            validation_result = ValidationResult(
                success=True,
                confidence=0.90,
                metadata={"product_code": product.model_code, "persistence_test": True}
            )
            product_id = f"{product.brand}_{product.model_code}_{product.year}"
            temp_database.save_validation_result(product_id, validation_result)
        
        # Phase 4: Verify persistence after processing
        stats = temp_database.get_statistics()
        assert stats["total_products"] == 3
        
        # Phase 5: Test database integrity with direct SQL
        with temp_database.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verify price entries
            cursor.execute("SELECT COUNT(*) FROM price_entries")
            entry_count = cursor.fetchone()[0]
            assert entry_count == 3
            
            # Verify match results table exists and has data
            cursor.execute("SELECT COUNT(*) FROM match_results")
            match_count = cursor.fetchone()[0]
            assert match_count == 3
            
            # Verify validation results table exists and has data
            cursor.execute("SELECT COUNT(*) FROM validation_results")
            validation_count = cursor.fetchone()[0]
            assert validation_count == 3
            
            # Verify data integrity - prices preserved
            cursor.execute("SELECT price FROM price_entries WHERE model_code = 'PERS'")
            price_row = cursor.fetchone()
            assert price_row is not None
            assert float(price_row[0]) == 15000.00
        
        # Phase 6: Test filtering persistence
        persist_brand_products = temp_database.load_product_data(brand="PersistBrand")
        different_brand_products = temp_database.load_product_data(brand="DifferentBrand")
        year_2024_products = temp_database.load_product_data(year=2024)
        year_2025_products = temp_database.load_product_data(year=2025)
        
        assert len(persist_brand_products) == 2  # PERS and ADD1
        assert len(different_brand_products) == 1  # ADD2
        assert len(year_2024_products) == 2  # PERS and ADD1  
        assert len(year_2025_products) == 1  # ADD2
        
        print(f"\n💾 DATA PERSISTENCE VERIFICATION:")
        print(f"   Total Products: {len(all_products)}")
        print(f"   Database Stats: {stats}")
        print(f"   Brand Filtering: ✅")
        print(f"   Year Filtering: ✅") 
        print(f"   Price Preservation: ✅")

    @pytest.mark.e2e
    def test_statistics_tracking_e2e(self, temp_database):
        """
        Test statistics tracking throughout pipeline execution
        """
        # Create diverse test data for statistics
        stats_products = [
            ProductData(model_code="ST01", brand="StatsBrand", year=2024, malli="Stats Model 1"),
            ProductData(model_code="ST02", brand="StatsBrand", year=2024, malli="Stats Model 2"), 
            ProductData(model_code="ST03", brand="OtherBrand", year=2023, malli="Other Model"),
        ]
        
        # Initial statistics (should be empty)
        initial_stats = temp_database.get_statistics()
        
        # Save products and check statistics update
        temp_database.save_product_data(stats_products, clear_existing=True)
        after_save_stats = temp_database.get_statistics()
        
        # Verify statistics updated
        assert after_save_stats["total_products"] == 3
        assert after_save_stats["total_products"] > initial_stats.get("total_products", 0)
        
        # Add match results and check statistics
        for product in stats_products:
            match_result = MatchResult(
                product_data=product,
                confidence_score=0.87,
                matched=True,
                match_details={"stats_test": True}
            )
            temp_database.save_match_result(match_result)
        
        # Add validation results and check statistics  
        for product in stats_products:
            validation_result = ValidationResult(
                success=True,
                confidence=0.89,
                metadata={"product_code": product.model_code, "stats_test": True}
            )
            product_id = f"{product.brand}_{product.model_code}_{product.year}"
            temp_database.save_validation_result(product_id, validation_result)
        
        # Final statistics check
        final_stats = temp_database.get_statistics()
        assert final_stats["total_products"] == 3
        
        # Verify statistics reflect processing
        print(f"\n📈 STATISTICS TRACKING:")
        print(f"   Initial Stats: {initial_stats}")
        print(f"   After Save: {after_save_stats}")
        print(f"   Final Stats: {final_stats}")
        
        # Verify brand-based statistics
        brand_products = temp_database.load_product_data(brand="StatsBrand")
        other_brand_products = temp_database.load_product_data(brand="OtherBrand")
        
        assert len(brand_products) == 2
        assert len(other_brand_products) == 1