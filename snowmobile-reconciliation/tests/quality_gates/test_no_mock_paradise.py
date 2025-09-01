"""
Quality Gate: No Mock Paradise Prevention

Enforces the production testing methodology by ensuring tests use real data.
Prevents AYTS-style failures caused by over-mocking.
"""
import ast
import glob
from pathlib import Path


class TestQualityGates:
    """Enforce testing quality standards"""
    
    def test_no_mock_paradise(self):
        """Ensure tests use real data, not excessive mocking"""
        
        test_files = glob.glob("tests/**/*.py", recursive=True)
        violations = []
        
        for test_file in test_files:
            # Skip this quality gate file itself
            if "quality_gates" in test_file:
                continue
                
            try:
                with open(test_file, encoding="utf-8") as f:
                    content = f.read()
                
                # Count mocking patterns
                mock_count = (
                    content.count("@patch") +
                    content.count("Mock(") + 
                    content.count("MagicMock") +
                    content.count("AsyncMock") +
                    content.count("mock_")
                )
                
                # Count real data patterns
                real_data_count = (
                    content.count("real_") +
                    content.count("actual_") +
                    content.count("production_") +
                    content.count("EXPECTED_MODEL_RESULTS") +
                    content.count("validate_against_expected") +
                    content.count(".pdf")
                )
                
                # Calculate mock ratio
                total_patterns = mock_count + real_data_count
                if total_patterns > 0:
                    mock_ratio = mock_count / total_patterns
                    
                    # Flag files with excessive mocking
                    if mock_ratio > 0.7:  # More than 70% mocking
                        violations.append({
                            "file": test_file,
                            "mock_count": mock_count,
                            "real_data_count": real_data_count,
                            "mock_ratio": mock_ratio
                        })
                        
            except Exception as e:
                # Skip files we can't read
                pass
        
        # Report violations
        if violations:
            violation_details = "\n".join([
                f"  {v['file']}: {v['mock_ratio']:.1%} mocking ({v['mock_count']} mocks, {v['real_data_count']} real data)"
                for v in violations
            ])
            
            assert False, f"Mock Paradise detected in {len(violations)} files:\n{violation_details}\n\nUse real data instead of excessive mocking!"
    
    def test_no_fake_fixtures(self):
        """Ensure fixtures use real production data"""
        
        fixture_files = glob.glob("tests/fixtures/**/*.py", recursive=True)
        violations = []
        
        for fixture_file in fixture_files:
            try:
                with open(fixture_file, encoding="utf-8") as f:
                    content = f.read()
                
                # Check for fabricated data indicators
                fake_indicators = [
                    "fake_", "mock_", "dummy_", "test_123", "example_",
                    "sample_data", "fabricated", "artificial"
                ]
                
                found_fakes = []
                for indicator in fake_indicators:
                    if indicator in content.lower():
                        found_fakes.append(indicator)
                
                if found_fakes:
                    violations.append({
                        "file": fixture_file,
                        "fake_indicators": found_fakes
                    })
                    
            except Exception:
                pass
        
        if violations:
            violation_details = "\n".join([
                f"  {v['file']}: {', '.join(v['fake_indicators'])}"
                for v in violations
            ])
            
            assert False, f"Fake fixtures detected in {len(violations)} files:\n{violation_details}\n\nUse real production data in fixtures!"
    
    def test_ayts_specific_validation(self):
        """Specific validation for AYTS case to prevent regression"""
        
        # Check that AYTS is correctly specified in expected results
        from tests.fixtures.expected_results_real import EXPECTED_MODEL_RESULTS
        
        ayts_expected = EXPECTED_MODEL_RESULTS.get("AYTS")
        assert ayts_expected is not None, "AYTS must be in expected results"
        
        # Critical validations that would have prevented the failure
        assert ayts_expected["brand"] == "Ski-Doo", \
            f"AYTS brand must be Ski-Doo, got {ayts_expected['brand']}"
        
        assert ayts_expected["engine"] == "900 ACE Turbo R", \
            f"AYTS engine must be 900 ACE Turbo R, got {ayts_expected['engine']}"
        
        assert float(ayts_expected["price_eur"]) == 25110.00, \
            f"AYTS price must be 25110.00 EUR, got {ayts_expected['price_eur']}"
        
        assert ayts_expected["model_family"] == "Expedition SE", \
            f"AYTS model must be Expedition SE, got {ayts_expected['model_family']}"
    
    def test_real_pdf_files_exist(self):
        """Ensure referenced PDF files actually exist"""
        
        from tests.fixtures.expected_results_real import EXPECTED_MODEL_RESULTS
        
        project_root = Path(__file__).parent.parent.parent.parent
        data_dir = project_root / "data"
        
        for model_code, expected in EXPECTED_MODEL_RESULTS.items():
            if "source_pdf" in expected:
                pdf_path = data_dir / expected["source_pdf"]
                assert pdf_path.exists(), \
                    f"Referenced PDF not found for {model_code}: {pdf_path}"
    
    def test_no_hardcoded_mock_results(self):
        """Ensure no hardcoded mock results that could mask failures"""
        
        test_files = glob.glob("tests/**/*.py", recursive=True)
        violations = []
        
        # Patterns that indicate hardcoded mock results
        suspicious_patterns = [
            'return "Lynx Adventure"',  # The wrong result from AYTS failure
            'return 14995',             # The wrong price from AYTS failure
            'return "600 ACE"',         # Wrong engine
            '"fake_brand"',
            '"mock_model"',
            'confidence=1.0',           # Unrealistically perfect confidence
        ]
        
        for test_file in test_files:
            try:
                with open(test_file, encoding="utf-8") as f:
                    content = f.read()
                
                found_patterns = []
                for pattern in suspicious_patterns:
                    if pattern in content:
                        found_patterns.append(pattern)
                
                if found_patterns:
                    violations.append({
                        "file": test_file,
                        "patterns": found_patterns
                    })
                    
            except Exception:
                pass
        
        if violations:
            violation_details = "\n".join([
                f"  {v['file']}: {', '.join(v['patterns'])}"
                for v in violations
            ])
            
            assert False, f"Hardcoded mock results found in {len(violations)} files:\n{violation_details}"