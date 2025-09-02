"""
Simple End-to-End Workflow Tests
===============================

Simplified E2E tests that validate basic pipeline workflows using the existing codebase structure.
These tests focus on core functionality without complex external dependencies.
"""

import pytest
import tempfile
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any
import time

# Import core components  
from core.models import ProductData, CatalogData, ValidationResult, MatchResult
from core.database import DatabaseManager
from core.exceptions import PipelineError

# Import fixtures
from tests.fixtures.sample_data import SampleDataFactory


class TestSimpleWorkflows:
    """Simple end-to-end tests for basic pipeline workflows"""

    @pytest.mark.e2e
    def test_basic_data_flow_e2e(self, temp_database):
        """
        Test basic data flow through the pipeline stages
        """
        # Stage 1: Create sample extracted products
        extracted_products = [
            ProductData(
                model_code="S1BX",
                brand="Ski-Doo", 
                year=2024,
                malli="Summit X",
                paketti="Expert 165",
                moottori="850 E-TEC Turbo R"
            ),
            ProductData(
                model_code="P850", 
                brand="Polaris",
                year=2024,
                malli="Pro-RMK 850",
                paketti="Assault 155", 
                moottori="850 Patriot"
            )
        ]
        
        # Save to database (simulating extraction stage)
        save_result = temp_database.save_product_data(extracted_products, clear_existing=True)
        assert save_result is True
        
        # Verify extraction data
        saved_products = temp_database.get_all_product_data()
        assert len(saved_products) == 2
        assert saved_products[0].model_code in ["S1BX", "P850"]
        
        # Stage 2: Create sample catalog data and matching results
        catalog_data = [
            CatalogData(
                model_family="Summit X",
                specifications={"engine": "850 E-TEC", "track_width": "3.0"},
                features=["Electronic Reverse", "Digital Display"]
            ),
            CatalogData(
                model_family="Pro-RMK",
                specifications={"engine": "850 Patriot", "track_width": "2.75"}, 
                features=["Mountain Performance", "AXYS Chassis"]
            )
        ]
        
        temp_database.save_catalog_data(catalog_data)
        
        # Create match results (simulating matching stage)
        match_results = [
            MatchResult(
                product_data=extracted_products[0],
                catalog_data=catalog_data[0],
                confidence_score=0.95,
                matched=True
            ),
            MatchResult(
                product_data=extracted_products[1], 
                catalog_data=catalog_data[1],
                confidence_score=0.88,
                matched=True
            )
        ]
        
        # Verify matching results
        assert len(match_results) == 2
        assert all(result.matched for result in match_results)
        assert all(result.confidence_score > 0.8 for result in match_results)
        
        # Stage 3: Create validation results
        validation_results = [
            ValidationResult(
                success=True,
                confidence=0.94,
                metadata={"product_code": "S1BX", "validation_type": "e2e_test"}
            ),
            ValidationResult(
                success=True, 
                confidence=0.89,
                metadata={"product_code": "P850", "validation_type": "e2e_test"}
            )
        ]
        
        # Verify validation results
        assert len(validation_results) == 2
        assert all(result.success for result in validation_results)
        assert all(result.confidence > 0.85 for result in validation_results)
        
        # Stage 4: Generate simple specifications (simulated)
        generated_specs = []
        for match_result, validation_result in zip(match_results, validation_results):
            if validation_result.success:
                spec = {
                    "product_id": match_result.product_data.model_code,
                    "title": match_result.product_data.full_model_name,
                    "description": f"{match_result.product_data.brand} {match_result.product_data.malli}",
                    "specifications": match_result.catalog_data.specifications if match_result.catalog_data else {},
                    "features": match_result.catalog_data.features if match_result.catalog_data else []
                }
                generated_specs.append(spec)
        
        # Verify spec generation
        assert len(generated_specs) == 2
        assert all("title" in spec for spec in generated_specs)
        assert all("specifications" in spec for spec in generated_specs)
        
        # Stage 5: Simulate upload success
        upload_results = []
        for spec in generated_specs:
            upload_results.append({
                "status": "success",
                "product_id": spec["product_id"],
                "upload_id": f"upload_{spec['product_id']}"
            })
        
        # Verify upload results
        assert len(upload_results) == 2
        assert all(result["status"] == "success" for result in upload_results)
        
        # Final verification of complete data flow
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        # Verify all products are in database
        cursor.execute("SELECT COUNT(*) FROM product_data")
        product_count = cursor.fetchone()[0]
        assert product_count == 2
        
        # Verify all catalog data is in database  
        cursor.execute("SELECT COUNT(*) FROM catalog_data")
        catalog_count = cursor.fetchone()[0]
        assert catalog_count == 2
        
        conn.close()

    @pytest.mark.e2e
    def test_mixed_success_failure_e2e(self, temp_database):
        """
        Test pipeline behavior with mixed success and failure scenarios
        """
        # Create mixed quality products (some valid, some problematic)
        mixed_products = [
            ProductData(
                model_code="GOOD",
                brand="Ski-Doo",
                year=2024,
                malli="Summit X", 
                paketti="Expert 165",
                moottori="850 E-TEC"
            ),
            # This will pass basic validation but might fail later stages
            ProductData(
                model_code="PART", 
                brand="Unknown",
                year=2024,
                malli="Partial Model",
                paketti="TBD",
                moottori="Unknown Engine"
            )
        ]
        
        # Save mixed data
        temp_database.save_product_data(mixed_products, clear_existing=True)
        saved_products = temp_database.get_all_product_data()
        assert len(saved_products) == 2
        
        # Create matching results with varying success
        match_results = [
            MatchResult(
                product_data=mixed_products[0],
                catalog_data=CatalogData(
                    model_family="Summit X",
                    specifications={"engine": "850 E-TEC"}
                ),
                confidence_score=0.95,
                matched=True
            ),
            MatchResult(
                product_data=mixed_products[1],
                catalog_data=None,  # No match found
                confidence_score=0.35,
                matched=False
            )
        ]
        
        # Create validation results reflecting match quality
        validation_results = [
            ValidationResult(
                success=True,
                confidence=0.93,
                metadata={"product_code": "GOOD"}
            ),
            ValidationResult(
                success=False,
                confidence=0.40,
                errors=["Low matching confidence", "Unknown brand"],
                metadata={"product_code": "PART"}
            )
        ]
        
        # Only generate specs for successful validations
        successful_products = [
            (match, validation) for match, validation in zip(match_results, validation_results)
            if validation.success
        ]
        
        generated_specs = []
        for match_result, validation_result in successful_products:
            spec = {
                "product_id": match_result.product_data.model_code,
                "title": match_result.product_data.full_model_name,
                "status": "generated"
            }
            generated_specs.append(spec)
        
        # Verify business logic - only valid products proceed
        assert len(generated_specs) == 1  # Only the "GOOD" product
        assert generated_specs[0]["product_id"] == "GOOD"
        
        # Simulate upload for generated specs
        upload_results = []
        for spec in generated_specs:
            upload_results.append({
                "status": "success",
                "product_id": spec["product_id"]
            })
        
        # Verify final results
        successful_validations = [v for v in validation_results if v.success]
        failed_validations = [v for v in validation_results if not v.success]
        
        assert len(successful_validations) == 1
        assert len(failed_validations) == 1
        assert len(upload_results) == 1
        
        # Verify database reflects processing results
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT model_code FROM product_data ORDER BY model_code")
        saved_codes = [row[0] for row in cursor.fetchall()]
        assert "GOOD" in saved_codes
        assert "PART" in saved_codes
        
        conn.close()

    @pytest.mark.e2e
    def test_batch_processing_workflow_e2e(self, temp_database):
        """
        Test batch processing workflow with multiple products
        """
        # Create batch of products
        batch_size = 5
        batch_products = []
        
        sample_products = SampleDataFactory.create_valid_products()
        for i in range(batch_size):
            base_product = sample_products[i % len(sample_products)]
            batch_product = ProductData(
                model_code=f"B{i:03d}",  # B000, B001, etc.
                brand=base_product.brand,
                year=base_product.year,
                malli=f"{base_product.malli} Batch{i}",
                paketti=base_product.paketti,
                moottori=base_product.moottori
            )
            batch_products.append(batch_product)
        
        # Process batch through pipeline stages
        start_time = time.time()
        
        # Stage 1: Batch extraction simulation
        temp_database.save_product_data(batch_products, clear_existing=True)
        stage1_time = time.time() - start_time
        
        # Verify batch extraction
        saved_products = temp_database.get_all_product_data()
        assert len(saved_products) == batch_size
        
        # Stage 2: Batch matching simulation
        batch_matches = []
        for product in batch_products:
            match_result = MatchResult(
                product_data=product,
                catalog_data=CatalogData(
                    model_family=product.malli.split()[0],  # Use first word as family
                    specifications={"engine": product.moottori or "Standard Engine"}
                ),
                confidence_score=0.85 + (0.1 * (hash(product.model_code) % 3) / 10),  # Vary confidence
                matched=True
            )
            batch_matches.append(match_result)
        
        stage2_time = time.time() - start_time - stage1_time
        
        # Stage 3: Batch validation simulation  
        batch_validations = []
        for match in batch_matches:
            validation = ValidationResult(
                success=match.confidence_score > 0.8,
                confidence=match.confidence_score,
                metadata={"batch_processing": True, "product_code": match.product_data.model_code}
            )
            batch_validations.append(validation)
        
        stage3_time = time.time() - start_time - stage1_time - stage2_time
        
        # Stage 4: Batch spec generation
        successful_validations = [v for v in batch_validations if v.success]
        batch_specs = []
        
        for validation in successful_validations:
            spec = {
                "product_id": validation.metadata["product_code"],
                "batch_processed": True,
                "generation_time": time.time()
            }
            batch_specs.append(spec)
        
        stage4_time = time.time() - start_time - stage1_time - stage2_time - stage3_time
        
        # Stage 5: Batch upload simulation
        batch_uploads = []
        for spec in batch_specs:
            upload_result = {
                "status": "success",
                "product_id": spec["product_id"],
                "batch_id": "BATCH_E2E_TEST"
            }
            batch_uploads.append(upload_result)
        
        total_time = time.time() - start_time
        
        # Verify batch processing results
        assert len(batch_matches) == batch_size
        assert len(batch_validations) == batch_size
        assert len(successful_validations) >= batch_size * 0.8  # At least 80% should succeed
        assert len(batch_specs) == len(successful_validations)
        assert len(batch_uploads) == len(batch_specs)
        
        # Verify performance - batch processing should be efficient
        assert total_time < 10.0  # Should complete in under 10 seconds
        
        # Verify database state
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM product_data WHERE model_code LIKE 'B%'")
        batch_count = cursor.fetchone()[0]
        assert batch_count == batch_size
        
        conn.close()
        
        # Business outcome verification
        success_rate = len(successful_validations) / batch_size
        assert success_rate >= 0.8, f"Batch success rate {success_rate:.2%} below 80% threshold"
        
        # Performance metrics
        print(f"\n📊 BATCH PROCESSING METRICS:")
        print(f"   Products: {batch_size}")
        print(f"   Success Rate: {success_rate:.2%}")
        print(f"   Total Time: {total_time:.3f}s")
        print(f"   Products/sec: {batch_size/total_time:.1f}")

    @pytest.mark.e2e 
    def test_data_consistency_e2e(self, temp_database):
        """
        Test data consistency throughout the pipeline
        """
        # Create test products with specific attributes to track
        consistency_products = [
            ProductData(
                model_code="CON1",
                brand="TestBrand",
                year=2024,
                malli="Consistency Model",
                paketti="Test Package", 
                moottori="Test Engine",
                price=15000.00,
                currency="EUR"
            ),
            ProductData(
                model_code="CON2",
                brand="TestBrand",
                year=2024,
                malli="Consistency Model 2",
                paketti="Premium Package",
                moottori="Premium Engine", 
                price=18000.00,
                currency="EUR"
            )
        ]
        
        # Track original data for consistency verification
        original_data = {
            product.model_code: {
                "brand": product.brand,
                "year": product.year,
                "malli": product.malli,
                "price": product.price,
                "currency": product.currency
            }
            for product in consistency_products
        }
        
        # Stage 1: Save and verify data integrity
        temp_database.save_product_data(consistency_products, clear_existing=True)
        saved_products = temp_database.get_all_product_data()
        
        # Verify Stage 1 data consistency
        saved_data = {p.model_code: p for p in saved_products}
        for code, original in original_data.items():
            saved_product = saved_data[code]
            assert saved_product.brand == original["brand"]
            assert saved_product.year == original["year"] 
            assert saved_product.malli == original["malli"]
            assert saved_product.price == original["price"]
            assert saved_product.currency == original["currency"]
        
        # Stage 2: Matching with data preservation
        matches_with_data = []
        for product in saved_products:
            match_result = MatchResult(
                product_data=product,
                catalog_data=CatalogData(
                    model_family=product.malli,
                    specifications={"price_range": f"{product.price}_{product.currency}"}
                ),
                confidence_score=0.90,
                matched=True
            )
            matches_with_data.append(match_result)
        
        # Verify Stage 2 data consistency
        for match in matches_with_data:
            original = original_data[match.product_data.model_code]
            assert match.product_data.brand == original["brand"]
            assert match.product_data.price == original["price"]
            assert str(match.product_data.price) in match.catalog_data.specifications["price_range"]
        
        # Stage 3: Validation with metadata tracking
        validations_with_tracking = []
        for match in matches_with_data:
            validation = ValidationResult(
                success=True,
                confidence=0.92,
                metadata={
                    "original_code": match.product_data.model_code,
                    "original_brand": match.product_data.brand,
                    "original_price": match.product_data.price,
                    "consistency_check": "passed"
                }
            )
            validations_with_tracking.append(validation)
        
        # Verify Stage 3 data consistency
        for validation in validations_with_tracking:
            original_code = validation.metadata["original_code"]
            original = original_data[original_code]
            assert validation.metadata["original_brand"] == original["brand"]
            assert validation.metadata["original_price"] == original["price"]
        
        # Stage 4: Spec generation with complete data chain
        specs_with_chain = []
        for validation, match in zip(validations_with_tracking, matches_with_data):
            spec = {
                "product_id": validation.metadata["original_code"],
                "title": f"{match.product_data.brand} {match.product_data.malli}",
                "price_info": f"{match.product_data.price} {match.product_data.currency}",
                "consistency_chain": {
                    "extraction": match.product_data.model_code,
                    "matching": match.matched,
                    "validation": validation.success,
                    "original_data": validation.metadata
                }
            }
            specs_with_chain.append(spec)
        
        # Verify Stage 4 data consistency
        for spec in specs_with_chain:
            original_code = spec["product_id"]
            original = original_data[original_code]
            assert original["brand"] in spec["title"]
            assert str(original["price"]) in spec["price_info"]
            assert spec["consistency_chain"]["validation"] is True
        
        # Stage 5: Final consistency verification
        final_results = []
        for spec in specs_with_chain:
            result = {
                "status": "success",
                "product_id": spec["product_id"],
                "data_chain_verified": all([
                    spec["consistency_chain"]["extraction"],
                    spec["consistency_chain"]["matching"], 
                    spec["consistency_chain"]["validation"]
                ])
            }
            final_results.append(result)
        
        # Complete consistency verification
        assert len(final_results) == len(consistency_products)
        assert all(result["data_chain_verified"] for result in final_results)
        assert all(result["status"] == "success" for result in final_results)
        
        # Database consistency check
        conn = sqlite3.connect(temp_database.db_path)
        cursor = conn.cursor()
        
        # Verify no data corruption occurred
        for code, original in original_data.items():
            cursor.execute(
                "SELECT brand, year, malli, price, currency FROM product_data WHERE model_code = ?",
                (code,)
            )
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == original["brand"]  # brand
            assert row[1] == original["year"]   # year
            assert row[2] == original["malli"]  # malli
            assert float(row[3]) == original["price"]  # price
            assert row[4] == original["currency"]  # currency
        
        conn.close()
        
        print(f"\n✅ DATA CONSISTENCY VERIFICATION:")
        print(f"   Products Processed: {len(consistency_products)}")
        print(f"   Consistency Checks Passed: {len([r for r in final_results if r['data_chain_verified']])}")
        print(f"   Data Integrity: 100%")